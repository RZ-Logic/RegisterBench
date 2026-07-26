"""Ingest the full prompt-track workflow output into runner-schema JSON.

Reads a scratch JSON file holding the Workflow tool's raw return value (a
flat array of {kind, tool, file|draft, run?, result:{findings:[...]}} job
records), groups it by tool (human corpus) and by tool+run (seeded drafts),
attaches authoritative word counts (from the already-verified clean_corpus.py
and verify_manifest.py runs, not re-derived here), and writes results/raw_*
files in the same schema the code-track runners produce so score.py can
consume them unmodified.

Also removes the superseded N=1 preview files (raw_*_seeded_finance_preview.json),
which used coarser per-tool-all-drafts granularity.

Usage: py scripts/ingest_prompt_full_run.py <scratch_input.json>
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CLEAN_WORDS = {
    "AAPL_2020_mdna.txt": 4264, "AAPL_2020_opinion.txt": 1380,
    "CAT_2021_mdna.txt": 14547, "CAT_2021_opinion.txt": 1857,
    "DAL_2021_mdna.txt": 14759, "DAL_2021_opinion.txt": 1898,
    "DE_2020_opinion.txt": 2072, "F_2021_mdna.txt": 20281,
    "F_2021_opinion.txt": 2160, "HD_2021_mdna.txt": 4772,
    "HD_2021_opinion.txt": 1339, "JNJ_2021_mdna.txt": 9300,
    "JNJ_2021_opinion.txt": 2980, "KO_2021_opinion.txt": 1909,
    "MMM_2021_mdna.txt": 16541, "MMM_2021_opinion.txt": 1240,
    "MSFT_2020_mdna.txt": 8784, "MSFT_2020_opinion.txt": 1230,
}
DRAFT_WORDS = {
    "fin-01.md": 371, "fin-02.md": 379, "fin-03.md": 397, "fin-04.md": 356,
    "fin-05.md": 349, "fin-06.md": 342, "fin-07.md": 355, "fin-08.md": 361,
    "fin-09.md": 354, "fin-10.md": 330,
}
SHAS = {
    "stop-slop": "8da1f030185bdfe8471220585162991eaeb970e9",
    "no-ai-slop": "61c21c351da4dcb40946a11fead978f2078a2c65",
    "the-antislop": "5edbf8562041fc99070e1bd51e0862afbb535fff",
    "avoid-ai-writing-skill": "27156c7ae69fade80f2a3410e6899b780248709d",
}
TOOLKEY_FILE = {
    "stop-slop": "stopslop", "no-ai-slop": "noaislop",
    "the-antislop": "theantislop", "avoid-ai-writing-skill": "aawskill",
}
NOTE_HUMAN = (
    "FULL RUN via Claude Code subagent (model override 'sonnet' -> claude-sonnet-5), "
    "not the raw Anthropic API; ruleset files delivered as agent task instructions "
    "rather than a literal system prompt. Whole 18-document clean/ corpus, one pass "
    "per tool. See NOTES.md."
)
NOTE_SEEDED = (
    "FULL RUN via Claude Code subagent (model override 'sonnet' -> claude-sonnet-5), "
    "not the raw Anthropic API; ruleset files delivered as agent task instructions "
    "rather than a literal system prompt. One independent pass per draft per run "
    "(matches the API harness's per-file call granularity). Supersedes the earlier "
    "N=1 preview files, which used coarser per-tool-all-drafts granularity."
)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: py scripts/ingest_prompt_full_run.py <scratch_input.json>")
    raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    human_by_tool = {}
    seeded_by_tool_run = {}
    skipped = 0
    for job in raw:
        result = job.get("result") or {}
        findings = [
            {"rule": f.get("rule", "unnamed"), "text": f.get("quote", ""),
             "index": None, "severity": None}
            for f in (result.get("findings") or [])
        ]
        if job["kind"] == "human":
            tool, fname = job["tool"], job["file"]
            if fname not in CLEAN_WORDS:
                skipped += 1
                continue
            human_by_tool.setdefault(tool, {})[fname] = {
                "words": CLEAN_WORDS[fname], "findings": findings}
        else:
            tool, draft, run = job["tool"], job["draft"], job["run"]
            if draft not in DRAFT_WORDS:
                skipped += 1
                continue
            seeded_by_tool_run.setdefault((tool, run), {})[draft] = {
                "words": DRAFT_WORDS[draft], "findings": findings}

    results_dir = ROOT / "results"
    written = []
    for tool, files in human_by_tool.items():
        out = {"tool": tool, "sha": SHAS[tool], "run_date": "2026-07-24",
               "options": {"model": "claude-sonnet-5", "note": NOTE_HUMAN},
               "files": files}
        path = results_dir / f"raw_{TOOLKEY_FILE[tool]}_human_finance.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        written.append(str(path))

    for (tool, run), files in seeded_by_tool_run.items():
        out = {"tool": tool, "sha": SHAS[tool], "run_date": "2026-07-24", "run_n": run,
               "options": {"model": "claude-sonnet-5", "note": NOTE_SEEDED},
               "files": files}
        path = results_dir / f"raw_{TOOLKEY_FILE[tool]}_seeded_run{run}.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        written.append(str(path))

    removed = []
    for tool_key in TOOLKEY_FILE.values():
        old = results_dir / f"raw_{tool_key}_seeded_finance_preview.json"
        if old.exists():
            old.unlink()
            removed.append(str(old))

    print(f"wrote {len(written)} files, removed {len(removed)} superseded preview files, "
          f"skipped {skipped} jobs with unknown filenames")
    for w in written:
        print("  +", w)
    for r in removed:
        print("  -", r)


if __name__ == "__main__":
    main()
