"""PRD section 4: server per-client hello + req namespacing.

Uses fastapi.testclient.TestClient with plain queue.Queue objects standing in for the
worker's queues; a small stub thread answers `layout` commands with a minimal reply so
create_app's per-connection `{"cmd": "layout"}` enqueue does not hang the pumps.

Timeouts terminate the test: `_recv` runs the blocking receive on a daemon thread and
fails from the main thread when nothing arrives, so a wedged socket cannot leave the
test process waiting on a joined thread. Commands reaching the stub worker are awaited
on a condition variable with a deadline, not polled. No `pkill`, no shared ports.
"""
import json
import queue
import threading

import pytest

pytest.importorskip("fastapi.testclient", reason="fastapi.testclient needs httpx2 installed")
from fastapi.testclient import TestClient  # noqa: E402

ORIGIN = {"origin": "http://testserver"}  # the server enforces same-origin on /ws

from server.app import create_app  # noqa: E402

RECV_TIMEOUT = 2.0
CMD_TIMEOUT = 2.0
QUIET_PERIOD = 0.2


def _recv(ws, timeout=RECV_TIMEOUT):
    """Receive one JSON message or fail the test after `timeout` seconds.

    The receive runs on a daemon thread. On timeout the thread is abandoned, not joined:
    the session's `__exit__` closes the underlying stream, which unblocks it, and a daemon
    thread never holds up interpreter exit.
    """
    box = queue.Queue(maxsize=1)

    def run():
        try:
            box.put(("ok", ws.receive_json()))
        except BaseException as exc:  # noqa: BLE001 - surfaced on the main thread
            box.put(("err", exc))

    threading.Thread(target=run, daemon=True).start()
    try:
        kind, val = box.get(timeout=timeout)
    except queue.Empty:
        pytest.fail(f"no message received within {timeout}s")
    if kind == "err":
        raise val
    return val


class _Stub:
    """A stand-in worker: records every command and answers `layout` minimally."""

    def __init__(self):
        self.cmd_q, self.frame_q, self.reply_q = queue.Queue(), queue.Queue(), queue.Queue()
        self.received = []
        self.cv = threading.Condition()
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            try:
                cmd = self.cmd_q.get(timeout=0.05)
            except queue.Empty:
                continue
            with self.cv:
                self.received.append(cmd)
                self.cv.notify_all()
            if isinstance(cmd, dict) and cmd.get("cmd") == "layout":
                self.reply_q.put({"type": "layout", "regions": {}, "x": [], "y": [],
                                  "region": [], "is_exc": [], "synapse_sample": [],
                                  "patterns": [], "run_id": "run-test"})

    def __enter__(self):
        self.thread.start()
        self.app = create_app(self.cmd_q, self.frame_q, self.reply_q)
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self.thread.join(timeout=1.0)
        assert not self.thread.is_alive(), "stub worker thread did not stop"
        return False

    def wait_cmd(self, pred, timeout=CMD_TIMEOUT):
        """Return the first recorded command satisfying `pred`, or fail after `timeout`."""
        with self.cv:
            found = self.cv.wait_for(
                lambda: any(isinstance(c, dict) and pred(c) for c in self.received), timeout)
            if not found:
                pytest.fail(f"no command matching predicate reached the worker within {timeout}s; "
                            f"received: {self.received!r}")
            return next(c for c in self.received if isinstance(c, dict) and pred(c))

    def count(self):
        with self.cv:
            return len(self.received)


def test_each_socket_gets_distinct_hello_client_id():
    with _Stub() as stub:
        client = TestClient(stub.app)
        with client.websocket_connect("/ws", headers=ORIGIN) as ws1, \
                client.websocket_connect("/ws", headers=ORIGIN) as ws2:
            hello1 = _recv(ws1)
            hello2 = _recv(ws2)
            assert hello1["type"] == "hello"
            assert hello2["type"] == "hello"
            assert isinstance(hello1["client_id"], str) and hello1["client_id"]
            assert hello1["client_id"] != hello2["client_id"]


def test_req_namespaced_by_client_id_and_differs_per_socket():
    with _Stub() as stub:
        client = TestClient(stub.app)
        with client.websocket_connect("/ws", headers=ORIGIN) as ws1, \
                client.websocket_connect("/ws", headers=ORIGIN) as ws2:
            hello1 = _recv(ws1)
            hello2 = _recv(ws2)
            cid1, cid2 = hello1["client_id"], hello2["client_id"]
            assert cid1 != cid2
            ws1.send_json({"cmd": "status", "req": "1"})
            ws2.send_json({"cmd": "status", "req": "1"})

            def is_status(c):
                return c.get("cmd") == "status"

            # Both status commands must reach the worker; wait for the second one.
            stub.wait_cmd(lambda c: is_status(c) and c.get("req") == f"{cid2}:1")
            statuses = [c for c in stub.received if isinstance(c, dict) and is_status(c)]
            reqs = sorted(c.get("req") for c in statuses)
            assert reqs == sorted([f"{cid1}:1", f"{cid2}:1"]), reqs
            assert reqs[0] != reqs[1]
            # The bare client-side identifier must never reach the worker unprefixed.
            assert all(c.get("req") != "1" for c in statuses)


def test_non_object_payload_gets_error_and_is_not_enqueued():
    with _Stub() as stub:
        client = TestClient(stub.app)
        with client.websocket_connect("/ws", headers=ORIGIN) as ws:
            _recv(ws)  # hello
            # The per-connection layout request is the only command expected so far.
            stub.wait_cmd(lambda c: c.get("cmd") == "layout")
            n_before = stub.count()
            ws.send_text(json.dumps("just a string"))
            msg = _recv(ws)
            assert msg["type"] == "error"
            # A short quiet period: nothing further may reach the worker.
            with stub.cv:
                arrived = stub.cv.wait_for(lambda: len(stub.received) > n_before, QUIET_PERIOD)
            assert not arrived, stub.received[n_before:]
