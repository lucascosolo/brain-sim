import asyncio
import queue
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

from brainsim.telemetry import REPLY_KEYS

UI_DIR = __file__.rsplit("/", 2)[0] + "/ui"



async def _send(ws, msg):
    assert set(msg) == REPLY_KEYS[msg["type"]], msg["type"]
    try:
        await ws.send_json(msg)
    except Exception:
        pass


async def _err(ws, cmd, msg, req):
    await _send(ws, {"type": "error", "cmd": cmd, "msg": msg, "req": req, "run_id": None})


def create_app(cmd_q, frame_q, reply_q):
    socks = set()

    @asynccontextmanager
    async def lifespan(app):
        t1 = asyncio.create_task(_pump(frame_q))
        t2 = asyncio.create_task(_pump(reply_q))
        yield
        t1.cancel()
        t2.cancel()

    app = FastAPI(lifespan=lifespan)

    async def _pump(q):
        loop = asyncio.get_running_loop()
        while True:
            try:
                msg = await loop.run_in_executor(None, q.get, True, 0.5)
            except queue.Empty:
                continue
            for ws in list(socks):
                try:
                    await ws.send_json(msg)
                except Exception:
                    socks.discard(ws)

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        if ws.headers.get("origin") != "http://" + ws.headers.get("host", ""):
            await ws.close(code=1008)
            return
        await ws.accept()
        client_id = secrets.token_hex(4)
        await _send(ws, {"type": "hello", "client_id": client_id})
        socks.add(ws)
        cmd_q.put({"cmd": "layout"})
        try:
            while True:
                cmd = await ws.receive_json()
                if not isinstance(cmd, dict) or not isinstance(cmd.get("cmd"), str):
                    await _err(ws, None, "command must be an object with a string cmd", None)
                    continue
                if "req" in cmd:
                    cmd["req"] = f"{client_id}:{str(cmd['req'])[:32]}"
                try:
                    cmd_q.put_nowait(cmd)
                except queue.Full:
                    await _err(ws, cmd.get("cmd"), "command queue full", cmd.get("req"))
        except Exception:
            pass
        finally:
            socks.discard(ws)

    app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
    return app
