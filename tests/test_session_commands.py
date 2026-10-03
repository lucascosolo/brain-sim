"""PRD section 3: worker.Session, driven directly (no threads, no real queues)."""
from brainsim import worker
from brainsim.engine import Engine
from brainsim.telemetry import REPLY_KEYS


def _session(seed=1, batch=50):
    replies, frames = [], []
    e = Engine(seed=seed)
    s = worker.Session(e, replies.append, frames.append, batch=batch)
    return s, e, replies, frames


def _results(replies, cmd=None):
    return [r for r in replies if r["type"] == "result" and (cmd is None or r.get("cmd") == cmd)]


def test_present_while_paused_accepted_no_started_event_until_advance():
    s, e, replies, frames = _session()
    s.handle({"cmd": "pause"})
    replies.clear()
    s.handle({"cmd": "present", "pattern": 0, "ticks": 50, "req": "p1"})
    accepted = _results(replies, "present")
    assert accepted and accepted[0]["status"] == "accepted"
    n = s.advance()
    assert n == 0
    frame = s.emit_frame(1.0)
    assert frame["stim_events"] == []

    # now step it: FIFO step request executes and the stim starts
    replies.clear()
    s.handle({"cmd": "step", "ticks": 1, "req": "s1"})
    step_accepted = _results(replies, "step")
    assert step_accepted[0]["status"] == "accepted"
    t_target = step_accepted[0]["t_target"]
    assert t_target == e.t + 1
    s.advance()
    frame = s.emit_frame(1.0)
    started = [ev for ev in frame["stim_events"] if ev["event"] == "started"]
    assert len(started) == 1
    executed = [r for r in replies if r["type"] == "result" and r.get("req") == "s1"
                and r["status"] == "executed"]
    assert executed[0]["status"] == "executed"
    assert executed[0]["t"] == t_target


def test_present_in_sleep_rejected_sense_gated_with_t():
    s, e, replies, frames = _session()
    s.handle({"cmd": "sleep", "on": True})
    replies.clear()
    s.handle({"cmd": "present", "pattern": 0, "ticks": 50, "req": "p2"})
    res = _results(replies, "present")[0]
    assert res["status"] == "rejected"
    assert res["reason"] == "sense_gated"
    assert res["t"] == e.t


def test_inject_ctx_cells_in_sleep_accepted():
    s, e, replies, frames = _session()
    ctx_start = e.net.region_slice["ctx"].start
    s.handle({"cmd": "sleep", "on": True})
    replies.clear()
    s.handle({"cmd": "inject", "ids": [ctx_start], "amp": 5.0, "ticks": 20, "req": "i1"})
    res = _results(replies, "inject")[0]
    assert res["status"] == "accepted"
    assert res["n_cells"] == 1


def test_sleep_when_already_asleep_changed_false_clock_reset_true():
    s, e, replies, frames = _session()
    s.handle({"cmd": "sleep", "on": True, "req": "sl1"})
    first = _results(replies, "sleep")[0]
    assert first["changed"] is True
    assert first["phase_before"] == "wake"
    assert first["phase_after"] == "sleep"
    assert first["phase_clock_reset"] is True
    replies.clear()
    s.handle({"cmd": "sleep", "on": True, "req": "sl2"})
    second = _results(replies, "sleep")[0]
    assert second["changed"] is False
    assert second["phase_before"] == "sleep"
    assert second["phase_after"] == "sleep"
    assert second["phase_clock_reset"] is True


def test_run_pause_speed_accepted_plus_status_with_t():
    s, e, replies, frames = _session()
    for cmd, extra in (("run", {}), ("pause", {}), ("speed", {"factor": 2.0})):
        replies.clear()
        s.handle(dict(cmd=cmd, req=f"{cmd}1", **extra))
        statuses = [r for r in replies if r["type"] == "status"]
        assert statuses and statuses[0]["t"] == e.t
        res = _results(replies, cmd)
        assert res and res[0]["status"] == "accepted"
        if cmd == "speed":
            assert res[0]["factor"] == 2.0


def test_layout_replies_in_order_with_run_id():
    s, e, replies, frames = _session()
    replies.clear()
    s.handle({"cmd": "layout"})
    types = [r["type"] for r in replies]
    assert types == ["layout", "config", "status", "stimlog"]
    for r in replies:
        assert r["run_id"] == s.run_id


def test_req_echoed_on_every_result():
    s, e, replies, frames = _session()
    s.handle({"cmd": "run", "req": "echo1"})
    res = _results(replies, "run")
    assert res[0]["req"] == "echo1"


def test_invalid_command_rejected_with_reason():
    s, e, replies, frames = _session()
    s.handle({"cmd": "inject", "ids": "bad", "ticks": 10, "req": "bad1"})
    res = _results(replies, "inject")
    assert res and res[0]["status"] == "rejected"
    assert res[0]["reason"].startswith("invalid: ")


def test_step_fifo_two_requests_batch_50():
    s, e, replies, frames = _session(batch=50)
    s.handle({"cmd": "pause"})
    replies.clear()
    s.handle({"cmd": "step", "ticks": 30, "req": "r1"})
    s.handle({"cmd": "step", "ticks": 40, "req": "r2"})
    s.advance()
    executed_after_1 = {r["req"] for r in replies if r["type"] == "result" and r["status"] == "executed"}
    assert executed_after_1 == {"r1"}
    replies.clear()
    s.advance()
    executed_after_2 = {r["req"] for r in replies if r["type"] == "result" and r["status"] == "executed"}
    assert executed_after_2 == {"r2"}
    r2_result = [r for r in replies if r["req"] == "r2"][0]
    assert r2_result["t"] == e.t


def test_history_expiry_66_presents_keeps_64_drops_first_two():
    s, e, replies, frames = _session()
    stim_ids = []
    for _ in range(66):
        replies.clear()
        s.handle({"cmd": "present", "pattern": 0, "ticks": 1})
        res = _results(replies, "present")[0]
        stim_ids.append(res["stim_id"])
        s.advance()
    assert len(e.stimlog) == 64
    logged = {r["stim_id"] for r in e.stimlog}
    assert stim_ids[0] not in logged
    assert stim_ids[1] not in logged


def test_every_reply_keys_match_reply_keys():
    s, e, replies, frames = _session()
    s.handle({"cmd": "layout"})
    s.handle({"cmd": "present", "pattern": 0, "ticks": 5, "req": "p"})
    s.advance()
    for r in replies:
        assert set(r) == REPLY_KEYS[r["type"]], r["type"]


def test_257th_active_inject_rejected_too_many_active():
    from brainsim import params
    stim_active_max = getattr(params, "STIM_ACTIVE_MAX", 256)
    s, e, replies, frames = _session()
    s.handle({"cmd": "pause"})
    for i in range(stim_active_max):
        replies.clear()
        s.handle({"cmd": "inject", "ids": [i], "amp": 5.0, "ticks": 100000, "req": f"i{i}"})
        res = _results(replies, "inject")[0]
        assert res["status"] == "accepted", (i, res)
    replies.clear()
    s.handle({"cmd": "inject", "ids": [stim_active_max], "amp": 5.0, "ticks": 100000, "req": "over"})
    res = _results(replies, "inject")[0]
    assert res["status"] == "rejected"
    assert res["reason"] == "too_many_active"


def test_second_of_two_large_step_requests_rejected_pending_exceeds():
    s, e, replies, frames = _session()
    s.handle({"cmd": "pause"})
    replies.clear()
    s.handle({"cmd": "step", "ticks": 60000, "req": "big1"})
    first = _results(replies, "step")[0]
    assert first["status"] == "accepted"
    replies.clear()
    s.handle({"cmd": "step", "ticks": 60000, "req": "big2"})
    second = _results(replies, "step")[0]
    assert second["status"] == "rejected"
    assert second["reason"].startswith("invalid: pending step ticks exceed")


def test_two_sessions_different_run_ids_stim_ids_restart_at_one():
    s1, e1, r1, f1 = _session(seed=1)
    s2, e2, r2, f2 = _session(seed=1)
    assert s1.run_id != s2.run_id
    s1.handle({"cmd": "present", "pattern": 0, "ticks": 10, "req": "a"})
    s2.handle({"cmd": "present", "pattern": 0, "ticks": 10, "req": "a"})
    res1 = _results(r1, "present")[0]
    res2 = _results(r2, "present")[0]
    assert res1["stim_id"] == 1
    assert res2["stim_id"] == 1
