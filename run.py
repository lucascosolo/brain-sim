import os
import multiprocessing as mp

import uvicorn

from brainsim import worker
from server.app import create_app

if __name__ == "__main__":
    mp.set_start_method("spawn")
    cmd_q = mp.Queue(maxsize=64)
    frame_q = mp.Queue(maxsize=4)
    reply_q = mp.Queue(maxsize=16)
    proc = mp.Process(target=worker.run, args=(cmd_q, frame_q, reply_q), daemon=True)
    proc.start()
    try:
        uvicorn.run(create_app(cmd_q, frame_q, reply_q), host=os.environ.get("BRAINSIM_HOST", "127.0.0.1"), port=8000, log_level="warning")
    finally:
        cmd_q.put({"cmd": "quit"})
        proc.join(timeout=2)
        if proc.is_alive():
            proc.terminate()
