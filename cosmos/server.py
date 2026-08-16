from __future__ import annotations

import json
import os
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlparse

from .adapters import health
from .engine import CosmosEngine


ROOT = Path(__file__).resolve().parent.parent

STATE = Path(
    os.environ.get(
        "COSMOS_STATE",
        str(
            Path.home()
            / ".local/share/cosmos"
        ),
    )
)

ENGINE = CosmosEngine(STATE)

REGISTRY = json.loads(
    (
        Path(__file__).resolve().parent
        / "registry.json"
    ).read_text(
        encoding="utf-8"
    )
)


class Handler(BaseHTTPRequestHandler):
    server_version = "Cosmos/0.1"

    def send_json(self, status, payload):
        data = json.dumps(
            payload,
            indent=2,
        ).encode()

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json",
        )
        self.send_header(
            "Content-Length",
            str(len(data)),
        )
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            data = (
                ROOT
                / "static/index.html"
            ).read_bytes()

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8",
            )
            self.send_header(
                "Content-Length",
                str(len(data)),
            )
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/api/repos":
            self.send_json(
                200,
                REGISTRY,
            )
            return

        if path.startswith("/api/repos/") \
           and path.endswith("/health"):

            name = path[
                len("/api/repos/"):
                -len("/health")
            ].strip("/")

            self.send_json(
                200,
                health(name),
            )
            return

        if path.startswith("/api/task/"):
            task_id = path.rsplit(
                "/",
                1,
            )[-1]

            result = (
                STATE
                / "tasks"
                / task_id
                / "result.json"
            )

            if not result.exists():
                self.send_json(
                    404,
                    {
                        "error":
                            "task_not_found",
                    },
                )
                return

            self.send_json(
                200,
                json.loads(
                    result.read_text(
                        encoding="utf-8"
                    )
                ),
            )
            return

        self.send_json(
            404,
            {
                "error": "not_found",
            },
        )

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/request":
            self.send_json(
                404,
                {
                    "error": "not_found",
                },
            )
            return

        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )

        if length <= 0 or length > 1_000_000:
            self.send_json(
                400,
                {
                    "error":
                        "invalid_content_length",
                },
            )
            return

        try:
            payload = json.loads(
                self.rfile.read(
                    length
                )
            )

            request = str(
                payload.get(
                    "request",
                    "",
                )
            ).strip()

        except Exception:
            self.send_json(
                400,
                {
                    "error":
                        "invalid_json",
                },
            )
            return

        if not request:
            self.send_json(
                400,
                {
                    "error":
                        "request_required",
                },
            )
            return

        result = ENGINE.execute(
            request
        )

        self.send_json(
            200,
            result,
        )


def main():
    host = os.environ.get(
        "COSMOS_HOST",
        "127.0.0.1",
    )

    port = int(
        os.environ.get(
            "COSMOS_PORT",
            "8787",
        )
    )

    print(
        f"Cosmos listening on "
        f"http://{host}:{port}"
    )

    ThreadingHTTPServer(
        (host, port),
        Handler,
    ).serve_forever()


if __name__ == "__main__":
    main()
