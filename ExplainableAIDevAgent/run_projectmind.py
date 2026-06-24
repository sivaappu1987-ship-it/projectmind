import os
import socket
import sys
from typing import Optional


HOST = os.getenv("PROJECTMIND_HOST", "127.0.0.1")
PREFERRED_PORTS = [5174, 8010, 8765, 9000, 0]


def can_bind(port: int) -> Optional[int]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((HOST, port))
            return sock.getsockname()[1]
    except OSError:
        return None


def choose_port() -> int:
    for port in PREFERRED_PORTS:
        available = can_bind(port)
        if available:
            return available
    raise RuntimeError(
        "Windows refused every local port ProjectMind tried. "
        "Restart your terminal and try again, or run as Administrator once."
    )


def main() -> int:
    try:
        import uvicorn
    except ImportError:
        print("Uvicorn is not installed. Run: pip install -r requirements.txt")
        return 1

    port = choose_port()
    url = f"http://{HOST}:{port}"

    print("")
    print("ProjectMind AI is starting.")
    print(f"Open this URL: {url}")
    print("Press Ctrl+C to stop the server.")
    print("")

    try:
        uvicorn.run("main:app", host=HOST, port=port, reload=False)
    except OSError as exc:
        print("")
        print(f"Windows blocked the server socket: {exc}")
        print("Try closing other local servers, then run start_projectmind.bat again.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
