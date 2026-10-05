"""Entry point for the portable app. Run the server and open the browser."""
import multiprocessing
import os
import threading
import time
import webbrowser

import uvicorn
from backend.app import app
from backend.paths import ROOT, ENGINE


def main():
    host = os.environ.get("FEUD_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    url = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, loop="asyncio", http="h11", ws="none"))
    print(f"Feudsolver: {url}\nKeep this window open. Press Ctrl+C to stop.", flush=True)
    print(f"Application folder: {ROOT}\nEngine: {ENGINE}", flush=True)

    def open_when_ready():
        for _ in range(300):
            if server.should_exit:
                return
            if server.started:
                webbrowser.open(url)
                return
            time.sleep(.1)

    if os.environ.get("FEUD_OPEN_BROWSER", "1") != "0":
        threading.Thread(target=open_when_ready, daemon=True).start()
    server.run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
