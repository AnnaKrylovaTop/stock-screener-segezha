from __future__ import annotations

import socket
import subprocess
import sys
import time
from contextlib import closing

import requests
import webview


def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.getsockname()[1]


def wait_for_server(port: int, timeout: int = 20) -> None:
    url = f"http://localhost:{port}"
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError("Streamlit server did not start in time")


def main() -> None:
    port = find_free_port()
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    process = subprocess.Popen(cmd)
    try:
        wait_for_server(port)
        webview.create_window("AI Hedge Assistant", f"http://localhost:{port}")
        webview.start()
    finally:
        process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()
