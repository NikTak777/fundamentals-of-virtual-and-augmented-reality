"""Локальный сервер для стенда. Нужен Python 3.8+, сторонних пакетов нет."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Local server for the AR lab")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    # Раздаём только папку стенда, независимо от текущего каталога терминала.
    handler = partial(SimpleHTTPRequestHandler, directory=str(Path(__file__).resolve().parent))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError as error:
        print(f"Cannot start server: {error}")
        print("Try another port: python serve.py --port 8001")
        return 1
    print(f"Open in a browser: http://localhost:{args.port}", flush=True)
    print(f"Marker for printing: http://localhost:{args.port}/marker.html", flush=True)
    print("Keep this window open. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
