"""Local static server with Vercel-style clean URLs."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CLEAN_URLS = {
    "/": "index.html",
    "/index": "index.html",
    "/login-seeker": "login-seeker.html",
    "/login-employer": "login-employer.html",
    "/seeker": "seeker.html",
    "/employer": "employer.html",
}


class FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path.endswith("/") and path != "/":
            path = path.rstrip("/")
        mapped = CLEAN_URLS.get(path)
        if mapped:
            query = ""
            if "?" in self.path:
                query = "?" + self.path.split("?", 1)[1]
            self.path = f"/{mapped}{query}"
        super().do_GET()

    def log_message(self, format: str, *args) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve frontend with clean URLs.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5500, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), FrontendHandler)
    print(f"Frontend running at http://{args.host}:{args.port}/", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
