"""Unit tests for the SearXNG-first web_search tool (stdlib only, no network).

A loopback http.server acts as a fake SearXNG; a closed port stands for a
stopped container.

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import http.server
import json
import socket
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import tools  # noqa: E402
from agent.tools import Toolbox, _searxng_search  # noqa: E402


class _FakeSearxng(http.server.BaseHTTPRequestHandler):
    payload = {
        "results": [
            {
                "title": "Primo risultato",
                "url": "https://example.test/one",
                "content": "<b>grassetto</b> e &amp; <i>corsivo</i>",
            },
            {
                "title": "Senza snippet",
                "url": "https://example.test/two",
                "content": "",
            },
        ]
    }

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        body = json.dumps(self.payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # silence the test output
        pass


def _closed_port() -> int:
    """Bind an ephemeral port, then close it: nothing listens there."""
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


class _FakeServer:
    @classmethod
    def start(cls) -> str:
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), _FakeSearxng)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        return f"http://{host}:{port}/search"

    @classmethod
    def stop(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)


class SearxngSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_url = _FakeServer.start()

    @classmethod
    def tearDownClass(cls) -> None:
        _FakeServer.stop()

    def test_returns_results_and_strips_html(self) -> None:
        results = _searxng_search("test", base_url=self.base_url, timeout=2)
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 2)
        first = results[0]
        self.assertEqual(first["title"], "Primo risultato")
        self.assertEqual(first["url"], "https://example.test/one")
        self.assertIn("grassetto", first["snippet"])
        self.assertIn("corsivo", first["snippet"])
        self.assertIn("&", first["snippet"])
        self.assertNotIn("<b>", first["snippet"])
        self.assertNotIn("&amp;", first["snippet"])

    def test_empty_snippet_falls_back_to_title(self) -> None:
        results = _searxng_search("test", base_url=self.base_url, timeout=2)
        self.assertEqual(results[1]["snippet"], "Senza snippet")

    def test_connection_refused_returns_none(self) -> None:
        port = _closed_port()
        url = f"http://127.0.0.1:{port}/search"
        self.assertIsNone(_searxng_search("test", base_url=url, timeout=2))


class WebSearchToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_url = _FakeServer.start()

    @classmethod
    def tearDownClass(cls) -> None:
        _FakeServer.stop()

    def _toolbox(self) -> Toolbox:
        return Toolbox(cwd=Path.cwd(), approve=lambda _k, _p: True, log=lambda _l, _t: None)

    def test_searxng_first_formats_results(self) -> None:
        with mock.patch.object(tools, "SEARXNG_URL", self.base_url):
            out = self._toolbox().t_web_search("test")
        self.assertIn("1. Primo risultato", out)
        self.assertIn("https://example.test/one", out)
        self.assertIn("grassetto", out)
        self.assertNotIn("not installed", out)
        self.assertNotIn("Traceback", out)

    def test_falls_back_to_ddgs_when_searxng_down(self) -> None:
        port = _closed_port()
        url = f"http://127.0.0.1:{port}/search"
        # Force the ddgs import to fail: no network, deterministic message.
        with mock.patch.object(tools, "SEARXNG_URL", url), \
             mock.patch.dict(sys.modules, {"ddgs": None, "duckduckgo_search": None}):
            out = self._toolbox().t_web_search("test")
        self.assertIsInstance(out, str)
        self.assertIn("not installed", out)
        self.assertNotIn("Traceback", out)


if __name__ == "__main__":
    unittest.main()
