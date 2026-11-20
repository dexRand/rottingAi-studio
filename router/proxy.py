"""OpenAI-compatible proxy in front of llama-server (stdlib only).

  client (OpenCode / web UI / curl)
      -> router proxy  :ROUTER_PORT  (public, default 127.0.0.1:8080)
      -> llama-server  :LLAMA_PORT   (internal, always 127.0.0.1:8081)

Every request is forwarded unchanged, except POST .../chat/completions, whose
`messages` go through the Composer (router + add-on injection). Streaming
(SSE) responses are relayed chunk by chunk. The Authorization header is
forwarded, so LLAMA_API_KEY is still enforced by llama-server itself.

Debug endpoints (local only):
  GET  /router/status   registry, settings, per-conversation add-ons
  POST /router/route    {"messages": [...]} -> routing decision, no model call
"""
from __future__ import annotations

import http.client
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .compose import Composer, message_text

log = logging.getLogger("router.proxy")

HOP_BY_HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade",
              "proxy-authorization", "proxy-authenticate", "host", "content-length"}
UPSTREAM_TIMEOUT = 900          # long prompts on CPU can take minutes to prefill
CHUNK = 16384


def make_handler(composer: Composer, upstream_host: str, upstream_port: int) -> type[BaseHTTPRequestHandler]:

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"   # close after each response: simple streaming relay
        server_version = "rottingAi-router"

        def log_message(self, fmt: str, *args) -> None:
            log.debug("%s " + fmt, self.address_string(), *args)

        # --- helpers ----------------------------------------------------------
        def _read_body(self) -> bytes:
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def _is_local(self) -> bool:
            return self.client_address[0] in ("127.0.0.1", "::1")

        def _send_json(self, code: int, obj: object) -> None:
            body = json.dumps(obj, ensure_ascii=False, indent=2).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _forward(self, body: bytes, extra_headers: dict[str, str] | None = None) -> None:
            headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP}
            if body:
                headers["Content-Length"] = str(len(body))
            conn = http.client.HTTPConnection(upstream_host, upstream_port, timeout=UPSTREAM_TIMEOUT)
            try:
                conn.request(self.command, self.path, body=body or None, headers=headers)
                resp = conn.getresponse()
            except OSError as err:
                self._send_json(502, {"error": {"message": f"llama-server unreachable: {err}"}})
                return
            try:
                self.send_response(resp.status, resp.reason)
                for k, v in resp.getheaders():
                    if k.lower() not in HOP_BY_HOP:
                        self.send_header(k, v)
                for k, v in (extra_headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                while chunk := resp.read1(CHUNK):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                log.info("client disconnected")
            finally:
                conn.close()

        # --- routes -------------------------------------------------------------
        def do_GET(self) -> None:
            if self.path == "/router/status" and self._is_local():
                reg = composer.router.registry
                self._send_json(200, {
                    "backend": composer.router.classifier.name,
                    "magika": bool(composer.router.detector and composer.router.detector.available),
                    "settings": vars(composer.router.settings),
                    "addons": {a.id: {"category": a.category, "type": a.type, "tokens": a.tokens}
                               for a in reg.addons.values()},
                    "sessions": composer.sessions(),
                })
                return
            self._forward(b"")

        def do_POST(self) -> None:
            body = self._read_body()
            if self.path == "/router/route" and self._is_local():
                try:
                    payload = json.loads(body or b"{}")
                    texts = [message_text(m) for m in payload.get("messages", []) if m.get("role") == "user"]
                except (ValueError, AttributeError) as err:
                    self._send_json(400, {"error": {"message": str(err)}})
                    return
                self._send_json(200, composer.router.route(texts).to_dict())
                return

            extra = {}
            if self.path.rstrip("/").endswith("/chat/completions"):
                try:
                    payload = json.loads(body)
                    messages = payload.get("messages")
                except ValueError:
                    messages = None             # let llama-server report the error
                if isinstance(messages, list) and messages:
                    new_messages, decision = composer.process(messages)
                    payload["messages"] = new_messages
                    body = json.dumps(payload, ensure_ascii=False).encode()
                    if decision is not None:
                        d = decision.to_dict()
                        log.info("route: category=%s (%.2f) addons=%s backend=%s",
                                 d["category"], d["category_score"],
                                 [a["id"] for a in d["addons"]] or "-", d["backend"])
                        extra["X-Router-Category"] = str(d["category"])
                        extra["X-Router-Addons"] = ",".join(a["id"] for a in d["addons"])
            self._forward(body, extra)

        def do_PUT(self) -> None:
            self._forward(self._read_body())

        def do_DELETE(self) -> None:
            self._forward(self._read_body())

        def do_OPTIONS(self) -> None:
            self._forward(b"")

    return Handler


def serve(composer: Composer, host: str, port: int, upstream_host: str, upstream_port: int) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(composer, upstream_host, upstream_port))
    server.daemon_threads = True
    log.info("router on http://%s:%d -> llama-server http://%s:%d (backend: %s)",
             host, port, upstream_host, upstream_port, composer.router.classifier.name)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
