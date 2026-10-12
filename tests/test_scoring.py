"""Scorer invariants: span assignment, document-level credit, protected-term
boundaries and anchoring, quote validation, ground-truth verification, and
reproduction of the committed results from the committed raw findings."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _support import REPO, load_score

sc = load_score()
WHITELIST = json.loads((REPO / "corpora" / "finance-audit" / "whitelist.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((REPO / "seeded" / "finance-audit" / "manifest.json").read_text(encoding="utf-8"))
CLEAN = REPO / "corpora" / "finance-audit" / "clean"
_, RULE_TO_CANON, _ = sc.load_crosswalk()


def seeded_run(tool, findings_by_draft):
    files = {f"{d}.md": {"words": 0, "findings": fs} for d, fs in findings_by_draft.items()}
    return {"tool": tool, "files": files}


class SpanAssignmentTest(unittest.TestCase):
    def test_maximum_matching_beats_greedy_order(self):
        # Greedy would give left 0 the right node 0 and strand left 1.
        self.assertEqual(len(sc.max_bipartite_matching([[0, 1], [0]], 2)), 2)

    def test_one_long_quote_is_credited_to_at_most_one_plant(self):
        draft = MANIFEST["drafts"][0]["draft_id"]
        text = (REPO / "seeded" / "finance-audit" / f"{draft}.md").read_text(encoding="utf-8")
        run = seeded_run("stop-slop", {draft: [{"rule": "Anything", "text": text, "index": None}]})
        self.assertLessEqual(sc.match_seeded(run, MANIFEST, RULE_TO_CANON)["matched"], 1)

    def test_document_level_rule_covers_every_plant_of_its_pattern(self):
        # One document-level flag must be reusable across every plant of its
        # pattern. The draft chosen has two formatting plants, so a flag
        # consumed after its first plant would fail this.
        draft = next(d for d in MANIFEST["drafts"]
                     if sum(p["pattern_id"] == "str-formatting-slop" for p in d["plants"]) >= 2)
        n = sum(p["pattern_id"] == "str-formatting-slop" for p in draft["plants"])
        self.assertGreaterEqual(n, 2)
        run = seeded_run("avoid-ai-writing-detector",
                         {draft["draft_id"]: [{"rule": "formatting", "text": "formatting", "index": None}]})
        r = sc.match_seeded(run, MANIFEST, RULE_TO_CANON)
        self.assertEqual(r["per_pattern"]["str-formatting-slop"]["matched"], n)

    def test_unlocatable_seeded_quote_is_reported_and_never_credited(self):
        draft = MANIFEST["drafts"][0]["draft_id"]
        run = seeded_run("stop-slop", {draft: [{"rule": "Invented", "text": "ideate, iterate, and deliver", "index": None}]})
        r = sc.match_seeded(run, MANIFEST, RULE_TO_CANON)
        self.assertEqual((r["matched"], r["unlocated"], r["findings_reported"]), (0, 1, 1))


class ProtectedTermTest(unittest.TestCase):
    def test_word_boundaries(self):
        lower = "an unqualified opinion, then a qualified opinion."
        spans = sc.boundary_spans(lower, "qualified opinion")
        self.assertEqual(len(spans), 1)
        self.assertEqual(lower[spans[0][0]:spans[0][1]], "qualified opinion")

    def test_anchored_containment_and_unlocated_quotes(self):
        fname = "F_2021_opinion.txt"
        text = (CLEAN / fname).read_text(encoding="utf-8")
        term = "present fairly, in all material respects"
        i = text.find(term)
        self.assertGreaterEqual(i, 0)
        wide = text[max(0, i - 300):i + len(term) + 300]
        run = {"tool": "test", "files": {fname: {"words": len(text.split()), "findings": [
            {"rule": "Adverbs", "text": term, "index": None},
            {"rule": "Passive voice", "text": wide, "index": None},
            {"rule": "Invented", "text": "ideate, iterate, and deliver", "index": None},
        ]}}}
        r = sc.score_human(run, WHITELIST)
        self.assertEqual(r["findings_reported"], 3)
        self.assertEqual(r["unlocated"], 1)
        self.assertEqual(r["flags"], 2)
        self.assertEqual(r["toa_violations"], 1)
        self.assertEqual(r["toa_containment"], 2)
        self.assertEqual(r["flags_per_1k"], round(2 / len(text.split()) * 1000, 2))

    def test_document_level_flags_count_without_a_quote(self):
        fname = "F_2021_mdna.txt"
        text = (CLEAN / fname).read_text(encoding="utf-8")
        run = {"tool": "test", "files": {fname: {"words": len(text.split()), "findings": [
            {"rule": "em-dash", "text": "40 em dashes in 20281 words", "index": None}]}}}
        r = sc.score_human(run, WHITELIST)
        self.assertEqual((r["flags"], r["unlocated"]), (1, 0))


class GroundTruthAndReproductionTest(unittest.TestCase):
    def test_manifest_verifies(self):
        proc = subprocess.run([sys.executable, str(REPO / "scripts" / "verify_manifest.py"), "finance-audit"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("OK: 122 plants across 10 drafts", proc.stdout)

    def test_committed_results_reproduce_from_committed_raw_findings(self):
        published = sorted((REPO / "results").glob("finance-audit_*.json"))[-1]
        tmp = Path(tempfile.mkdtemp())
        try:
            for d in ("scripts", "seeded", "corpora", "crosswalk"):
                shutil.copytree(REPO / d, tmp / d)
            (tmp / "results").mkdir()
            for p in (REPO / "results").glob("raw_*.json"):
                shutil.copy(p, tmp / "results" / p.name)
            subprocess.run([sys.executable, str(tmp / "scripts" / "score.py"), "finance-audit"],
                           check=True, capture_output=True)
            fresh = json.loads(next((tmp / "results").glob("finance-audit_*.json")).read_text(encoding="utf-8"))
            expected = json.loads(published.read_text(encoding="utf-8"))
            for key in ("date",):
                fresh.pop(key, None)
                expected.pop(key, None)
            self.assertEqual(fresh, expected)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
