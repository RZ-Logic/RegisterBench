"""Synchronous prompt harness (run_prompt_tool.py): key handling, cost gate,
smoke mode, resume, input guards and HTTP errors, against a mocked endpoint."""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from _support import FAKE_KEY, REPO, FakeResponse, refuse_network, rt

SEEDED = REPO / "seeded" / "finance-audit"
CLEAN = REPO / "corpora" / "finance-audit" / "clean"


def ok_message(text='[{"rule": "r1", "quote": "q1"}]', stop="end_turn"):
    return {"model": "claude-sonnet-5", "stop_reason": stop,
            "usage": {"input_tokens": 1234, "output_tokens": 56},
            "content": [{"type": "text", "text": text}]}


class PromptHarnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "results").mkdir()
        self.saved = (rt.ROOT, rt.ENV_FILE, rt.N_RUNS, urllib.request.urlopen, rt.time.sleep)
        rt.ROOT, rt.ENV_FILE = self.tmp, self.tmp / ".env"
        rt.time.sleep = lambda s: None
        urllib.request.urlopen = refuse_network
        os.environ.pop("REGISTERBENCH_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.calls = []

    def tearDown(self):
        rt.ROOT, rt.ENV_FILE, rt.N_RUNS, urllib.request.urlopen, rt.time.sleep = self.saved
        os.environ.pop("REGISTERBENCH_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def serve(self, message=None):
        def fake(req, timeout=None):
            self.calls.append(req)
            return FakeResponse(message or ok_message())
        urllib.request.urlopen = fake

    def run_main(self, argv):
        out = io.StringIO()
        saved = sys.argv
        sys.argv = ["run_prompt_tool.py"] + argv
        code = 0
        try:
            with contextlib.redirect_stdout(out):
                rt.main()
        except SystemExit as e:
            code = e.code
        finally:
            sys.argv = saved
        return code, out.getvalue()

    # --- key handling -----------------------------------------------------
    def test_env_file_encodings_and_syntax(self):
        cases = [
            f"# comment\nREGISTERBENCH_API_KEY={FAKE_KEY}\n".encode("utf-8"),
            f"REGISTERBENCH_API_KEY={FAKE_KEY}\r\n".encode("utf-8-sig"),
            f"REGISTERBENCH_API_KEY={FAKE_KEY}\r\n".encode("utf-16"),
            f'export REGISTERBENCH_API_KEY = "{FAKE_KEY}"\n'.encode("utf-8"),
            f"REGISTERBENCH_API_KEY={FAKE_KEY}  # workspace key\n".encode("utf-8"),
        ]
        for raw in cases:
            with self.subTest(raw=raw[:24]):
                rt.ENV_FILE.write_bytes(raw)
                self.assertEqual(rt.read_env_file(rt.ENV_FILE).get("REGISTERBENCH_API_KEY"), FAKE_KEY)
        self.assertEqual(rt.read_env_file(self.tmp / "missing"), {})

    def test_environment_wins_over_env_file(self):
        rt.ENV_FILE.write_text(f"REGISTERBENCH_API_KEY={FAKE_KEY}\n", encoding="utf-8")
        self.assertEqual(rt.load_api_key(), FAKE_KEY)
        os.environ["REGISTERBENCH_API_KEY"] = "sk-ant-ENV"
        self.assertEqual(rt.load_api_key(), "sk-ant-ENV")

    def test_anthropic_api_key_is_never_read(self):
        rt.ENV_FILE.write_text(f"ANTHROPIC_API_KEY={FAKE_KEY}\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            rt.load_api_key()
        self.assertIn("deliberately not read", str(cm.exception.code))
        self.assertNotIn(FAKE_KEY, str(cm.exception.code))
        rt.ENV_FILE.unlink()
        os.environ["ANTHROPIC_API_KEY"] = FAKE_KEY
        with self.assertRaises(SystemExit) as cm:
            rt.load_api_key()
        self.assertIn("rename it", str(cm.exception.code))

    def test_blank_key_is_refused(self):
        rt.ENV_FILE.write_text("REGISTERBENCH_API_KEY=\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            rt.load_api_key()

    # --- gates ------------------------------------------------------------
    def test_cost_gate_refuses_before_any_call(self):
        code, _ = self.run_main(["avoid-ai-writing-skill", "x", str(SEEDED)])
        self.assertIn("Refusing", str(code))
        code, _ = self.run_main(["--approved", "--smoke", "avoid-ai-writing-skill", str(SEEDED / "fin-10.md")])
        self.assertIn("not set", str(code))
        self.assertEqual(self.calls, [])

    def test_directory_inputs_skip_corpus_documentation(self):
        drafts = rt.collect(SEEDED)
        self.assertEqual(len(drafts), 10)
        self.assertTrue(all(d.name.startswith("fin-") for d in drafts))
        self.assertEqual(len(rt.collect(CLEAN)), 18)

    def test_long_inputs_are_refused_on_the_sync_path(self):
        os.environ["REGISTERBENCH_API_KEY"] = FAKE_KEY
        code, _ = self.run_main(["--approved", "stop-slop", "raw_x", str(CLEAN)])
        self.assertIn("use run_prompt_batch.py", str(code))

    # --- smoke --------------------------------------------------------------
    def test_smoke_makes_one_call_and_reports_the_served_model(self):
        os.environ["REGISTERBENCH_API_KEY"] = FAKE_KEY
        self.serve()
        code, out = self.run_main(["--approved", "--smoke", "avoid-ai-writing-skill", str(SEEDED / "fin-10.md")])
        self.assertIn(code, (0, None))
        self.assertEqual(len(self.calls), 1)
        self.assertIn("served model:    claude-sonnet-5", out)
        self.assertIn("1234 in, 56 out", out)
        self.assertNotIn(FAKE_KEY, out)
        body = json.loads(self.calls[0].data)
        headers = {k.lower(): v for k, v in self.calls[0].header_items()}
        self.assertEqual(headers["x-api-key"], FAKE_KEY)
        self.assertEqual(body["model"], "claude-sonnet-5")
        self.assertIn("BENCHMARK INSTRUCTION", body["system"])
        self.assertFalse(list((self.tmp / "results").glob("*.json")))

    def test_smoke_flags_truncated_or_malformed_output(self):
        os.environ["REGISTERBENCH_API_KEY"] = FAKE_KEY
        self.serve(ok_message(text='[{"rule": "r"', stop="max_tokens"))
        code, out = self.run_main(["--approved", "--smoke", "stop-slop", str(SEEDED / "fin-10.md")])
        self.assertEqual(code, 1)
        self.assertIn("UNPARSEABLE", out)

    # --- full mode ----------------------------------------------------------
    def test_full_run_writes_result_and_resumes_without_paying_twice(self):
        os.environ["REGISTERBENCH_API_KEY"] = FAKE_KEY
        rt.N_RUNS = 1
        self.serve()
        code, _ = self.run_main(["--approved", "stop-slop", "raw_test_seeded", str(SEEDED)])
        self.assertIn(code, (0, None))
        self.assertEqual(len(self.calls), 10)
        res = json.loads((self.tmp / "results" / "raw_test_seeded_run1.json").read_text(encoding="utf-8"))
        self.assertEqual(res["options"]["served_models"], ["claude-sonnet-5"])
        self.assertNotIn("README.md", res["files"])
        self.assertEqual(res["files"]["fin-01.md"]["findings"][0]["text"], "q1")
        self.calls.clear()
        code, out = self.run_main(["--approved", "stop-slop", "raw_test_seeded", str(SEEDED)])
        self.assertEqual(self.calls, [])
        self.assertIn("reusing saved response", out)

    def test_malformed_response_is_fatal_not_an_empty_result(self):
        os.environ["REGISTERBENCH_API_KEY"] = FAKE_KEY
        rt.N_RUNS = 1
        self.serve(ok_message(text='[{}]'))
        code, _ = self.run_main(["--approved", "stop-slop", "raw_test_seeded", str(SEEDED / "fin-01.md")])
        self.assertIn("did not parse", str(code))
        self.assertFalse((self.tmp / "results" / "raw_test_seeded_run1.json").exists())

    # --- HTTP errors --------------------------------------------------------
    def test_rate_limit_is_retried(self):
        os.environ["REGISTERBENCH_API_KEY"] = FAKE_KEY
        seq = []

        def flaky(req, timeout=None):
            seq.append(1)
            if len(seq) == 1:
                raise urllib.error.HTTPError(req.full_url, 429, "rate", {}, io.BytesIO(b"{}"))
            return FakeResponse(ok_message())
        urllib.request.urlopen = flaky
        code, _ = self.run_main(["--approved", "--smoke", "no-ai-slop", str(SEEDED / "fin-10.md")])
        self.assertEqual(len(seq), 2)
        self.assertIn(code, (0, None))

    def test_other_http_errors_exit_with_the_api_body_and_no_key(self):
        os.environ["REGISTERBENCH_API_KEY"] = FAKE_KEY

        def not_found(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 404, "nf", {},
                                         io.BytesIO(b'{"error":{"type":"not_found_error"}}'))
        urllib.request.urlopen = not_found
        code, _ = self.run_main(["--approved", "--smoke", "no-ai-slop", str(SEEDED / "fin-10.md")])
        self.assertIn("HTTP 404", str(code))
        self.assertIn("not_found_error", str(code))
        self.assertNotIn(FAKE_KEY, str(code))

    def test_network_errors_are_not_retried(self):
        os.environ["REGISTERBENCH_API_KEY"] = FAKE_KEY
        seq = []

        def drop(req, timeout=None):
            seq.append(1)
            raise TimeoutError("timed out")
        urllib.request.urlopen = drop
        code, _ = self.run_main(["--approved", "--smoke", "no-ai-slop", str(SEEDED / "fin-10.md")])
        self.assertEqual(len(seq), 1)
        self.assertIn("may have been billed", str(code))


if __name__ == "__main__":
    unittest.main()
