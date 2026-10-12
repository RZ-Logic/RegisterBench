"""Prompt-track harness: run a tool's skill files verbatim as system prompt.

Protocol (spec 5.2): the tool's ruleset files, concatenated verbatim, become
the system prompt, followed by a uniform detect-only instruction. Fixed model
(MODEL below), N runs per draft, temperature default. Raw responses are saved
under results/prompt_runs/ and normalized findings under results/ in the
same schema the code-track runners emit, one file per run index so score.py
computes mean/min/max variance.

COST GATE: this script makes paid API calls. It refuses to run unless
--approved is passed. Reads REGISTERBENCH_API_KEY from the environment or
from the repo's gitignored .env; ANTHROPIC_API_KEY is deliberately ignored
(see load_api_key).

Usage:
  py run_prompt_tool.py --approved <tool> <out-prefix> <file-or-dir> [...]
  py run_prompt_tool.py --approved --smoke <tool> <file>
  tool: stop-slop | no-ai-slop | the-antislop | avoid-ai-writing-skill

--smoke makes exactly one call and prints the model actually served, the
stop reason and token usage. It writes only the raw response, under
results/prompt_runs/, never a file score.py reads.

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
# Sized for the worst case in the corpus: F_2021_mdna.txt is 20,281 words, and
# an aggressive ruleset flagging ~7 per 1,000 words emits ~140 findings, each a
# rule name plus a quote. A truncated response is a silent zero unless caught,
# and the bias would run against exactly the tools that flag most, so the
# harness treats truncation as fatal rather than recording an empty result.
# Thinking also counts against max_tokens: claude-sonnet-5 thinks adaptively
# by default (effort high), and the 2026-10-11 smoke call spent 6,888 thinking
# tokens on a 330-word draft. 16,000 was sized before that was known; 64,000
# leaves headroom for the long filings (the model's limit is 128K).
MAX_TOKENS = 64000
SYNC_MAX_WORDS = 5000

ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS_DIR = Path(os.environ.get("REGISTERBENCH_TOOLS_DIR", ROOT.parent / "tools"))
ENV_KEY = "REGISTERBENCH_API_KEY"
ENV_FILE = ROOT / ".env"
# Same skip set as the code-track runners: these describe a corpus, they are
# not documents in it, and sending one would be a paid call scored as a draft.
SKIP = {"readme.md", "provenance.md", "notes.md"}

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


def read_env_file(path: Path) -> dict:
    """Minimal KEY=VALUE reader for the repo's .env (stdlib only)."""
    if not path.is_file():
        return {}
    raw = path.read_bytes()
    # Windows PowerShell 5.1 `>` redirection writes UTF-16; Notepad may add a BOM.
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[key] = value
    return values


def load_api_key() -> str:
    """REGISTERBENCH_API_KEY from the environment, else from the repo's .env.

    Deliberately never ANTHROPIC_API_KEY. Other tools read that name, Claude
    Code among them, and a session that picks it up bills the API instead of
    a subscription. A dedicated name keeps the benchmark key, and its spend
    limit, scoped to this harness.
    """
    key = os.environ.get(ENV_KEY, "").strip()
    if key:
        return key
    from_file = read_env_file(ENV_FILE)
    key = from_file.get(ENV_KEY, "").strip()
    if key:
        return key
    hint = ""
    if "ANTHROPIC_API_KEY" in from_file or os.environ.get("ANTHROPIC_API_KEY"):
        hint = (" ANTHROPIC_API_KEY was found but is deliberately not read;"
                f" rename it to {ENV_KEY}.")
    sys.exit(f"{ENV_KEY} not set. Add a line {ENV_KEY}=<key> to {ENV_FILE}"
             f" (gitignored; see .env.example) or set it in the environment.{hint}")


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
            with urllib.request.urlopen(req, timeout=900) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 529) and attempt < 4:
                time.sleep(10 * (attempt + 1))
                continue
            # The error body names the cause (bad key, unknown model, spend
            # limit reached) and never echoes the key.
            detail = e.read().decode("utf-8", "replace")[:500]
            sys.exit(f"API error HTTP {e.code}: {detail}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            # Not retried: the request was sent and may already be generating
            # and billed. Re-running resumes from saved raw responses.
            sys.exit(f"network error after sending ({e!r}); the call may have "
                     f"been billed. Check the Console usage page before re-running.")
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
    # Strict schema. Every element must be {"rule": str, "quote": str}, both
    # non-empty. Dropping a malformed element instead would let [{}] or
    # ["bad response"] score as a clean empty result, indistinguishable from a
    # tool that genuinely found nothing, so any malformed element makes the
    # whole response unparseable and the harness refuses it.
    if not isinstance(arr, list):
        return None
    out = []
    for item in arr:
        if not isinstance(item, dict):
            return None
        rule, quote = item.get("rule"), item.get("quote")
        if not (isinstance(rule, str) and rule.strip() and isinstance(quote, str) and quote.strip()):
            return None
        out.append({"rule": rule, "text": quote, "index": None, "severity": None})
    return out


def collect(p: Path):
    if p.is_dir():
        return sorted(f for f in p.iterdir()
                      if f.suffix in (".txt", ".md") and f.name.lower() not in SKIP)
    return [p]


def main():
    args = sys.argv[1:]
    if "--approved" not in args:
        sys.exit("Refusing to run: paid API calls need the --approved flag "
                 "(API budget is an open item; see the brief, section 10).")
    args.remove("--approved")
    smoke = "--smoke" in args
    if smoke:
        args.remove("--smoke")
        if len(args) != 2 or not Path(args[1]).is_file():
            sys.exit("usage: py run_prompt_tool.py --approved --smoke <tool> <file>")
        tool, out_prefix, inputs = args[0], None, args[1:]
    else:
        if len(args) < 3:
            sys.exit("usage: py run_prompt_tool.py --approved <tool> <out-prefix> <file-or-dir> [...]")
        tool, out_prefix, inputs = args[0], args[1], args[2:]
    if tool not in RULESET_FILES:
        sys.exit(f"unknown tool {tool}; choose from {sorted(RULESET_FILES)}")
    api_key = load_api_key()

    import subprocess
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=TOOLS_DIR / TOOL_REPO_DIR[tool]).decode().strip()
    system = build_system_prompt(tool)
    raw_dir = ROOT / "results" / "prompt_runs"
    raw_dir.mkdir(exist_ok=True)

    if smoke:
        file = Path(inputs[0])
        resp = call_api(system, file.read_text(encoding="utf-8"), api_key)
        raw_path = raw_dir / f"smoke_{tool}_{file.stem}.json"
        raw_path.write_text(json.dumps(resp, indent=2), encoding="utf-8")
        findings = parse_findings(
            "".join(b.get("text", "") for b in resp.get("content", [])))
        usage = resp.get("usage", {})
        print(f"requested model: {MODEL}")
        print(f"served model:    {resp.get('model')}")
        print(f"stop_reason:     {resp.get('stop_reason')}")
        print(f"tokens:          {usage.get('input_tokens')} in, "
              f"{usage.get('output_tokens')} out")
        print(f"findings:        "
              f"{'UNPARSEABLE' if findings is None else len(findings)}")
        print(f"raw response:    {raw_path}")
        if findings is None or resp.get("stop_reason") == "max_tokens":
            sys.exit(1)
        return

    files = [f for inp in inputs for f in collect(Path(inp))]
    # A non-streaming call on a long filing can outlast the socket timeout or
    # an idle-connection drop after it has been billed. Long inputs go through
    # run_prompt_batch.py, which has no such window.
    too_long = [f.name for f in files if len(f.read_text(encoding="utf-8").split()) > SYNC_MAX_WORDS]
    if too_long:
        sys.exit(f"{len(too_long)} inputs exceed {SYNC_MAX_WORDS:,} words "
                 f"({', '.join(too_long[:3])}...); use run_prompt_batch.py for them.")
    for n in range(1, N_RUNS + 1):
        result = {
            "tool": tool, "sha": sha, "run_date": date.today().isoformat(),
            "run_n": n,
            "options": {"model": MODEL, "max_tokens": MAX_TOKENS,
                        "detect_instruction": "uniform-v1"},
            "files": {},
        }
        served = set()
        for file in files:
            text = file.read_text(encoding="utf-8")
            raw_path = raw_dir / f"{tool}_{file.stem}_run{n}.json"
            saved = (json.loads(raw_path.read_text(encoding="utf-8"))
                     if raw_path.is_file() else None)
            if saved and saved.get("stop_reason") == "end_turn" and saved.get("model") == MODEL:
                # Resume: a completed, billed response is reused, never re-bought.
                resp = saved
                print(f"{tool} run{n} {file.name}: reusing saved response")
            else:
                resp = call_api(system, text, api_key)
                raw_path.write_text(json.dumps(resp, indent=2), encoding="utf-8")
            served.add(str(resp.get("model")))
            if resp.get("stop_reason") == "max_tokens":
                sys.exit(
                    f"FATAL {file.name} run{n}: response hit max_tokens "
                    f"({MAX_TOKENS}). Recording this as zero findings would "
                    f"understate the most aggressive tools and silently bias "
                    f"flags/1k. Raise MAX_TOKENS or chunk the input, then "
                    f"re-run. Raw response saved to {raw_path}.")
            content = "".join(
                b.get("text", "") for b in resp.get("content", []))
            findings = parse_findings(content)
            if findings is None:
                sys.exit(
                    f"FATAL {file.name} run{n}: response did not parse as the "
                    f"requested JSON array. An empty result here is "
                    f"indistinguishable from a genuine zero, so the harness "
                    f"refuses to guess. Raw response saved to {raw_path}.")
            result["files"][file.name] = {
                "words": len(text.split()),
                "findings": findings,
            }
            print(f"{tool} run{n} {file.name}: {len(findings)} findings")
            time.sleep(1)
        # The API echoes the model it actually served; recorded so the pinned
        # MODEL above is verifiable from the result file, not just asserted.
        result["options"]["served_models"] = sorted(served)
        out = ROOT / "results" / f"{out_prefix}_run{n}.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"-> {out}")


if __name__ == "__main__":
    main()
