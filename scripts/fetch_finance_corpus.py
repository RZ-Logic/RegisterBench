"""Fetch the finance-audit corpus from SEC EDGAR.

Downloads one 10-K per company (filed 2019-2021, fiscal years 2018-2021),
extracts the Item 7 MD&A section and the audit opinion (Report of Independent
Registered Public Accounting Firm), and writes plain-text files plus a
PROVENANCE.md with source URLs, accession numbers, and retrieval dates.

All source text is pre-November-2022 and public domain (SEC filings).
Stdlib only. Usage: py scripts/fetch_finance_corpus.py
"""

import json
import re
import time
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "corpora" / "finance-audit" / "raw"
PROVENANCE = OUT_DIR.parent / "PROVENANCE.md"

# SEC fair-access policy requires a descriptive User-Agent with contact info.
UA = "slopbench benchmark research (rizwan.ahmed109@gmail.com)"

# CIK, ticker, company. One 10-K each, latest filed on or before CUTOFF.
COMPANIES = [
    (320193, "AAPL", "Apple Inc."),
    (789019, "MSFT", "Microsoft Corporation"),
    (21344, "KO", "The Coca-Cola Company"),
    (200406, "JNJ", "Johnson & Johnson"),
    (104169, "WMT", "Walmart Inc."),
    (37996, "F", "Ford Motor Company"),
    (354950, "HD", "The Home Depot, Inc."),
    (27904, "DAL", "Delta Air Lines, Inc."),
    (80424, "PG", "The Procter & Gamble Company"),
    (18230, "CAT", "Caterpillar Inc."),
    (315189, "DE", "Deere & Company"),
    (66740, "MMM", "3M Company"),
]

CUTOFF = "2021-06-30"  # filing date ceiling; keeps fiscal years 2018-2020
FLOOR = "2019-01-01"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


class TextExtractor(HTMLParser):
    """HTML to text, preserving block boundaries as newlines."""

    BLOCK = {"p", "div", "tr", "br", "li", "h1", "h2", "h3", "h4", "table", "hr"}
    SKIP = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = raw.replace(" ", " ").replace("’", "'").replace("‘", "'")
        raw = raw.replace("“", '"').replace("”", '"')
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.split("\n")]
        out, blank = [], 0
        for ln in lines:
            if ln:
                out.append(ln)
                blank = 0
            else:
                blank += 1
                if blank == 1:
                    out.append("")
        return "\n".join(out).strip()


def html_to_text(html: str) -> str:
    p = TextExtractor()
    p.feed(html)
    return p.text()


def find_sections(text: str):
    """Return (mdna, opinion) extracted from full filing text, or Nones."""
    # Item 7 MD&A: choose the Item 7 -> Item 7A/8 span with the most content
    # (skips table-of-contents hits, which produce tiny spans).
    starts = [m.start() for m in re.finditer(
        r"(?im)^\s*item\s*7\.?\s*\n?\s*management'?s discussion", text)]
    if not starts:
        starts = [m.start() for m in re.finditer(
            r"(?i)item\s*7\.?\s{0,4}management'?s discussion", text)]
    ends_re = re.compile(r"(?i)item\s*7A\.?\s{0,4}(quantitative|qualitative)|item\s*8\.?\s{0,4}(financial statements|consolidated)")
    best = None
    for s in starts:
        m = ends_re.search(text, s + 100)
        e = m.start() if m else len(text)
        span = text[s:e]
        if best is None or len(span) > len(best):
            best = span
    mdna = best if best and len(best.split()) > 500 else None

    # Audit opinion: from the report heading to a statements heading or cap.
    op = None
    heads = [m.start() for m in re.finditer(
        r"(?i)report of independent registered public accounting firm", text)]
    for h in heads:
        chunk = text[h:h + 30000]
        if not re.search(r"(?i)we have audited", chunk[:6000]):
            continue  # TOC or exhibit-index hit
        endm = re.search(
            r"(?i)\n\s*(consolidated (balance sheets?|statements? of)|"
            r"item\s*9\.?)", chunk[500:])
        op = chunk[: endm.start() + 500] if endm else chunk[:15000]
        break
    if op and len(op.split()) < 250:
        op = None
    return mdna, op


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prov = [
        "# Provenance: finance-audit corpus",
        "",
        "All files below are extracted from SEC EDGAR filings (public domain).",
        "Every source document was filed before November 2022. Extraction:",
        "scripts/fetch_finance_corpus.py (HTML to text, Item 7 and audit",
        f"opinion section slicing). Retrieved {date.today().isoformat()}.",
        "",
        "| file | company | CIK | form | filed | accession | words | source URL |",
        "|---|---|---|---|---|---|---|---|",
    ]
    total_words = 0
    n_docs = 0
    for cik, ticker, name in COMPANIES:
        try:
            sub = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))
            recent = sub["filings"]["recent"]
            candidates = [
                (recent["filingDate"][i], recent["accessionNumber"][i],
                 recent["primaryDocument"][i])
                for i in range(len(recent["form"]))
                if recent["form"][i] == "10-K"
                and FLOOR <= recent["filingDate"][i] <= CUTOFF
            ]
            if not candidates:
                print(f"{ticker}: no 10-K in window, skipping")
                continue
            filed, acc, doc = sorted(candidates)[-1]
            acc_nodash = acc.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"
            time.sleep(0.3)
            html = get(url).decode("utf-8", errors="replace")
            text = html_to_text(html)
            mdna, opinion = find_sections(text)
            for label, body in (("mdna", mdna), ("opinion", opinion)):
                if not body:
                    print(f"{ticker}: {label} extraction FAILED")
                    continue
                fname = f"{ticker}_{filed[:4]}_{label}.txt"
                (OUT_DIR / fname).write_text(body, encoding="utf-8")
                words = len(body.split())
                total_words += words
                n_docs += 1
                prov.append(
                    f"| {fname} | {name} | {cik} | 10-K | {filed} | {acc} | {words} | {url} |")
                print(f"{ticker}: {label} ok ({words} words)")
            time.sleep(0.3)
        except Exception as exc:  # keep going; report at end
            print(f"{ticker}: ERROR {exc}")
    prov += ["", f"Total: {n_docs} documents, {total_words} words."]
    PROVENANCE.write_text("\n".join(prov) + "\n", encoding="utf-8")
    print(f"\nDone: {n_docs} docs, {total_words} words -> {OUT_DIR}")


if __name__ == "__main__":
    main()
