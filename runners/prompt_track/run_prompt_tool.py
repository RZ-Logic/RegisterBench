"""Prompt-track harness: run a tool's skill files verbatim as system prompt.

Protocol (spec 5.2): the tool's ruleset files, concatenated verbatim, become
the system prompt, followed by a uniform detect-only instruction. Fixed model
(MODEL below), N runs per draft, temperature default. Raw responses are saved
under results/prompt_runs/ and normalized findings under results/ in the
same schema the code-track runners emit, one file per run index so score.py
computes mean/min/max variance.

COST GATE: this script makes paid API calls. It refuses to run unless
--approved is passed. Requires ANTHROPIC_API_KEY in the environment.

Usage:
  py run_prompt_tool.py --approved <tool> <out-prefix> <file-or-dir> [...]
  tool: stop-slop | no-ai-slop | the-antislop | avoid-ai-writing-skill

Stdlib only.
"""

import json
import os
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

MODEL = "claude-sonnet-5"   # pinned per Rizwan 2026-07-24 (supersedes the brief's 4-6); do not float
N_RUNS = 3
MAX_TOKENS = 4000

ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS_DIR = Path(os.environ.get("REGISTERBENCH_TOOLS_DIR", ROOT.parent / "tools"))

RULESET_FILES = {
    "stop-slop": ["SKILL.md", "references/phrases.md",
                  "references/structures.md", "references/examples.md"],
    "no-ai-slop": ["SKILL.md", "eval.md"],
    "the-antislop": ["SKILL.md"],
    "avoid-ai-writing-skill": ["SKILL.md"],
}
TOOL_REPO_DIR = {
    "stop-slop": "stop-slop",
    "no-ai-slop": "no-ai-slop",
    "the-antislop": "the-antislop",
    "avoid-ai-writing-skill": "avoid-ai-writing",
}

DETECT_INSTRUCTION = """
---
BENCHMARK INSTRUCTION (appended by the harness, applies regardless of any
workflow above): Operate in detect-only / audit-only mode. Do not rewrite,
edit, or score the text, and do not state or imply whether AI wrote it.
Apply the ruleset above to the text the user provides. Report every place a
rule of the ruleset fires. Respond with a JSON array only, no prose before or
after, where each element is:
  {"rule": "<the ruleset's own name for the pattern>",
   "quote": "<the exact text span that triggered it, copied verbatim>"}
If nothing fires, respond with [].
"""


def build_system_prompt(tool: str) -> str:
    repo = TOOLS_DIR / TOOL_REPO_DIR[tool]
    parts = []
    for rel in RULESET_FILES[tool]:
        parts.append(f"<!-- file: {rel} -->\n" + (repo / rel).read_text(encoding="utf-8"))
    return "\n\n".join(parts) + "\n" + DETECT_INSTRUCTION


def call_api(system: str, user_text: str, api_key: str) -> dict:
    body = json.dumps({
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user_text}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        })
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 529) and attempt < 4:
                time.sleep(10 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def parse_findings(response_text: str):
    t = response_text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("["):]
    start, end = t.find("["), t.rfind("]")
    if start < 0 or end < 0:
        return None
    try:
        arr = json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None
    out = []
    for item in arr:
        if isinstance(item, dict) and "quote" in item:
            out.append({"rule": str(item.get("rule", "unnamed")),
                        "text": str(item["quote"]), "index": None,
                        "severity": None})
    return out


def collect(p: Path):
    if p.is_dir():
        return sorted(f for f in p.iterdir() if f.suffix in (".txt", ".md"))
    return [p]


def main():
    args = sys.argv[1:]
    if "--approved" not in args:
        sys.exit("Refusing to run: paid API calls need the --approved flag "
                 "(API budget is an open item; see the brief, section 10).")
    args.remove("--approved")
    if len(args) < 3:
        sys.exit("usage: py run_prompt_tool.py --approved <tool> <out-prefix> <file-or-dir> [...]")
    tool, out_prefix, inputs = args[0], args[1], args[2:]
    if tool not in RULESET_FILES:
        sys.exit(f"unknown tool {tool}; choose from {sorted(RULESET_FILES)}")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY not set")

    import subprocess
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=TOOLS_DIR / TOOL_REPO_DIR[tool]).decode().strip()
    system = build_system_prompt(tool)
    raw_dir = ROOT / "results" / "prompt_runs"
    raw_dir.mkdir(exist_ok=True)

    files = [f for inp in inputs for f in collect(Path(inp))]
    for n in range(1, N_RUNS + 1):
        result = {
            "tool": tool, "sha": sha, "run_date": date.today().isoformat(),
            "run_n": n,
            "options": {"model": MODEL, "max_tokens": MAX_TOKENS,
                        "detect_instruction": "uniform-v1"},
            "files": {},
        }
        for file in files:
            text = file.read_text(encoding="utf-8")
            resp = call_api(system, text, api_key)
            raw_path = raw_dir / f"{tool}_{file.stem}_run{n}.json"
            raw_path.write_text(json.dumps(resp, indent=2), encoding="utf-8")
            content = "".join(
                b.get("text", "") for b in resp.get("content", []))
            findings = parse_findings(content)
            if findings is None:
                print(f"WARN {file.name} run{n}: unparseable response, logged raw")
                findings = []
            result["files"][file.name] = {
                "words": len(text.split()),
                "findings": findings,
            }
            print(f"{tool} run{n} {file.name}: {len(findings)} findings")
            time.sleep(1)
        out = ROOT / "results" / f"{out_prefix}_run{n}.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"-> {out}")


if __name__ == "__main__":
    main()
