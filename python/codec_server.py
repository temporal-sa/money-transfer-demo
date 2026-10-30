"""A local Codec Server, so the Temporal UI on the dev server can show encrypted payloads.

    poetry run python codec_server.py        # http://127.0.0.1:8089

Then in the Temporal UI: Codec Server (bottom left) > endpoint http://127.0.0.1:8089, access token off.
The decrypted data reaches only your browser; the server keeps the ciphertext.
Uses the same key as codec.py. Local demos only: it answers localhost origins and nothing else.
"""

import asyncio
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from google.protobuf import json_format
from temporalio.api.common.v1 import Payloads

from codec import EncryptionCodec

codec = EncryptionCodec()
PORT = int(os.getenv("CODEC_PORT", "8089"))


class Handler(BaseHTTPRequestHandler):
    def cors(self) -> None:
        origin = self.headers.get("Origin", "")
        if urlparse(origin).hostname in ("localhost", "127.0.0.1"):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Namespace, Authorization")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_POST(self) -> None:
        # The UI adds a query string (?preserveStorageRefs=true), so match on the path alone.
        fn = {"/decode": codec.decode, "/encode": codec.encode}.get(urlparse(self.path).path)
        if not fn:
            self.send_response(404)
            self.end_headers()
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        payloads = json_format.Parse(body, Payloads()).payloads
        out = json_format.MessageToJson(Payloads(payloads=asyncio.run(fn(payloads)))).encode()
        self.send_response(200)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)


if __name__ == "__main__":
    print(f"Codec server on http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
