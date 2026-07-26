"""Run unslop's deterministic layer over text files, emit normalized findings.

Calls humanize_deterministic_with_report directly (bypasses the CLI file-type
gate). Intensity 'full' for maximum deterministic rule coverage; structural
and soul passes disabled because they are rewrites (sentence splitting,
contraction lifts), not slop detections. Voice profiles never touch the
deterministic layer, so runs are voice-neutral by construction.

unslop reports rule/before/after with no character offsets, so index is null;
score.py matches its findings by text containment.

Usage: py run_unslop.py <out.json> <file-or-dir> [...]
Env:   REGISTERBENCH_TOOLS_DIR overrides the default ../../../tools location.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(os.environ.get(
    "REGISTERBENCH_TOOLS_DIR",
    Path(__file__).resolve().parent.parent.parent.parent / "tools"))
TOOL_DIR = TOOLS_DIR / "unslop"
sys.path.insert(0, str(TOOL_DIR / "unslop"))

from scripts.humanize import humanize_deterministic_with_report  # noqa: E402

INTENSITY = "full"


def collect(p: Path):
    if p.is_dir():
        return sorted(f for f in p.iterdir() if f.suffix in (".txt", ".md"))
    return [p]


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: py run_unslop.py <out.json> <file-or-dir> [...]")
    out_file, inputs = sys.argv[1], sys.argv[2:]
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=TOOL_DIR).decode().strip()
    result = {
        "tool": "unslop-deterministic",
        "sha": sha,
        # UTC, matching run_avoid_ai_writing.js, so a single reproduction
        # cannot stamp two different dates on its own outputs.
        "run_date": datetime.now(timezone.utc).date().isoformat(),
        "options": {"intensity": INTENSITY, "structural": False, "soul": False},
        "files": {},
    }
    for inp in inputs:
        for file in collect(Path(inp)):
            text = file.read_text(encoding="utf-8")
            _, report = humanize_deterministic_with_report(
                text, intensity=INTENSITY, structural=False, soul=False)
            rep = report.to_dict()
            findings = [
                {"rule": r["rule"], "text": r["before"], "index": None,
                 "severity": None}
                for r in rep.get("replacements", [])
            ]
            capped = rep.get("em_dashes_before", 0) - rep.get("em_dashes_after", 0)
            findings += [
                {"rule": "em_dash_cap", "text": "—", "index": None,
                 "severity": None}
                for _ in range(max(0, capped))
            ]
            result["files"][file.name] = {
                "words": len(text.split()),
                "findings": findings,
            }
    Path(out_file).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"unslop-deterministic: {len(result['files'])} files -> {out_file}")


if __name__ == "__main__":
    main()
