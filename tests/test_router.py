"""Unit tests for the router (stdlib only, no model needed).

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import sklearn  # noqa: F401
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from router.compose import HEADER, Composer, conversation_key  # noqa: E402
from router.detect import Detection  # noqa: E402
from router.intent import KeywordClassifier  # noqa: E402
from router.proxy import make_handler  # noqa: E402
from router.registry import Registry, Settings, estimate_tokens  # noqa: E402
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


class TfidfClassifierTest(unittest.TestCase):
    """Trained backend: sklearn is optional, so skip when it is not installed."""

    @unittest.skipIf(not SKLEARN_AVAILABLE, "scikit-learn not installed")
    def test_train_roundtrip_and_predict_category(self):
        from router.tfidf import TfidfClassifier, train

        rows = [
            {"text": "scrivi una funzione python che legge un file", "category": "coding"},
            {"text": "ho un errore nel codice python, questo traceback", "category": "coding"},
            {"text": "correggi la classe e refactor del codice", "category": "coding"},
            {"text": "questa funzione python ha un bug", "category": "coding"},
            {"text": "il servizio nginx non parte, usa systemctl", "category": "sysadmin"},
            {"text": "comando linux nel terminale per i permessi", "category": "sysadmin"},
            {"text": "sposta la cartella nella home con mv", "category": "sysadmin"},
            {"text": "il disco e le partizioni su debian", "category": "sysadmin"},
            {"text": "trova il flag in questo binario elf", "category": "ctf"},
            {"text": "questa challenge ha un buffer overflow, exploit", "category": "ctf"},
            {"text": "estrai il flag dall'immagine con la steganografia", "category": "ctf"},
            {"text": "reverse engineering del malware per la flag", "category": "ctf"},
            {"text": "mi consigli un libro da leggere?", "category": None},
            {"text": "che tempo fa domani a milano?", "category": None},
            {"text": "scrivi una mail al mio capo per le ferie", "category": None},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "tiny.jsonl"
            dataset.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            model_path = Path(tmp) / "intent.joblib"

            stats = train([dataset], model_path)
            self.assertEqual(stats["examples"], len(rows))
            self.assertEqual(stats["classes"]["none"], 3)
            self.assertTrue(Path(stats["model"]).is_file())

            clf = TfidfClassifier(Registry.load(), model_path)
            self.assertEqual(clf.name, "tfidf")

            scores = clf.scores("scrivi una funzione python, mi dà un errore nel codice")
            best = max(scores, key=scores.get)
            self.assertEqual(best, "cat:coding")
            for key, value in scores.items():
                self.assertTrue(key.startswith("cat:"), key)
                self.assertNotEqual(key, "cat:none")
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)
            self.assertLessEqual(sum(scores.values()), 1.0001)

    @unittest.skipIf(not SKLEARN_AVAILABLE, "scikit-learn not installed")
    def test_missing_model_fails_loudly(self):
        from router.tfidf import TfidfClassifier

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                TfidfClassifier(Registry.load(), Path(tmp) / "missing.joblib")


class TokenEstimateTest(unittest.TestCase):
    def test_uses_3_5_chars_per_token(self):
        self.assertEqual(estimate_tokens("x" * 70), 20)

    def test_uses_conservative_ratio_for_shorter_text(self):
        self.assertEqual(estimate_tokens("x" * 35), 10)

    def test_floor_is_one_token_for_empty_text(self):
        self.assertEqual(estimate_tokens(""), 1)


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

    def test_http_prompt_routes_to_http(self):
        d = self.router.route(["come chiamo un endpoint API da python con curl?"])
        self.assertEqual(d.category, "coding")
        self.assertIn("python", [p.addon for p in d.addons])
        self.assertIn("http", [p.addon for p in d.addons])

    def test_unrelated_prompt_does_not_pick_http(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("http", [p.addon for p in d.addons])

    def test_summarize_prompt_routes_to_summarize(self):
        prompts = [
            "riassumi questo articolo in tre punti",
            "dammi una sintesi del documento",
            "fammi un tldr",
            "elenca i punti chiave del testo",
            "summarize this article for me",
        ]
        for text in prompts:
            with self.subTest(text=text):
                d = self.router.route([text])
                self.assertIn("summarize", [p.addon for p in d.addons])

    def test_unrelated_prompt_does_not_pick_summarize(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("summarize", [p.addon for p in d.addons])

    def test_translate_prompt_routes_to_translate(self):
        prompts = [
            "traduci questo paragrafo in inglese",
            "translate this into English",
            "traduci in italiano questa email",
            "can you translate this into english?",
        ]
        for text in prompts:
            with self.subTest(text=text):
                d = self.router.route([text])
                self.assertIn("translate", [p.addon for p in d.addons])

    def test_unrelated_prompt_does_not_pick_translate(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("translate", [p.addon for p in d.addons])

    def test_humanize_prompt_routes_to_humanize(self):
        prompts = [
            "umanizza questo testo",
            "umanizzare questo paragrafo",
            "rendi più umano questo testo",
            "scrivi in modo più naturale",
            "rendilo meno robotico",
            "humanize this text",
            "can you humanise this paragraph?",
        ]
        for text in prompts:
            with self.subTest(text=text):
                d = self.router.route([text])
                self.assertIn("humanize", [p.addon for p in d.addons])

    def test_unrelated_prompt_does_not_pick_humanize(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("humanize", [p.addon for p in d.addons])

    def test_bash_scripting_prompt_routes_to_bash_scripting(self):
        prompts = [
            "scrivi uno script bash per fare il backup dei file",
            "come uso shellcheck sul mio script?",
            "aggiungi set -euo pipefail in cima allo script",
            "mi serve una shebang corretta per lo script",
        ]
        for text in prompts:
            with self.subTest(text=text):
                d = self.router.route([text])
                self.assertIn("bash-scripting", [p.addon for p in d.addons])

    def test_unrelated_prompt_does_not_pick_bash_scripting(self):
        prompts = [
            "come faccio l'hash in python",
            "come riavvio nginx con systemctl",
            "come eseguo questo comando bash sulla shell?",
        ]
        for text in prompts:
            with self.subTest(text=text):
                d = self.router.route([text])
                self.assertNotIn("bash-scripting", [p.addon for p in d.addons])


class JavaScriptAddonTest(unittest.TestCase):
    def setUp(self):
        self.router = make_router()

    def test_javascript_keyword_routes_to_coding(self):
        d = self.router.route(["scrivi una funzione in javascript"])
        self.assertEqual(d.category, "coding")
        self.assertIn("javascript", [p.addon for p in d.addons])

    def test_git_fetch_does_not_pull_javascript(self):
        d = self.router.route(["git fetch origin main"])
        self.assertNotIn("javascript", [p.addon for p in d.addons])
        self.assertIn("git", [p.addon for p in d.addons])

    def test_async_python_does_not_pull_javascript(self):
        d = self.router.route(["scrivi una funzione async in python con asyncio"])
        self.assertNotIn("javascript", [p.addon for p in d.addons])
        self.assertIn("python", [p.addon for p in d.addons])

    def test_typescript_keyword_routes_to_javascript(self):
        d = self.router.route(["devo tipizzare una interfaccia in typescript"])
        self.assertIn("javascript", [p.addon for p in d.addons])

    def test_magika_labels_route_to_javascript(self):
        for label in ("javascript", "typescript"):
            with self.subTest(label=label):
                router = make_magika_router([Detection(label, 0.99, f"file:app.{label}")])
                d = router.route(["correggi questo file"])
                self.assertEqual(d.category, "coding")
                self.assertIn("javascript", [p.addon for p in d.addons])

    def test_python_prompt_does_not_pull_javascript(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("javascript", [p.addon for p in d.addons])


class VueAddonTest(unittest.TestCase):
    def setUp(self):
        self.router = make_router()

    def test_vue_keyword_routes_to_coding(self):
        d = self.router.route(["scrivi un componente vue con la composition api"])
        self.assertEqual(d.category, "coding")
        self.assertIn("vue", [p.addon for p in d.addons])

    def test_vue_ecosystem_keywords_route_to_vue(self):
        d = self.router.route(["come uso pinia in un progetto vue3 con vite.config"])
        self.assertIn("vue", [p.addon for p in d.addons])

    def test_italian_word_vite_does_not_pull_vue(self):
        d = self.router.route(["devo avvitare una vite nel muro"])
        self.assertNotIn("vue", [p.addon for p in d.addons])

    def test_dot_vue_extension_routes_to_vue(self):
        d = self.router.route(["correggi il componente App.vue"])
        self.assertIn("vue", [p.addon for p in d.addons])

    def test_python_prompt_does_not_pull_vue(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("vue", [p.addon for p in d.addons])


class LaravelAddonTest(unittest.TestCase):
    def setUp(self):
        self.router = make_router()

    def test_laravel_keyword_routes_to_coding(self):
        d = self.router.route(["scrivi una migration laravel per la tabella utenti"])
        self.assertEqual(d.category, "coding")
        self.assertIn("laravel", [p.addon for p in d.addons])

    def test_php_eloquent_artisan_prompt_routes_to_laravel(self):
        d = self.router.route(["un controller php con eloquent e una route"])
        self.assertIn("laravel", [p.addon for p in d.addons])

    def test_magika_php_routes_to_laravel(self):
        router = make_magika_router([Detection("php", 0.99, "file:app.php")])
        d = router.route(["correggi questo file"])
        self.assertEqual(d.category, "coding")
        self.assertIn("laravel", [p.addon for p in d.addons])

    def test_python_prompt_does_not_pull_laravel(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("laravel", [p.addon for p in d.addons])


class CAddonTest(unittest.TestCase):
    def setUp(self):
        self.router = make_router()

    def test_cpp_keyword_routes_to_coding(self):
        d = self.router.route(["scrivi una funzione in c++ che inverte una lista"])
        self.assertEqual(d.category, "coding")
        self.assertIn("c", [p.addon for p in d.addons])

    def test_c_keywords_route_to_c(self):
        d = self.router.route(["compila con gcc e correggi il segfault"])
        self.assertIn("c", [p.addon for p in d.addons])

    def test_standalone_c_language_name_routes_to_c(self):
        for text in ["scrivi un programma C che legge un file", "scritto in C", "in C"]:
            with self.subTest(text=text):
                d = self.router.route([text])
                self.assertIn("c", [p.addon for p in d.addons])

    def test_dot_c_extension_routes_to_c(self):
        d = self.router.route(["correggi il file main.c"])
        self.assertIn("c", [p.addon for p in d.addons])

    def test_magika_c_and_cpp_route_to_c(self):
        for label in ("c", "cpp"):
            with self.subTest(label=label):
                router = make_magika_router([Detection(label, 0.99, f"file:app.{label}")])
                d = router.route(["correggi questo file"])
                self.assertEqual(d.category, "coding")
                self.assertIn("c", [p.addon for p in d.addons])

    def test_python_prompt_does_not_pull_c(self):
        d = self.router.route(["come faccio l'hash in python"])
        self.assertNotIn("c", [p.addon for p in d.addons])

    def test_italian_ce_does_not_pull_c(self):
        d = self.router.route(["c'è un problema con il codice"])
        self.assertNotIn("c", [p.addon for p in d.addons])


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
