"""Unit tests for the router (stdlib only, no model needed).

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from router.compose import HEADER, Composer, conversation_key  # noqa: E402
from router.detect import Detection  # noqa: E402
from router.intent import KeywordClassifier  # noqa: E402
from router.proxy import make_handler  # noqa: E402
from router.registry import Registry, Settings  # noqa: E402
from router.router import Router  # noqa: E402


def make_router(**overrides) -> Router:
    reg = Registry.load()
    settings = Settings(backend="keywords", magika=False, **overrides)
    return Router(registry=reg, settings=settings, classifier=KeywordClassifier(reg), detector=None)


class _FakeDetector:
    """Stand-in for Magika: real Magika is an optional dependency."""

    available = True

    def __init__(self, detections):
        self._detections = detections

    def detect_text(self, text):
        return []

    def detect_files(self, paths):
        return self._detections


def make_magika_router(detections) -> Router:
    reg = Registry.load()
    settings = Settings(backend="keywords")   # magika defaults True
    return Router(registry=reg, settings=settings,
                  classifier=KeywordClassifier(reg), detector=_FakeDetector(detections))


def user(text: str) -> dict:
    return {"role": "user", "content": text}


def assistant(text: str) -> dict:
    return {"role": "assistant", "content": text}


class RegistryTest(unittest.TestCase):
    def test_registry_is_valid(self):
        self.assertEqual(Registry.load().validate(), [])

    def test_skill_frontmatter_is_stripped(self):
        self.assertFalse(Registry.load().addons["docker"].text.startswith("---"))


class RouterTest(unittest.TestCase):
    def setUp(self):
        self.router = make_router()

    def test_sysadmin_prompt_gets_default_addon(self):
        d = self.router.route(["il servizio nginx non parte, cosa controllo con systemctl?"])
        self.assertEqual(d.category, "sysadmin")
        self.assertIn("linux-commands", [p.addon for p in d.addons])

    def test_unrelated_prompt_makes_no_guess(self):
        d = self.router.route(["mi consigli un libro da leggere?"])
        self.assertIsNone(d.category)
        self.assertEqual(d.addons, [])

    def test_router_reads_recent_history(self):
        # the last message alone says nothing; the previous one sets the topic
        d = self.router.route(["ho un problema con pacman su arch", "e adesso cosa faccio?"])
        self.assertEqual(d.category, "sysadmin")

    def test_topic_change_in_last_message_beats_history(self):
        d = self.router.route(["correggi il file bugtest.py", "ora sposta il file in home"])
        self.assertEqual(d.category, "sysadmin")
        self.assertNotIn("python", [p.addon for p in d.addons])

    def test_pure_follow_up_inherits_previous_topic(self):
        d = self.router.route(["pacman da errore di chiavi", "e adesso cosa faccio?"])
        self.assertEqual(d.category, "sysadmin")

    def test_ctf_prompt_routes_to_ctf_triage(self):
        d = self.router.route(["trova il flag in questo binario"])
        self.assertEqual(d.category, "ctf")
        self.assertIn("ctf-triage", [p.addon for p in d.addons])

    def test_web_ctf_prompt_routes_to_ctf(self):
        d = self.router.route(["bypassa la login con SQL injection"])
        self.assertEqual(d.category, "ctf")

    def test_non_ctf_prompt_is_not_captured_by_ctf(self):
        d = self.router.route(["mi consigli un libro giallo?"])
        self.assertIsNone(d.category)
        self.assertEqual(d.addons, [])

    def test_already_loaded_addons_are_not_repeated(self):
        d = self.router.route(["systemctl restart nginx non va"], loaded={"linux-commands"})
        self.assertNotIn("linux-commands", [p.addon for p in d.addons])

    def test_token_budget_is_enforced(self):
        d = make_router(max_addon_tokens=100).route(["systemctl e journalctl su debian"])
        self.assertEqual(d.addons, [])
        self.assertIn("linux-commands", d.skipped)

    def test_regex_prompt_routes_to_regex(self):
        d = self.router.route(["come scrivo una regex con lookahead per estrarre l'anno?"])
        self.assertIn("regex", [p.addon for p in d.addons])

    def test_unrelated_prompt_does_not_pick_regex(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("regex", [p.addon for p in d.addons])

    def test_git_prompt_routes_to_git(self):
        d = self.router.route(["come faccio il rebase del branch sul main?"])
        self.assertIn("git", [p.addon for p in d.addons])

    def test_unrelated_prompt_does_not_pick_git(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("git", [p.addon for p in d.addons])

    def test_sql_prompt_routes_to_sql(self):
        d = self.router.route(["scrivi una query con JOIN e GROUP BY su postgres"])
        self.assertIn("sql", [p.addon for p in d.addons])

    def test_unrelated_prompt_does_not_pick_sql(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("sql", [p.addon for p in d.addons])


class MagikaRoutingTest(unittest.TestCase):
    """A binary with no textual hint must still reach ctf-triage."""

    def test_binary_labels_route_to_ctf_triage(self):
        for label in ("elf", "pebin", "wasm"):
            with self.subTest(label=label):
                router = make_magika_router([Detection(label, 0.99, "file:chall")])
                d = router.route(["analizza questo file"], files=[Path("chall")])
                self.assertEqual(d.category, "ctf")
                self.assertIn("ctf-triage", [p.addon for p in d.addons])
                pick = next(p for p in d.addons if p.addon == "ctf-triage")
                self.assertTrue(pick.reason.startswith("magika:"))

    def test_image_label_does_not_route(self):
        router = make_magika_router([Detection("png", 0.99, "file:img.png")])
        d = router.route(["analizza questo file"], files=[Path("img.png")])
        self.assertIsNone(d.category)
        self.assertEqual(d.addons, [])


class ComposerTest(unittest.TestCase):
    def setUp(self):
        self.composer = Composer(make_router())

    def test_user_prompt_stays_intact_at_the_end(self):
        prompt = "come uso systemctl per riavviare un servizio?"
        out, _ = self.composer.process([user(prompt)])
        self.assertTrue(out[-1]["content"].startswith(HEADER))
        self.assertTrue(out[-1]["content"].endswith(prompt))

    def test_prefix_is_stable_across_turns(self):
        """KV cache rule: what was sent once must be resent byte-identical."""
        conv = [user("come uso systemctl per riavviare nginx?")]
        out1, _ = self.composer.process(conv)
        conv += [assistant("sudo systemctl restart nginx"), user("e come scrivo uno script python per farlo?")]
        out2, d2 = self.composer.process(conv)
        self.assertEqual(out2[: len(out1)], out1)                 # old prefix untouched
        self.assertIn("python", [p.addon for p in d2.addons])      # new add-on at the end
        self.assertNotIn("<addon", out2[1]["content"])            # assistant turn untouched

    def test_addons_are_never_unloaded_mid_conversation(self):
        conv = [user("journalctl -u nginx mostra errori")]
        self.composer.process(conv)
        conv += [assistant("..."), user("grazie, ciao")]
        out, _ = self.composer.process(conv)
        self.assertIn('<addon id="linux-commands">', out[0]["content"])

    def test_retry_of_same_turn_is_identical(self):
        conv = [user("chmod e chown ricorsivi su una cartella")]
        out1, d1 = self.composer.process(conv)
        out2, d2 = self.composer.process(conv)
        self.assertEqual(out1, out2)
        self.assertIsNotNone(d1)
        self.assertIsNone(d2)                                      # not re-routed

    def test_new_conversation_starts_clean(self):
        self.composer.process([user("systemctl status sshd")])
        out, d = self.composer.process([user("mi consigli un film?")])
        self.assertNotIn("<addon", out[0]["content"])
        self.assertIsNone(d.category)

    def test_conversation_key_ignores_later_turns(self):
        a = [user("x")]
        self.assertEqual(conversation_key(a), conversation_key([*a, assistant("y"), user("z")]))

    def test_multipart_content_is_supported(self):
        msg = {"role": "user", "content": [{"type": "text", "text": "systemctl restart sshd"}]}
        out, _ = self.composer.process([msg])
        self.assertEqual(out[0]["content"][0]["type"], "text")
        self.assertTrue(out[0]["content"][0]["text"].startswith(HEADER))
        self.assertEqual(out[0]["content"][1:], msg["content"])


class _FakeLlama(BaseHTTPRequestHandler):
    received: list[dict] = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _FakeLlama.received.append(body)
        out = json.dumps({"choices": [{"message": {"role": "assistant", "content": "ok"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")


class ProxyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLlama)
        cls.proxy = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            make_handler(Composer(make_router()), "127.0.0.1", cls.upstream.server_address[1]),
        )
        for srv in (cls.upstream, cls.proxy):
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.proxy.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        for srv in (cls.proxy, cls.upstream):
            srv.shutdown()
            srv.server_close()

    def test_chat_completion_is_routed_and_forwarded(self):
        payload = {"model": "base", "messages": [user("systemctl restart nginx non funziona")]}
        req = urllib.request.Request(f"{self.base}/v1/chat/completions", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.headers["X-Router-Category"], "sysadmin")
            self.assertEqual(json.loads(resp.read())["choices"][0]["message"]["content"], "ok")
        sent = _FakeLlama.received[-1]["messages"][-1]["content"]
        self.assertIn('<addon id="linux-commands">', sent)

    def test_other_paths_pass_through(self):
        with urllib.request.urlopen(f"{self.base}/health", timeout=10) as resp:
            self.assertEqual(resp.read(), b"ok")

    def test_status_endpoint(self):
        with urllib.request.urlopen(f"{self.base}/router/status", timeout=10) as resp:
            self.assertIn("linux-commands", json.loads(resp.read())["addons"])


if __name__ == "__main__":
    unittest.main()
