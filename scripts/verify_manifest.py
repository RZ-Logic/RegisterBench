"""Verify seeded-draft manifests against the drafts and the crosswalk.

Checks, per draft: every plant span (and distractor span) occurs in the draft
at least `occurrence` times; word count is 300-600; plant count is 8-15; every
pattern_id exists in crosswalk/patterns.json. Exits nonzero on any failure.

Usage: py scripts/verify_manifest.py [register]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTER = sys.argv[1] if len(sys.argv) > 1 else "finance-audit"


def occurrences(text: str, span: str) -> int:
    count = start = 0
    while True:
        i = text.find(span, start)
        if i < 0:
            return count
        count += 1
        start = i + 1


def main():
    crosswalk = json.loads((ROOT / "crosswalk" / "patterns.json").read_text(encoding="utf-8"))
    valid_ids = {p["id"] for p in crosswalk["patterns"]}
    seeded = ROOT / "seeded" / REGISTER
    manifest = json.loads((seeded / "manifest.json").read_text(encoding="utf-8"))
    errors = []
    for draft in manifest["drafts"]:
        did = draft["draft_id"]
        text = (seeded / f"{did}.md").read_text(encoding="utf-8")
        words = len(text.split())
        if not 300 <= words <= 600:
            errors.append(f"{did}: word count {words} outside 300-600")
        n = len(draft["plants"])
        if not 8 <= n <= 15:
            errors.append(f"{did}: {n} plants outside 8-15")
        for p in draft["plants"]:
            if p["pattern_id"] not in valid_ids:
                errors.append(f"{did}: unknown pattern_id {p['pattern_id']}")
            occ = occurrences(text, p["span"])
            if occ < p.get("occurrence", 1):
                errors.append(f"{did}: span not found x{p.get('occurrence', 1)}: {p['span']!r} (found {occ})")
        for d in draft.get("distractors", []):
            if occurrences(text, d["span"]) < 1:
                errors.append(f"{did}: distractor span not found: {d['span']!r}")
        print(f"{did}: {words} words, {n} plants, {len(draft.get('distractors', []))} distractors")
    if errors:
        print("\nFAILURES:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    total = sum(len(d["plants"]) for d in manifest["drafts"])
    tiers = {}
    for d in manifest["drafts"]:
        for p in d["plants"]:
            tiers[p["tier"]] = tiers.get(p["tier"], 0) + 1
    pids = {p["pattern_id"] for d in manifest["drafts"] for p in d["plants"]}
    print(f"\nOK: {total} plants across {len(manifest['drafts'])} drafts")
    print(f"tiers: {tiers}")
    print(f"patterns covered: {len(pids)}/{len(valid_ids)}")
    missing = valid_ids - pids
    if missing:
        print(f"uncovered pattern ids: {sorted(missing)}")


if __name__ == "__main__":
    main()
