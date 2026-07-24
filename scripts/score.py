"""Score slopbench runner outputs: recall, flags/1k, ToA violations, variance.

Inputs: every results/raw_*.json runner output (normalized schema produced by
runners/). A run whose file names match seeded draft ids is treated as a
seeded run; anything else is a human-corpus run. Prompt-track runs may carry
"run_n" for N-run variance.

Matching (spec 5.2): a plant is recalled if any finding overlaps its span.
With a char index, overlap = shared chars / min(span lengths) >= 0.5.
Without an index, every occurrence of the finding text is located and the
same overlap test applies; doc-level findings (density, rates, rhythm) match
plants of their crosswalked canonical pattern anywhere in the draft.

Outputs: results/{register}_{date}.md (tables) and .json (full detail).

Usage: py scripts/score.py [register]
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTER = sys.argv[1] if len(sys.argv) > 1 else "finance-audit"

# Findings whose text is a description, not a quote. They match plants of
# their canonical pattern anywhere in the document.
DOC_LEVEL_RULES = {
    "em-dash", "em_dash_cap", "uniformity", "punct-distribution",
    "fnword-trigram-entropy", "cross-para-burstiness", "low-ttr",
    "smart-punct-signature", "formatting", "normalization-flag",
}
AAW_TIER3_RE = re.compile(r'^"(.+)" x\d+$')


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def find_all(text: str, needle: str):
    spans, start = [], 0
    while True:
        i = text.find(needle, start)
        if i < 0:
            return spans
        spans.append((i, i + len(needle)))
        start = i + 1


def overlap_ratio(a, b):
    shared = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    return shared / max(1, min(a[1] - a[0], b[1] - b[0]))


def plant_range(text: str, span: str, occurrence: int):
    spans = find_all(text, span)
    return spans[occurrence - 1] if len(spans) >= occurrence else None


def load_crosswalk():
    cw = json.loads((ROOT / "crosswalk" / "patterns.json").read_text(encoding="utf-8"))
    rule_to_canon = {}   # tool -> rule string -> set of canonical ids
    claimed = {}         # tool -> set of canonical ids with a non-empty map
    for p in cw["patterns"]:
        for tool, rules in p["map"].items():
            claimed.setdefault(tool, set())
            if rules:
                claimed[tool].add(p["id"])
            for r in rules:
                rule_to_canon.setdefault(tool, {}).setdefault(r, set()).add(p["id"])
    return cw, rule_to_canon, claimed


def canon_ids(tool, rule, rule_to_canon):
    table = rule_to_canon.get(tool, {})
    if rule in table:
        return table[rule]
    # prompt-track rule names are free text; match by containment either way
    out = set()
    nr = norm(rule)
    for known, ids in table.items():
        nk = norm(known)
        if nk in nr or nr in nk:
            out |= ids
    return out


def match_seeded(run, manifest, rule_to_canon):
    """Per-draft recall bookkeeping for one run."""
    tool = run["tool"]
    per_pattern = {}
    per_tier = {}
    matched_total = 0
    plants_total = 0
    unmatched_flags = []
    for draft in manifest["drafts"]:
        did = draft["draft_id"]
        fname = f"{did}.md"
        if fname not in run["files"]:
            continue
        text = (ROOT / "seeded" / REGISTER / fname).read_text(encoding="utf-8")
        findings = run["files"][fname]["findings"]
        # resolve finding char ranges (None = doc-level)
        resolved = []
        for f in findings:
            rule, ftext = f["rule"], f["text"]
            m = AAW_TIER3_RE.match(ftext or "")
            if rule in DOC_LEVEL_RULES:
                resolved.append((f, None))
            elif rule == "tier3" and m:
                resolved.append((f, [s for s in find_all(text, m.group(1))]))
            elif f.get("index") is not None:
                resolved.append((f, [(f["index"], f["index"] + len(ftext))]))
            else:
                occ = find_all(text, ftext)
                if not occ:
                    # try case-insensitive locate
                    occ = [(m2.start(), m2.end()) for m2 in
                           re.finditer(re.escape(ftext), text, re.I)]
                resolved.append((f, occ))
        used = [False] * len(resolved)
        for plant in draft["plants"]:
            pid = plant["pattern_id"]
            plants_total += 1
            per_pattern.setdefault(pid, [0, 0])[1] += 1
            per_tier.setdefault(plant["tier"], [0, 0])[1] += 1
            prange = plant_range(text, plant["span"], plant.get("occurrence", 1))
            hit = False
            if prange:
                for k, (f, ranges) in enumerate(resolved):
                    if ranges is None:
                        # doc-level: credit if canonical pattern matches
                        if pid in canon_ids(tool, f["rule"], rule_to_canon):
                            hit = True
                            used[k] = True
                            break
                    else:
                        if any(overlap_ratio(prange, r) >= 0.5 for r in ranges):
                            hit = True
                            used[k] = True
                            break
            if hit:
                matched_total += 1
                per_pattern[pid][0] += 1
                per_tier[plant["tier"]][0] += 1
        for k, (f, _) in enumerate(resolved):
            if not used[k]:
                unmatched_flags.append({"draft": did, "rule": f["rule"], "text": f["text"]})
    return {
        "recall": matched_total / plants_total if plants_total else None,
        "matched": matched_total,
        "plants": plants_total,
        "per_pattern": {k: {"matched": v[0], "planted": v[1]} for k, v in sorted(per_pattern.items())},
        "per_tier": {k: {"matched": v[0], "planted": v[1]} for k, v in sorted(per_tier.items())},
        "unmatched_flag_count": len(unmatched_flags),
        "unmatched_flags": unmatched_flags,
    }


def score_human(run, whitelist):
    terms = []
    for t in whitelist["terms"]:
        terms.append(t["term"])
        terms.extend(t.get("variants", []))
    total_words = 0
    total_flags = 0
    toa_hits = 0
    toa_examples = []
    corpus_dir = ROOT / "corpora" / REGISTER / "clean"
    for fname, data in run["files"].items():
        total_words += data["words"]
        total_flags += len(data["findings"])
        path = corpus_dir / fname
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        term_spans = []
        for t in terms:
            term_spans += find_all(lower, t.lower())
        for f in data["findings"]:
            ftext = f["text"] or ""
            if f.get("rule") in DOC_LEVEL_RULES:
                continue
            if f.get("index") is not None:
                ranges = [(f["index"], f["index"] + len(ftext))]
            else:
                ranges = find_all(lower, ftext.lower())
            if any(overlap_ratio(r, ts) >= 0.5 for r in ranges for ts in term_spans):
                toa_hits += 1
                if len(toa_examples) < 25:
                    toa_examples.append({"file": fname, "rule": f["rule"], "text": ftext})
    return {
        "words": total_words,
        "flags": total_flags,
        "flags_per_1k": round(total_flags / total_words * 1000, 2) if total_words else None,
        "toa_violations": toa_hits,
        "toa_per_1k": round(toa_hits / total_words * 1000, 3) if total_words else None,
        "toa_examples": toa_examples,
    }


def main():
    cw, rule_to_canon, claimed = load_crosswalk()
    manifest = json.loads((ROOT / "seeded" / REGISTER / "manifest.json").read_text(encoding="utf-8"))
    whitelist = json.loads((ROOT / "corpora" / REGISTER / "whitelist.json").read_text(encoding="utf-8"))
    draft_files = {f"{d['draft_id']}.md" for d in manifest["drafts"]}

    seeded_runs, human_runs = {}, {}
    for rf in sorted((ROOT / "results").glob("raw_*.json")):
        run = json.loads(rf.read_text(encoding="utf-8"))
        key = (run["tool"], run.get("run_n", 1))
        if set(run["files"]) & draft_files:
            seeded_runs.setdefault(run["tool"], []).append(run)
        else:
            human_runs.setdefault(run["tool"], []).append(run)

    out = {"register": REGISTER, "date": date.today().isoformat(),
           "crosswalk_version": cw["version"], "tools": {}}
    for tool in sorted(set(seeded_runs) | set(human_runs)):
        entry = {"sha": None, "runs": {}}
        recalls = []
        for run in seeded_runs.get(tool, []):
            entry["sha"] = run.get("sha")
            r = match_seeded(run, manifest, rule_to_canon)
            entry["runs"].setdefault("seeded", []).append(r)
            recalls.append(r["recall"])
        if recalls:
            entry["recall_mean"] = round(sum(recalls) / len(recalls), 4)
            entry["recall_min"] = round(min(recalls), 4)
            entry["recall_max"] = round(max(recalls), 4)
        for run in human_runs.get(tool, []):
            entry["sha"] = entry["sha"] or run.get("sha")
            entry["runs"].setdefault("human", []).append(score_human(run, whitelist))
        out["tools"][tool] = entry

    stamp = out["date"]
    (ROOT / "results" / f"{REGISTER}_{stamp}.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    # markdown table
    lines = [
        f"# slopbench results: {REGISTER} ({stamp})",
        "",
        "slopbench measures rules, not writers. It never claims or implies AI",
        "authorship of any text. A flag on human text is not automatically wrong",
        "as style advice; the claim under test is that these rules remove AI",
        "tells, and rule fire density on verifiably pre-ChatGPT text is evidence",
        "of style preference rather than AI signal. Readers judge the rows.",
        "",
        "| tool | sha | recall (mean) | recall (min-max) | flags/1k human | ToA violations/1k |",
        "|---|---|---|---|---|---|",
    ]
    for tool, e in out["tools"].items():
        sha = (e["sha"] or "")[:8]
        rec = f"{e['recall_mean']:.1%}" if e.get("recall_mean") is not None else "n/a"
        rng = (f"{e['recall_min']:.1%}-{e['recall_max']:.1%}"
               if e.get("recall_min") is not None else "n/a")
        h = e["runs"].get("human", [{}])
        f1k = h[0].get("flags_per_1k", "n/a")
        toa = h[0].get("toa_per_1k", "n/a")
        lines.append(f"| {tool} | {sha} | {rec} | {rng} | {f1k} | {toa} |")
    lines.append("")
    # per-tier recall
    for tool, e in out["tools"].items():
        seeded = e["runs"].get("seeded")
        if not seeded:
            continue
        lines += [f"## {tool}: recall by tier", "", "| tier | matched/planted | recall |", "|---|---|---|"]
        for tier, v in seeded[0]["per_tier"].items():
            lines.append(f"| {tier} | {v['matched']}/{v['planted']} | {v['matched'] / v['planted']:.1%} |")
        lines.append("")
    (ROOT / "results" / f"{REGISTER}_{stamp}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"scored {len(out['tools'])} tools -> results/{REGISTER}_{stamp}.md")
    for tool, e in out["tools"].items():
        print(f"  {tool}: recall={e.get('recall_mean')}, "
              f"human runs={len(e['runs'].get('human', []))}, seeded runs={len(e['runs'].get('seeded', []))}")


if __name__ == "__main__":
    main()
