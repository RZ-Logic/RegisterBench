"""Prose-filter the raw finance-audit corpus.

Filings contain financial tables that flatten into number-heavy lines when
HTML is stripped. Those lines are not prose and would dilute the flags/1k
metric, so this pass drops lines whose tokens are mostly numeric or symbolic,
plus short heading fragments, and writes clean/ files used for all scoring.
raw/ files are kept untouched as the provenance record.

Usage: py scripts/clean_corpus.py
"""

import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "corpora" / "finance-audit"
RAW = BASE / "raw"
CLEAN = BASE / "clean"

NUMERIC = re.compile(r"^[\d\$\.,%\(\)\-—/: ]+$")


def is_prose(line: str) -> bool:
    if not line:
        return True  # keep paragraph breaks
    tokens = line.split()
    if len(tokens) < 6:
        return False  # headings, table fragments, page markers
    numeric = sum(1 for t in tokens if NUMERIC.match(t))
    if numeric / len(tokens) > 0.4:
        return False
    # require sentence-like structure: some lowercase words
    lower = sum(1 for t in tokens if re.match(r"^[a-z]", t))
    return lower / len(tokens) > 0.3


def main():
    CLEAN.mkdir(exist_ok=True)
    total = 0
    for f in sorted(RAW.glob("*.txt")):
        lines = f.read_text(encoding="utf-8").split("\n")
        kept = [ln for ln in lines if is_prose(ln)]
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
        (CLEAN / f.name).write_text(text, encoding="utf-8")
        words = len(text.split())
        total += words
        print(f"{f.name}: {len(f.read_text(encoding='utf-8').split())} -> {words} words")
    print(f"\nClean total: {total} words -> {CLEAN}")


if __name__ == "__main__":
    main()
