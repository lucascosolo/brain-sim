import functools
import math
import queue
import secrets
import time
from collections import deque

from .engine import Engine
from .params import DT_MS, SEED, STIM_ACTIVE_MAX
from . import telemetry
from .telemetry import REPLY_KEYS

BATCH = 50
PRESENT_TICKS = 200

MAX_STEP_TICKS = 100000
# A present() that arms the encode schedule (SPEC 8.12) runs the identification pass
# inline on a deep copy, so a long presentation would block the worker loop twice over.
ENCODE_PRESENT_MAX_TICKS = 2000

_RESULT_FIELDS = ("reason", "stim_id", "n_cells", "amp_mv", "t_accept", "t_end_planned",
                  "t_target", "phase_before", "phase_after", "changed", "phase_clock_reset",
                  "factor")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_finite_float(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _validate(k, c, e):
    net = e.net
    if k == "inject":
        ids = c.get("ids")
        if not isinstance(ids, list) or len(ids) > 5000 or not all(_is_int(i) for i in ids):
            raise ValueError("ids must be a list of ints, length <= 5000")
        if any(i < 0 or i >= net.n for i in ids):
            raise ValueError("ids must be in [0, net.n)")
        amp = c.get("amp", 8.0)
        if not _is_finite_float(amp) or not (-50 <= amp <= 50):
            raise ValueError("amp must be a finite float in [-50, 50]")
        ticks = c.get("ticks", 50)
        if not _is_int(ticks) or not (1 <= ticks <= 100000):
            raise ValueError("ticks must be an int in [1, 100000]")
    elif k == "present":
        ticks = c.get("ticks", PRESENT_TICKS)
        if not _is_int(ticks) or not (1 <= ticks <= 100000):
            raise ValueError("ticks must be an int in [1, 100000]")
        pattern = c.get("pattern", 0)
        if not _is_int(pattern) or pattern not in range(len(e.patterns)):
            raise ValueError("pattern out of range")
        if e.encode_stage == "idle" and ticks > ENCODE_PRESENT_MAX_TICKS:
            raise ValueError(
                f"ticks must be <= {ENCODE_PRESENT_MAX_TICKS} while encode-mode is idle: "
                "the identification pass copies the engine and runs it inline")
    elif k in ("inspect", "watch"):
        i = c.get("id")
        if not _is_int(i) or not (0 <= i < net.n):
            raise ValueError("id must be an int in [0, net.n)")
    elif k == "region":
        if c.get("name") not in net.region_names:
            raise ValueError("unknown region")
    elif k == "speed":
        f = c.get("factor", 1.0)
        if not _is_finite_float(f) or not (0 <= f <= 64):
            raise ValueError("factor must be a finite float in [0, 64]")
    elif k in ("encode", "slow"):
        if not isinstance(c.get("on"), bool):
            raise ValueError("on must be a bool")
    elif k == "step":
        ticks = c.get("ticks", 1)
        if not _is_int(ticks) or not (1 <= ticks <= 100000):
            raise ValueError("ticks must be an int in [1, 100000]")


def _put(q, msg):
    assert set(msg) == REPLY_KEYS[msg["type"]], msg["type"]
    try:
        q.put_nowait(msg)
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(msg)
        except queue.Full:
            pass


class Session:
    """One engine plus the command protocol; no threads, no queues of its own."""

    def __init__(self, engine, reply_put, frame_put, run_id=None, batch=BATCH):
        self.e = engine
        self.reply_put = reply_put
        self.frame_put = frame_put
        self.run_id = run_id or f"run-{secrets.token_hex(3)}"
        self.batch = batch
        self.running = True
        self.speed = 1.0
        self.steps = deque()  # FIFO of [req, remaining]

    # --- emission -------------------------------------------------------
    def _emit(self, put, msg):
        assert set(msg) == REPLY_KEYS[msg["type"]], msg["type"]
        put(msg)

    def _reply(self, **msg):
        self._emit(self.reply_put, dict(run_id=self.run_id, **msg))

    def _result(self, cmd, req, status, **fields):
        out = dict(type="result", run_id=self.run_id, req=req, cmd=cmd, t=self.e.t,
                   status=status)
        out.update({k: None for k in _RESULT_FIELDS})
        out.update(fields)
        self._emit(self.reply_put, out)

    def _status(self):
        self._reply(type="status", running=self.running, speed=self.speed, t=self.e.t)

    def _stimlog(self):
        self._reply(type="stimlog", **telemetry.stimlog(self.e))

    # --- commands -------------------------------------------------------
    def handle(self, cmd):
        c = cmd if isinstance(cmd, dict) else {}
        k = c.get("cmd")
        req = c.get("req")
        try:
            _validate(k, c, self.e)
        except Exception as exc:
            self._result(k, req, "rejected", reason=f"invalid: {exc}")
            if req is None:
                self._reply(type="error", cmd=k, msg=str(exc), req=None)
            return
        try:
            self._dispatch(k, c, req)
        except (ValueError, KeyError, TypeError) as exc:
            self._result(k, req, "rejected", reason=f"invalid: {exc}")
            if req is None:
                self._reply(type="error", cmd=k, msg=str(exc), req=None)

    def _dispatch(self, k, c, req):
        e = self.e
        if k == "run" or k == "pause":
            self.running = k == "run"
            self._result(k, req, "accepted")
            self._status()
        elif k == "speed":
            self.speed = float(c.get("factor", 1.0))
            self._result(k, req, "accepted", factor=self.speed)
            self._status()
        elif k == "step":
            ticks = int(c.get("ticks", 1))
            pending = sum(s[1] for s in self.steps)
            if pending + ticks > MAX_STEP_TICKS:
                self._result(k, req, "rejected",
                             reason=f"invalid: pending step ticks exceed {MAX_STEP_TICKS}")
                return
            self.steps.append([req, ticks])
            self._result(k, req, "accepted", t_target=e.t + pending + ticks)
        elif k == "sleep":
            before = e.phase
            e.set_sleep(bool(c.get("on")))
            self._result(k, req, "accepted", phase_before=before, phase_after=e.phase,
                         changed=before != e.phase, phase_clock_reset=True)
        elif k in ("inject", "present"):
            if len(e._inj) >= STIM_ACTIVE_MAX:
                self._result(k, req, "rejected", reason="too_many_active")
                return
            if k == "inject":
                rec = e.inject(c["ids"], c.get("amp", 8.0), c.get("ticks", 50))
                reason = "no_cells"
            else:
                rec = e.present(c.get("pattern", 0), c.get("ticks", PRESENT_TICKS))
                reason = "sense_gated"
            if rec is None:
                self._result(k, req, "rejected", reason=reason)
            else:
                self._result(k, req, "accepted", stim_id=rec["stim_id"],
                             n_cells=rec["n_cells"], amp_mv=rec["amp_mv"],
                             t_accept=rec["t_accept"], t_end_planned=rec["t_end_planned"])
        elif k == "encode":
            # The MODE flag only; an armed schedule is never cancelled by it.
            before = e.encode_mode
            e.encode_mode = bool(c["on"])
            self._result(k, req, "accepted", changed=before != e.encode_mode)
        elif k == "slow":
            # SPEC 8.13: the flag only; the slow components already stored are kept.
            before = e.slow_weights
            e.slow_weights = bool(c["on"])
            self._result(k, req, "accepted", changed=before != e.slow_weights)
        elif k == "watch":
            e.watch(int(c["id"]))
            self._result(k, req, "accepted")
        elif k == "inspect":
            self._reply(type="inspect", **e.inspect_neuron(int(c["id"])))
        elif k == "region":
            self._reply(type="region", **e.region_stats(c["name"]))
        elif k == "layout":
            # built before any emission so the four-reply sequence cannot abort mid-way
            lay = dict(type="layout", **e.layout())
            cfg = dict(type="config", **telemetry.config(e, self.batch, PRESENT_TICKS))
            self._reply(**lay)
            self._reply(**cfg)
            self._status()
            self._stimlog()
        elif k == "stimlog":
            self._stimlog()
        elif k == "status":
            self._status()
        else:
            raise ValueError(f"unknown cmd {k!r}")

    # --- stepping -------------------------------------------------------
    def advance(self):
        pending = sum(s[1] for s in self.steps)
        n = self.batch if self.running else min(pending, self.batch)
        if n:
            self.e.step(n)
        left = n
        while left and self.steps:
            head = self.steps[0]
            used = min(head[1], left)
            head[1] -= used
            left -= used
            if head[1] == 0:
                self.steps.popleft()
                # t may exceed t_target: a free-running batch overshoots the request.
                self._result("step", head[0], "executed")
        return n

    def emit_frame(self, wall_ratio):
        f = self.e.frame()
        f["wall_ratio"] = wall_ratio
        msg = dict(type="frame", run_id=self.run_id, **f)
        self._emit(self.frame_put, msg)
        return msg


def run(cmd_q, frame_q, reply_q, seed=SEED):
    e = Engine(seed=seed)
    s = Session(e, functools.partial(_put, reply_q), functools.partial(_put, frame_q))
    pace = deque()
    s.handle({"cmd": "layout"})
    while True:
        iter_t0 = time.perf_counter()
        try:
            while True:
                c = cmd_q.get_nowait()
                if isinstance(c, dict) and c.get("cmd") == "quit":
                    return
                s.handle(c)
        except queue.Empty:
            pass

        t0 = time.perf_counter()
        n = s.advance()
        elapsed = time.perf_counter() - t0
        sim_s = n * DT_MS / 1000.0
        if s.running and s.speed > 0:
            slack = sim_s / s.speed - elapsed
            if slack > 0:
                time.sleep(slack)
        wall = time.perf_counter() - iter_t0
        pace.append((sim_s, wall))
        while len(pace) > 1 and sum(w for _, w in pace) > 1.0:
            pace.popleft()
        s.emit_frame(round(sum(s_ for s_, _ in pace) / max(sum(w for _, w in pace), 1e-9), 3))
        if not n:
            time.sleep(0.05)
