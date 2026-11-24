"""Unit tests for the agent tools that need no model (stdlib only).

    python3 -m unittest discover -s tests -v

fetch_url is exercised against a loopback http.server: no real network.
"""
from __future__ import annotations

import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.tools import SPECS, Toolbox  # noqa: E402

PAGE = """<!doctype html>
<html>
<head><title>T</title><style>.x { color: red; }</style></head>
<body>
<script>var secret = "SCRIPT_SECRET";</script>
<style>.hidden { display: none; }</style>
<p>Hello &amp; welcome</p>
<div>Second line</div>
</body>
</html>"""

BIG = "<html><body><p>" + ("word " * 3000) + "</p></body></html>"


class _Page(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/big":
            body, ctype = BIG, "text/html; charset=utf-8"
        elif self.path == "/json":
            body, ctype = '{"x": "<b>bold</b>"}', "application/json"
        else:
            body, ctype = PAGE, "text/html; charset=utf-8"
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # keep the test output clean
        pass


def _tools() -> Toolbox:
    return Toolbox(cwd=Path("."), approve=lambda kind, preview: True, log=lambda label, text: None)


class FetchUrlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Page)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_success_returns_readable_text_without_scripts_or_tags(self):
        text = _tools().t_fetch_url(f"{self.base}/")
        self.assertIn("Hello & welcome", text)
        self.assertIn("Second line", text)
        self.assertNotIn("SCRIPT_SECRET", text)
        self.assertNotIn("color: red", text)
        self.assertNotIn("display: none", text)
        self.assertNotIn("<p>", text)
        self.assertNotIn("<script", text)

    def test_long_page_is_truncated_with_marker(self):
        out = _tools().t_fetch_url(f"{self.base}/big")
        self.assertLessEqual(len(out), 9000)
        self.assertIn("chars cut", out)

    def test_connection_refused_returns_graceful_error(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        result = _tools().t_fetch_url(f"http://127.0.0.1:{port}/")
        self.assertTrue(result.startswith("error: fetch failed"), result)
        self.assertNotIn("Traceback", result)

    def test_non_html_response_is_not_tag_stripped(self):
        out = _tools().t_fetch_url(f"{self.base}/json")
        self.assertIn('{"x": "<b>bold</b>"}', out)

    def test_non_http_scheme_is_refused_without_reading(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("TOP_SECRET_FILE_CONTENT")
            path = fh.name
        try:
            result = _tools().t_fetch_url(f"file://{path}")
        finally:
            Path(path).unlink()
        self.assertTrue(result.startswith("error:"), result)
        self.assertNotIn("TOP_SECRET_FILE_CONTENT", result)


class FetchUrlSpecTests(unittest.TestCase):
    def test_spec_registered_with_required_url(self):
        specs = [s["function"] for s in SPECS if s["function"]["name"] == "fetch_url"]
        self.assertEqual(len(specs), 1)
        self.assertIn("url", specs[0]["parameters"]["required"])
        self.assertIn("url", specs[0]["parameters"]["properties"])
        self.assertIn("opt-in", specs[0]["description"].lower())


if __name__ == "__main__":
    unittest.main()
