"""Message Batches harness (run_prompt_batch.py) against a mocked Batches API:
selection guards, double-spend guards, resume, collection, cost accounting,
discard, and assembly refusals for missing responses and mixed protocols."""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.request
from pathlib import Path

from _support import FAKE_KEY, REPO, FakeResponse, rb, refuse_network, rt

PROBE = "*-human-F_2021_mdna-r1"


class FakeBatchesAPI:
    def __init__(self):
        self.batches, self.created, self.polls = {}, [], {}
        self.count_calls = 0
        self.errored, self.max_tokens, self.malformed, self.orphans = set(), set(), set(), []

    def message(self, cid):
        text = '[{}]' if cid in self.malformed else f'[{{"rule": "r", "quote": "{cid}"}}]'
        return {"model": "claude-sonnet-5",
                "stop_reason": "max_tokens" if cid in self.max_tokens else "end_turn",
                "content": [{"type": "text", "text": text}],
                "usage": {"input_tokens": 1000, "cache_creation_input_tokens": 20000,
                          "cache_read_input_tokens": 0,
                          "cache_creation": {"ephemeral_1h_input_tokens": 20000,
                                             "ephemeral_5m_input_tokens": 0},
                          "output_tokens": 8000, "output_tokens_details": {"thinking_tokens": 7500}}}

    def __call__(self, req, timeout=None):
        url, method = req.full_url, req.get_method()
        assert dict(req.header_items()).get("X-api-key") == FAKE_KEY
        if url.endswith("/messages/count_tokens"):
            self.count_calls += 1
            assert set(json.loads(req.data)) == {"model", "system", "messages"}
            return FakeResponse({"input_tokens": 12345})
        if url.endswith("/messages/batches?limit=100"):
            return FakeResponse({"data": [{"id": i} for i in list(self.batches) + self.orphans]})
        if url.endswith("/messages/batches") and method == "POST":
            body = json.loads(req.data)
            bid = f"msgbatch_{len(self.batches) + 1}"
            self.batches[bid] = [r["custom_id"] for r in body["requests"]]
            self.created.append(body)
            self.polls[bid] = 0
            return FakeResponse({"id": bid, "processing_status": "in_progress",
                                 "created_at": "2026-10-12T01:00:00Z"})
        if url.endswith("/results"):
            bid = url.split("/")[-2]
            lines = []
            for cid in self.batches[bid]:
                if cid in self.errored:
                    lines.append({"custom_id": cid, "result": {"type": "errored", "error": {
                        "type": "error", "error": {"type": "overloaded_error", "message": "x"}}}})
                else:
                    lines.append({"custom_id": cid, "result": {"type": "succeeded", "message": self.message(cid)}})
            return FakeResponse("\n".join(json.dumps(x) for x in lines).encode(), raw=True)
        if "/messages/batches/" in url:
            bid = url.split("/")[-1]
            self.polls[bid] += 1
            ended = self.polls[bid] >= 2
            return FakeResponse({
                "id": bid, "processing_status": "ended" if ended else "in_progress",
                "request_counts": {"processing": 0 if ended else len(self.batches[bid])},
                "ended_at": "2026-10-12T01:30:00Z" if ended else None,
                "results_url": f"https://api.anthropic.com/v1/messages/batches/{bid}/results" if ended else None})
        raise AssertionError(f"unexpected {method} {url}")


class BatchHarnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "results").mkdir()
        for short in rb.SHORT.values():
            (self.tmp / "results" / f"raw_{short}_human_finance.json").write_text("{}", encoding="utf-8")
        (self.tmp / "results" / "raw_aaw_human_finance.json").write_text("{}", encoding="utf-8")
        names = ("ROOT", "STATE_DIR", "RESP_DIR", "ERR_DIR", "DISCARD_DIR", "STATE")
        self.saved = {n: getattr(rb, n) for n in names}
        self.saved_env_file, self.saved_urlopen, self.saved_sleep = rt.ENV_FILE, urllib.request.urlopen, rb.time.sleep
        rb.ROOT = self.tmp
        rb.STATE_DIR = self.tmp / "results" / "prompt_runs" / "batch"
        rb.RESP_DIR, rb.ERR_DIR = rb.STATE_DIR / "responses", rb.STATE_DIR / "errors"
        rb.DISCARD_DIR, rb.STATE = rb.STATE_DIR / "discarded", rb.STATE_DIR / "state.json"
        rt.ENV_FILE = self.tmp / ".env"
        rb.time.sleep = lambda s: None
        os.environ["REGISTERBENCH_API_KEY"] = FAKE_KEY
        self.api = FakeBatchesAPI()
        urllib.request.urlopen = self.api

    def tearDown(self):
        for n, v in self.saved.items():
            setattr(rb, n, v)
        rt.ENV_FILE, urllib.request.urlopen, rb.time.sleep = self.saved_env_file, self.saved_urlopen, self.saved_sleep
        os.environ.pop("REGISTERBENCH_API_KEY", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def run_cmd(fn, args):
        out = io.StringIO()
        code = 0
        try:
            with contextlib.redirect_stdout(out):
                fn(args)
        except SystemExit as e:
            code = e.code
        return code, out.getvalue()

    def submit(self, *args):
        return self.run_cmd(rb.cmd_submit, ["--approved", *args])

    def wait(self):
        return self.run_cmd(rb.cmd_wait, ["--interval", "1"])

    # --- plan and selection guards -----------------------------------------
    def test_plan_covers_the_canonical_run(self):
        plan = rb.planned()
        self.assertEqual(len(plan), 336)
        self.assertTrue(all(len(c) <= 64 for c in plan))
        self.assertFalse(any("README" in c for c in plan))

    def test_selection_guards(self):
        code, _ = self.run_cmd(rb.cmd_submit, ["--only", PROBE, "--expect", "4"])
        self.assertIn("Refusing", str(code))
        code, _ = self.submit("--only")
        self.assertIn("needs one or more globs", str(code))
        code, _ = self.submit("--only", "--expect", "4")
        self.assertIn("needs one or more globs", str(code))
        code, _ = self.submit("--only", PROBE)
        self.assertIn("--expect 4", str(code))
        code, _ = self.submit("--expect", "4", "--only", PROBE, "*-seeded-fin-10-r1")
        self.assertIn("--expect 8", str(code))
        self.assertEqual(self.api.created, [])

    def test_unknown_workspace_batch_blocks_submit(self):
        self.api.orphans = ["msgbatch_orphan"]
        code, _ = self.submit("--only", PROBE, "--expect", "4")
        self.assertIn("does not know", str(code))
        self.assertEqual(self.api.created, [])

    # --- request shape ------------------------------------------------------
    def test_request_shape(self):
        code, out = self.submit("--only", PROBE, "--expect", "4")
        self.assertIn("4 requests", out)
        self.assertEqual(self.api.count_calls, 4)
        params = self.api.created[0]["requests"][0]["params"]
        self.assertEqual(params["model"], "claude-sonnet-5")
        self.assertEqual(params["max_tokens"], rt.MAX_TOKENS)
        self.assertNotIn("thinking", params)
        self.assertNotIn("temperature", params)
        self.assertEqual(params["system"][0]["cache_control"], {"type": "ephemeral", "ttl": "1h"})
        self.assertIn("BENCHMARK INSTRUCTION", params["system"][0]["text"])
        doc = (REPO / "corpora" / "finance-audit" / "clean" / "F_2021_mdna.txt").read_text(encoding="utf-8")
        self.assertEqual(params["messages"][0]["content"], doc)
        state = json.loads(rb.STATE.read_text(encoding="utf-8"))["batches"]["msgbatch_1"]
        self.assertEqual(set(state["tool_shas"]), set(rb.SHORT))

    # --- resume and double-spend guards ------------------------------------
    def test_in_flight_and_uncollected_batches_are_not_resubmitted(self):
        self.submit("--only", PROBE, "--expect", "4")
        code, _ = self.submit("--only", PROBE, "--expect", "4")
        self.assertIn("nothing pending", str(code))
        st = json.loads(rb.STATE.read_text(encoding="utf-8"))
        st["batches"]["msgbatch_1"]["status"] = "ended"
        rb.save_state(st)
        code, _ = self.submit("--only", PROBE, "--expect", "4")
        self.assertIn("nothing pending", str(code))
        self.assertEqual(len(self.api.created), 1)

    def test_errored_requests_become_pending_and_only_they_are_resent(self):
        self.api.errored = {"stopslop-human-F_2021_mdna-r1"}
        self.submit("--only", PROBE, "--expect", "4")
        code, out = self.wait()
        self.assertIn("collected {'succeeded': 3, 'errored': 1}", out)
        self.assertEqual(len(list(rb.RESP_DIR.glob("*.json"))), 3)
        # 1000 x $1 + 20000 x $2 (1h write) + 8000 x $5 = $0.081 per response
        self.assertIn("billed so far (batch prices): $0.24", out)
        self.api.errored = set()
        code, out = self.submit("--only", PROBE, "--expect", "1")
        self.assertIn("1 requests", out)
        self.assertEqual(self.api.created[-1]["requests"][0]["custom_id"], "stopslop-human-F_2021_mdna-r1")

    # --- assembly -----------------------------------------------------------
    def complete_run(self):
        self.submit("--expect", "336")
        self.wait()

    def test_assemble_refuses_missing_responses(self):
        self.submit("--only", PROBE, "--expect", "4")
        self.wait()
        code, _ = self.run_cmd(rb.cmd_assemble, [])
        self.assertIn("missing", str(code))

    def test_assemble_refuses_unusable_billed_responses_and_discard_keeps_cost(self):
        self.api.max_tokens = {"noaislop-seeded-fin-03-r2"}
        self.api.malformed = {"stopslop-seeded-fin-04-r1"}
        self.complete_run()
        code, _ = self.run_cmd(rb.cmd_assemble, [])
        self.assertIn("noaislop-seeded-fin-03-r2: hit max_tokens", str(code))
        self.assertIn("stopslop-seeded-fin-04-r1: did not parse", str(code))
        self.assertFalse(list((self.tmp / "results").glob("raw_*_run*.json")))
        code, out = self.run_cmd(rb.cmd_discard, ["noaislop-seeded-fin-03-r2", "stopslop-seeded-fin-04-r1"])
        self.assertIn("still counted as billed", out)
        code, out = self.run_cmd(rb.cmd_cost, [])
        self.assertIn("discarded but billed: 2 responses", out)
        self.api.max_tokens, self.api.malformed = set(), set()
        self.submit("--expect", "2")
        self.wait()
        code, out = self.run_cmd(rb.cmd_assemble, [])
        self.assertIn(code, (0, None))

    def test_assemble_refuses_mixed_protocols(self):
        self.complete_run()
        for field, value in (("system_sha256", "0" * 64), ("tool_shas", "f" * 40)):
            with self.subTest(field=field):
                st = json.loads(rb.STATE.read_text(encoding="utf-8"))
                first = list(st["batches"])[0]
                real = st["batches"][first][field]["no-ai-slop"]
                st["batches"]["msgbatch_extra"] = json.loads(json.dumps(st["batches"][first]))
                st["batches"]["msgbatch_extra"][field]["no-ai-slop"] = value
                cid = "noaislop-seeded-fin-01-r1"
                saved = json.loads((rb.RESP_DIR / f"{cid}.json").read_text(encoding="utf-8"))
                saved["batch_id"] = "msgbatch_extra"
                (rb.RESP_DIR / f"{cid}.json").write_text(json.dumps(saved), encoding="utf-8")
                rb.save_state(st)
                code, _ = self.run_cmd(rb.cmd_assemble, [])
                self.assertIn(f"more than one {field}", str(code))
                saved["batch_id"] = first
                (rb.RESP_DIR / f"{cid}.json").write_text(json.dumps(saved), encoding="utf-8")
                del st["batches"]["msgbatch_extra"]
                st["batches"][first][field]["no-ai-slop"] = real
                rb.save_state(st)

    def test_assemble_writes_score_ready_files(self):
        self.complete_run()
        code, out = self.run_cmd(rb.cmd_assemble, [])
        self.assertIn(code, (0, None))
        files = sorted(p.name for p in (self.tmp / "results").glob("raw_*_run*.json"))
        self.assertEqual(len(files), 24)
        for short in rb.SHORT.values():
            self.assertFalse((self.tmp / "results" / f"raw_{short}_human_finance.json").exists())
        self.assertTrue((self.tmp / "results" / "raw_aaw_human_finance.json").exists())
        human = json.loads((self.tmp / "results" / "raw_stopslop_human_run2.json").read_text(encoding="utf-8"))
        self.assertEqual((len(human["files"]), human["run_n"], human["tool"]), (18, 2, "stop-slop"))
        self.assertEqual(human["options"]["served_models"], ["claude-sonnet-5"])
        self.assertEqual(len(human["options"]["system_sha256"]), 64)
        self.assertEqual(human["options"]["usage"]["thinking"], 18 * 7500)
        seeded = json.loads((self.tmp / "results" / "raw_aawskill_seeded_run3.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(seeded["files"]), [f"fin-{i:02d}.md" for i in range(1, 11)])
        self.assertEqual(seeded["files"]["fin-01.md"]["findings"][0],
                         {"rule": "r", "text": "aawskill-seeded-fin-01-r3", "index": None, "severity": None})
        self.assertEqual(seeded["run_date"], "2026-10-12")


if __name__ == "__main__":
    unittest.main()
