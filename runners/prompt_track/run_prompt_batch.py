"""Prompt-track harness, Message Batches path: the canonical v0.1.1 run.

Same protocol as run_prompt_tool.py (the tool's ruleset files verbatim as the
system prompt, the uniform detect-only instruction, the pinned MODEL, sampling
and thinking left at the model's defaults), submitted through the Message
Batches API at half price. The system prompt carries a cache_control marker,
so each tool's ruleset is billed in full on a cache write and at the
cache-read rate on every hit after that. Cache hits in a batch are
best-effort; the cost report counts what the API actually billed.

Resumable by construction. Every succeeded response is saved under
results/prompt_runs/batch/responses/<custom_id>.json, and `submit` sends only
requests with neither a saved response nor a batch still in flight. Errored,
expired and canceled requests are not billed and simply become pending again.
A response that hit max_tokens or did not parse is billed, so it is kept and
reported by `assemble` rather than silently resent; `discard` sets it aside
(still counted in `cost`) so a deliberate resend can follow.

COST GATE: `submit` makes paid calls and refuses without --approved, and
without --expect N matching the number of requests it would send. Before
submitting it validates one request per tool against the free token-counting
endpoint, and refuses if the workspace has a batch this state file does not
know about (a lost create response would otherwise mean paying twice).

Usage:
  py run_prompt_batch.py plan   [--only GLOB ...]
  py run_prompt_batch.py submit --approved --expect N [--only GLOB ...]
  py run_prompt_batch.py wait   [--interval SECONDS]
  py run_prompt_batch.py cost
  py run_prompt_batch.py discard CUSTOM_ID [...]
  py run_prompt_batch.py assemble

custom_id is <short>-<set>-<file stem>-r<run>, e.g. aawskill-human-F_2021_mdna-r1;
--only takes fnmatch globs over it. `assemble` writes results/raw_<short>_<set>_run<n>.json
in the schema score.py reads and removes the superseded single-run
raw_<short>_human_finance.json files.

Stdlib only.
"""

import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from run_prompt_tool import (MAX_TOKENS, MODEL, ROOT, TOOL_REPO_DIR, TOOLS_DIR,
                             build_system_prompt, collect, load_api_key,
                             parse_findings)

SHORT = {
    "avoid-ai-writing-skill": "aawskill",
    "no-ai-slop": "noaislop",
    "stop-slop": "stopslop",
    "the-antislop": "theantislop",
}
SETS = {
    "seeded": ROOT / "seeded" / "finance-audit",
    "human": ROOT / "corpora" / "finance-audit" / "clean",
}
N_RUNS = 3
API = "https://api.anthropic.com/v1"
CACHE = {"type": "ephemeral", "ttl": "1h"}
# claude-sonnet-5 Message Batches prices, USD per million tokens: half of the
# list $2 input, $10 output, $4 one-hour cache write, $0.20 cache read.
# Thinking tokens are billed as output.
PRICE = {"input": 1.00, "output": 5.00, "cache_write_1h": 2.00,
         "cache_write_5m": 1.25, "cache_read": 0.10}

STATE_DIR = ROOT / "results" / "prompt_runs" / "batch"
RESP_DIR = STATE_DIR / "responses"
ERR_DIR = STATE_DIR / "errors"
DISCARD_DIR = STATE_DIR / "discarded"
STATE = STATE_DIR / "state.json"
CUSTOM_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def planned() -> dict:
    """Every request of the canonical run, keyed by custom_id."""
    plan = {}
    for tool, short in SHORT.items():
        for set_name, directory in SETS.items():
            for f in collect(directory):
                for n in range(1, N_RUNS + 1):
                    cid = f"{short}-{set_name}-{f.stem}-r{n}"
                    if not CUSTOM_ID.match(cid) or cid in plan:
                        sys.exit(f"bad or duplicate custom_id {cid}")
                    plan[cid] = {"tool": tool, "set": set_name, "file": f, "run": n}
    return plan


def selected(plan: dict, globs: list) -> list:
    return [c for c in plan if not globs or any(fnmatch.fnmatchcase(c, g) for g in globs)]


def globs_from(args: list) -> list:
    if "--only" not in args:
        return []
    globs = []
    for a in args[args.index("--only") + 1:]:
        if a.startswith("--"):
            break
        globs.append(a)
    # A bare --only must not silently widen to the whole run.
    if not globs:
        sys.exit("--only needs one or more globs after it")
    return globs


def flag_value(args: list, flag: str):
    if flag not in args or args.index(flag) + 1 >= len(args):
        return None
    return args[args.index(flag) + 1]


def load_state() -> dict:
    if STATE.is_file():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"batches": {}}


def save_state(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE)


def done_ids() -> set:
    return {p.stem for p in RESP_DIR.glob("*.json")} if RESP_DIR.is_dir() else set()


def inflight_ids(state: dict) -> set:
    # A batch counts as in flight until its results are collected, not merely
    # until it ends: otherwise an ended-but-uncollected batch would look
    # pending and be paid for twice.
    return {c for b in state["batches"].values() if not b.get("collected")
            for c in b["custom_ids"]}


def http(method: str, url: str, api_key: str, body=None, raw=False, create=False):
    """One API call with retries. A batch create is retried only on 429/529,
    which mean nothing was created; any other failure exits rather than risk
    submitting, and paying for, the same batch twice."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    if data is not None:
        headers["content-type"] = "application/json"
    retry_codes = (429, 529) if create else (429, 500, 502, 503, 529)
    for attempt in range(6):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                payload = resp.read()
                return payload if raw else json.loads(payload)
        except urllib.error.HTTPError as e:
            if e.code in retry_codes and attempt < 5:
                time.sleep(15 * (attempt + 1))
                continue
            detail = e.read().decode("utf-8", "replace")[:500]
            sys.exit(f"API error HTTP {e.code} on {method} {url}: {detail}")
        except (urllib.error.URLError, TimeoutError) as e:
            if not create and attempt < 5:
                time.sleep(15 * (attempt + 1))
                continue
            sys.exit(f"network error on {method} {url}: {e}. "
                     + ("The batch may or may not exist; check the Console's "
                        "Batches page before submitting again." if create else ""))
    raise RuntimeError("unreachable")


def request_params(system: str, text: str) -> dict:
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": [{"type": "text", "text": system, "cache_control": CACHE}],
        "messages": [{"role": "user", "content": text}],
    }


def tool_sha(tool: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=TOOLS_DIR / TOOL_REPO_DIR[tool]).decode().strip()


def usage_cost(u: dict) -> float:
    written = u.get("cache_creation_input_tokens", 0) or 0
    w1h = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) or 0
    return (u.get("input_tokens", 0) * PRICE["input"]
            + u.get("output_tokens", 0) * PRICE["output"]
            + w1h * PRICE["cache_write_1h"]
            + (written - w1h) * PRICE["cache_write_5m"]
            + (u.get("cache_read_input_tokens", 0) or 0) * PRICE["cache_read"]) / 1e6


def cmd_plan(args):
    plan = planned()
    state = load_state()
    done, inflight = done_ids(), inflight_ids(state)
    sel = selected(plan, globs_from(args))
    pending = [c for c in sel if c not in done and c not in inflight]
    print(f"planned {len(plan)} | selected {len(sel)} | saved {len(done & set(sel))} "
          f"| in flight {len(inflight & set(sel))} | pending {len(pending)}")
    for c in pending[:12]:
        print("  " + c)
    if len(pending) > 12:
        print(f"  ... and {len(pending) - 12} more")


def cmd_submit(args):
    if "--approved" not in args:
        sys.exit("Refusing to run: paid API calls need the --approved flag.")
    args = [a for a in args if a != "--approved"]
    plan = planned()
    state = load_state()
    done, inflight = done_ids(), inflight_ids(state)
    pending = [c for c in selected(plan, globs_from(args))
               if c not in done and c not in inflight]
    if not pending:
        sys.exit("nothing pending for that selection")
    # The caller states how many requests they mean to pay for; a selection
    # wider or narrower than intended is refused, not submitted.
    expect = flag_value(args, "--expect")
    if expect is None or not expect.isdigit() or int(expect) != len(pending):
        sys.exit(f"{len(pending)} requests pending for that selection; "
                 f"re-run with --expect {len(pending)} to submit them")
    api_key = load_api_key()

    listed = http("GET", f"{API}/messages/batches?limit=100", api_key)
    unknown = [b["id"] for b in listed.get("data", []) if b["id"] not in state["batches"]]
    if unknown:
        sys.exit(f"workspace has batches this state file does not know: {unknown}. "
                 f"Refusing to submit; reconcile them first.")

    tools = sorted({plan[c]["tool"] for c in pending})
    systems = {t: build_system_prompt(t) for t in tools}
    shas = {t: tool_sha(t) for t in tools}
    requests = [{"custom_id": c,
                 "params": request_params(systems[plan[c]["tool"]],
                                          plan[c]["file"].read_text(encoding="utf-8"))}
                for c in pending]
    for t in tools:
        first = next(r for r in requests if plan[r["custom_id"]]["tool"] == t)
        probe = {k: first["params"][k] for k in ("model", "system", "messages")}
        n = http("POST", f"{API}/messages/count_tokens", api_key, probe)["input_tokens"]
        print(f"validated {t}: {first['custom_id']} is {n} input tokens")

    batch = http("POST", f"{API}/messages/batches", api_key,
                 {"requests": requests}, create=True)
    state["batches"][batch["id"]] = {
        "custom_ids": pending,
        "status": batch.get("processing_status", "in_progress"),
        "created_at": batch.get("created_at"),
        "ended_at": None,
        "tool_shas": shas,
        "system_sha256": {t: hashlib.sha256(systems[t].encode("utf-8")).hexdigest()
                          for t in tools},
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
    }
    save_state(state)
    print(f"submitted {batch['id']}: {len(pending)} requests")


def fetch_results(bid: str, results_url: str, api_key: str) -> dict:
    RESP_DIR.mkdir(parents=True, exist_ok=True)
    ERR_DIR.mkdir(parents=True, exist_ok=True)
    counts = {}
    body = http("GET", results_url, api_key, raw=True).decode("utf-8")
    for line in body.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cid, result = row["custom_id"], row["result"]
        kind = result.get("type")
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "succeeded":
            (RESP_DIR / f"{cid}.json").write_text(
                json.dumps({"batch_id": bid, "message": result["message"]}, indent=2),
                encoding="utf-8")
        else:
            (ERR_DIR / f"{cid}.json").write_text(
                json.dumps({"batch_id": bid, "result": result}, indent=2),
                encoding="utf-8")
    return counts


def cmd_wait(args):
    interval = int(args[args.index("--interval") + 1]) if "--interval" in args else 60
    api_key = load_api_key()
    state = load_state()
    while True:
        still_open = False
        for bid, rec in state["batches"].items():
            if rec["status"] == "ended" and rec.get("collected"):
                continue
            b = http("GET", f"{API}/messages/batches/{bid}", api_key)
            rec["status"] = b["processing_status"]
            stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
            print(f"{stamp} {bid} {b['processing_status']} {b['request_counts']}", flush=True)
            if b["processing_status"] == "ended":
                rec["ended_at"] = b.get("ended_at")
                rec["counts"] = fetch_results(bid, b["results_url"], api_key)
                rec["collected"] = True
                print(f"  collected {rec['counts']}", flush=True)
            else:
                still_open = True
            save_state(state)
        if not still_open:
            break
        time.sleep(interval)
    cmd_cost([])


def cmd_discard(args):
    """Set aside billed responses that cannot be used (hit max_tokens, did not
    parse) so they become pending again. They move rather than vanish, so the
    cost report keeps counting what was billed for them."""
    if not args:
        sys.exit("usage: discard CUSTOM_ID [...]")
    DISCARD_DIR.mkdir(parents=True, exist_ok=True)
    for cid in args:
        src = RESP_DIR / f"{cid}.json"
        if not src.is_file():
            sys.exit(f"no saved response for {cid}")
        k = 1
        while (DISCARD_DIR / f"{cid}.{k}.json").exists():
            k += 1
        src.replace(DISCARD_DIR / f"{cid}.{k}.json")
        print(f"discarded {cid} -> discarded/{cid}.{k}.json (still counted as billed)")


def cmd_cost(args):
    plan = planned()
    by_tool, total, n, discarded = {}, 0.0, 0, 0.0
    tokens = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0, "thinking": 0}
    saved = sorted(RESP_DIR.glob("*.json")) if RESP_DIR.is_dir() else []
    thrown = sorted(DISCARD_DIR.glob("*.json")) if DISCARD_DIR.is_dir() else []
    for p in saved + thrown:
        msg = json.loads(p.read_text(encoding="utf-8"))["message"]
        u = msg.get("usage", {})
        c = usage_cost(u)
        cid = p.name.split(".")[0]
        tool = plan[cid]["tool"] if cid in plan else "unplanned"
        by_tool[tool] = by_tool.get(tool, 0.0) + c
        total += c
        if p in thrown:
            discarded += c
        else:
            n += 1
        tokens["input"] += u.get("input_tokens", 0)
        tokens["cache_write"] += u.get("cache_creation_input_tokens", 0) or 0
        tokens["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
        tokens["output"] += u.get("output_tokens", 0)
        tokens["thinking"] += (u.get("output_tokens_details") or {}).get("thinking_tokens", 0) or 0
    print(f"saved responses {n} of {len(plan)} planned")
    print("tokens " + ", ".join(f"{k} {v:,}" for k, v in tokens.items()))
    for tool, c in sorted(by_tool.items()):
        print(f"  {tool:24s} ${c:.2f}")
    if thrown:
        print(f"discarded but billed: {len(thrown)} responses, ${discarded:.2f}")
    print(f"billed so far (batch prices): ${total:.2f}")


def cmd_assemble(args):
    plan = planned()
    state = load_state()
    missing = [c for c in plan if not (RESP_DIR / f"{c}.json").is_file()]
    if missing:
        sys.exit(f"{len(missing)} planned responses missing, e.g. {missing[:5]}")
    runs, bad, batch_of = {}, [], {}
    for cid, p in plan.items():
        saved = json.loads((RESP_DIR / f"{cid}.json").read_text(encoding="utf-8"))
        msg, bid = saved["message"], saved["batch_id"]
        batch_of[cid] = bid
        if msg.get("stop_reason") == "max_tokens":
            bad.append(f"{cid}: hit max_tokens "
                       f"({state['batches'][bid].get('max_tokens')}); raise MAX_TOKENS before resending")
            continue
        findings = parse_findings("".join(b.get("text", "") for b in msg.get("content", [])))
        if findings is None:
            bad.append(f"{cid}: did not parse as the requested JSON array")
            continue
        key = (p["tool"], p["set"], p["run"])
        r = runs.setdefault(key, {"files": {}, "served": set(), "batches": set(),
                                  "usage": {"input": 0, "cache_write": 0, "cache_read": 0,
                                            "output": 0, "thinking": 0, "cost_usd": 0.0}})
        text = p["file"].read_text(encoding="utf-8")
        r["files"][p["file"].name] = {"words": len(text.split()), "findings": findings}
        r["served"].add(str(msg.get("model")))
        r["batches"].add(bid)
        u = msg.get("usage", {})
        r["usage"]["input"] += u.get("input_tokens", 0)
        r["usage"]["cache_write"] += u.get("cache_creation_input_tokens", 0) or 0
        r["usage"]["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
        r["usage"]["output"] += u.get("output_tokens", 0)
        r["usage"]["thinking"] += (u.get("output_tokens_details") or {}).get("thinking_tokens", 0) or 0
        r["usage"]["cost_usd"] += usage_cost(u)
    if bad:
        sys.exit("refusing to assemble; these billed responses are unusable and "
                 "need a deliberate, paid resend (`discard` them, then submit):\n  "
                 + "\n  ".join(bad))

    # Every response for a tool must come from one ruleset commit, one exact
    # system prompt (ruleset files plus the harness instruction, so an
    # uncommitted edit or an instruction change is caught), one model and one
    # max_tokens. Otherwise run-to-run spread would partly be a protocol change.
    recorded = {}
    for tool in SHORT:
        recs = [state["batches"][batch_of[c]] for c in plan if plan[c]["tool"] == tool]
        for field in ("tool_shas", "system_sha256"):
            vals = {r[field][tool] for r in recs}
            if len(vals) != 1:
                sys.exit(f"{tool} was run with more than one {field}: {sorted(vals)}")
        for field in ("model", "max_tokens"):
            vals = {r[field] for r in recs}
            if len(vals) != 1:
                sys.exit(f"{tool} was run with more than one {field}: {sorted(map(str, vals))}")
        recorded[tool] = {"sha": recs[0]["tool_shas"][tool],
                          "system_sha256": recs[0]["system_sha256"][tool],
                          "model": recs[0]["model"], "max_tokens": recs[0]["max_tokens"]}

    written = []
    for (tool, set_name, n), r in sorted(runs.items()):
        bids = sorted(r["batches"])
        ended = sorted((state["batches"][b].get("ended_at") or "")[:10] for b in bids)
        rec = recorded[tool]
        result = {
            "tool": tool,
            "sha": rec["sha"],
            "run_date": ended[-1],
            "run_n": n,
            "options": {
                "model": rec["model"], "max_tokens": rec["max_tokens"],
                "detect_instruction": "uniform-v1",
                "system_sha256": rec["system_sha256"],
                "api": "message-batches",
                "thinking": "model default (adaptive, effort high); not set by the harness",
                "prompt_caching": "system prompt, ephemeral 1h",
                "served_models": sorted(r["served"]),
                "batch_ids": bids,
                "usage": {k: (round(v, 4) if k == "cost_usd" else v)
                          for k, v in r["usage"].items()},
            },
            "files": dict(sorted(r["files"].items())),
        }
        out = ROOT / "results" / f"raw_{SHORT[tool]}_{set_name}_run{n}.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        written.append(out.name)
    for short in SHORT.values():
        old = ROOT / "results" / f"raw_{short}_human_finance.json"
        if old.is_file():
            old.unlink()
            print(f"removed superseded {old.name}")
    print("wrote " + ", ".join(written))
    cmd_cost([])


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    commands = {"plan": cmd_plan, "submit": cmd_submit, "wait": cmd_wait,
                "cost": cmd_cost, "discard": cmd_discard, "assemble": cmd_assemble}
    if cmd not in commands:
        sys.exit(f"unknown command {cmd}; choose from {sorted(commands)}")
    commands[cmd](args)


if __name__ == "__main__":
    main()
