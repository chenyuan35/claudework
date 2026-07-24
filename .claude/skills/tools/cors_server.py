#!/usr/bin/env python3
"""Local, stop-file-controlled CORS static server for browser publishing skills."""

from __future__ import annotations

import argparse
import http.server
import os
import socketserver
from pathlib import Path


class CorsStaticHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def log_message(self, _format: str, *_args: object) -> None:
        # This helper is intentionally quiet; callers have their own task log.
        return


class ReusableThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(root: Path, port_file: Path, stop_file: Path) -> None:
    root = root.resolve()
    port_file.parent.mkdir(parents=True, exist_ok=True)
    os.chdir(root)
    with ReusableThreadingServer(("127.0.0.1", 0), CorsStaticHandler) as server:
        server.timeout = 0.25
        port_file.write_text(str(server.server_port), encoding="utf-8")
        while not stop_file.exists():
            server.handle_request()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--port-file", required=True)
    parser.add_argument("--stop-file", required=True)
    args = parser.parse_args()
    serve(Path(args.root), Path(args.port_file), Path(args.stop_file))


if __name__ == "__main__":
    main()
