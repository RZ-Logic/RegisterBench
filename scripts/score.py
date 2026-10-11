"""Score RegisterBench runner outputs: recall, flags/1k, ToA violations, variance.

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


def index_valid(text, f):
    """Trust a reported character offset only if the flagged text is actually
    there. Engines can report offsets into a normalized copy of the input, and
    chunked runs shift offsets, so an unverified index can point at the wrong
    words. A mismatched index falls back to locating the text by search."""
    i = f.get("index")
    t = f.get("text") or ""
    return isinstance(i, int) and t != "" and text[i:i + len(t)] == t


def locate(text, ftext):
    """Occurrences of a flagged quote. Case-sensitive first, because engines and
    models preserve the case of what they flagged ('Leverage' the heading is not
    'leverage' inside 'managed leverage'); case-insensitive only as a fallback."""
    occ = find_all(text, ftext)
    if not occ:
        occ = [(m.start(), m.end()) for m in re.finditer(re.escape(ftext), text, re.I)]
    return occ


def plant_range(text: str, span: str, occurrence: int):
    spans = find_all(text, span)
    return spans[occurrence - 1] if len(spans) >= occurrence else None


def boundary_spans(lower: str, term: str):
    """Whole-phrase occurrences of term, respecting word boundaries.

    Implements the rule whitelist.json documents. Plain substring search would
    let "qualified opinion" match inside "unqualified opinion", which is the
    opposite meaning.
    """
    pat = r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)"
    return [(m.start(), m.end()) for m in re.finditer(pat, lower)]


def max_bipartite_matching(edges, n_right):
    """Kuhn's algorithm. edges[i] = iterable of right-node indices for left i.

    Returns dict left_index -> right_index. Used so each quoted finding is
    credited to at most one plant, while still giving every tool the best
    assignment available to it (a greedy scan would instead make recall depend
    on the order plants happen to appear in the manifest).
    """
    match_right = {}

    def try_assign(left, seen):
        for r in edges[left]:
            if r in seen:
                continue
            seen.add(r)
            if r not in match_right or try_assign(match_right[r], seen):
                match_right[r] = left
                return True
        return False

    for left in range(len(edges)):
        try_assign(left, set())
    return {v: k for k, v in match_right.items()}


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
            elif index_valid(text, f):
                resolved.append((f, [(f["index"], f["index"] + len(ftext))]))
            else:
                occ = find_all(text, ftext)
                if not occ:
                    # try case-insensitive locate
                    occ = [(m2.start(), m2.end()) for m2 in
                           re.finditer(re.escape(ftext), text, re.I)]
                resolved.append((f, occ))
        # Two-stage assignment. Document-level rules describe a whole document
        # ("you overuse em dashes"), so one such flag legitimately covers every
        # plant of its canonical pattern and is never consumed. Quoted spans are
        # located evidence and are consumed once each: without that, a single
        # paragraph-long quote scores 1.0 against every short plant inside it
        # (overlap_ratio divides by the smaller span), so a tool that quotes
        # whole paragraphs would score as if it had located each plant.
        doc_level = [(k, f) for k, (f, r) in enumerate(resolved) if r is None]
        span_level = [(k, f, r) for k, (f, r) in enumerate(resolved) if r is not None]

        plants = draft["plants"]
        for plant in plants:
            per_pattern.setdefault(plant["pattern_id"], [0, 0])[1] += 1
            per_tier.setdefault(plant["tier"], [0, 0])[1] += 1
        plants_total += len(plants)

        ranges_by_plant = [
            plant_range(text, p["span"], p.get("occurrence", 1)) for p in plants
        ]

        hit = [False] * len(plants)
        used = [False] * len(resolved)

        # Stage 1: document-level credit, unlimited reuse.
        for i, plant in enumerate(plants):
            if ranges_by_plant[i] is None:
                continue
            for k, f in doc_level:
                if plant["pattern_id"] in canon_ids(tool, f["rule"], rule_to_canon):
                    hit[i] = True
                    used[k] = True
                    break

        # Stage 2: quoted spans, one finding to at most one plant. Running this
        # only on plants stage 1 missed is what keeps the assignment optimal.
        pending = [i for i in range(len(plants)) if not hit[i] and ranges_by_plant[i]]
        edges = []
        for i in pending:
            prange = ranges_by_plant[i]
            edges.append([
                j for j, (_, _, ranges) in enumerate(span_level)
                if any(overlap_ratio(prange, r) >= 0.5 for r in ranges)
            ])
        assignment = max_bipartite_matching(edges, len(span_level))
        for left, right in assignment.items():
            hit[pending[left]] = True
            used[span_level[right][0]] = True

        for i, plant in enumerate(plants):
            if hit[i]:
                matched_total += 1
                per_pattern[plant["pattern_id"]][0] += 1
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


def term_coverage(span, term_spans):
    """Share of a flagged span made up of protected-term text (union of terms)."""
    s, e = span
    if e <= s:
        return 0.0
    ivs = sorted((max(s, a), min(e, b)) for a, b in term_spans if min(e, b) > max(s, a))
    covered, cur_s, cur_e = 0, None, None
    for a, b in ivs:
        if cur_e is None or a > cur_e:
            if cur_e is not None:
                covered += cur_e - cur_s
            cur_s, cur_e = a, b
        else:
            cur_e = max(cur_e, b)
    if cur_e is not None:
        covered += cur_e - cur_s
    return covered / (e - s)


def contains_term(span, term_spans):
    """Containment rule: the flag overlaps a protected term at >=0.5 of the
    shorter span, so any flag that encloses a term qualifies however wide."""
    return any(overlap_ratio(span, ts) >= 0.5 for ts in term_spans)


def anchored_on_term(span, term_spans):
    """Flag-anchored rule: protected-term text is at least half of what was
    flagged. A 700-character quote that happens to enclose 'reasonable
    assurance' was flagged for something else and does not qualify; a flag on
    'fairly' inside 'present fairly' does. This is the human-corpus analogue of
    the one-finding-one-plant fix on the recall side: without it, the metric
    rewards narrow quoting and punishes wide quoting regardless of what the
    rule actually targeted."""
    return term_coverage(span, term_spans) >= 0.5


def doc_type(fname):
    return "opinion" if "opinion" in fname else "mdna"


def whitelist_terms(whitelist):
    """(surface form, canonical term) pairs for every term and variant."""
    out = []
    for t in whitelist["terms"]:
        for form in [t["term"]] + t.get("variants", []):
            out.append((form, t["term"]))
    return out


def merged(spans):
    """Merge overlapping spans, so a variant nested inside another variant
    ('comprehensive income' inside 'other comprehensive income') is one
    occurrence, not two."""
    out = []
    for a, b in sorted(spans):
        if out and a < out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def whitelist_stats(whitelist):
    """Corpus-level protected-phrase occurrence counts, with nested variants
    merged so no character range is counted twice."""
    terms = whitelist_terms(whitelist)
    total, by_type, by_term = 0, {}, {}
    for p in sorted((ROOT / "corpora" / REGISTER / "clean").glob("*.txt")):
        lower = p.read_text(encoding="utf-8").lower()
        dt = doc_type(p.name)
        per_canon = {}
        for form, canon in terms:
            per_canon.setdefault(canon, []).extend(boundary_spans(lower, form))
        all_spans = merged([s for v in per_canon.values() for s in v])
        total += len(all_spans)
        by_type[dt] = by_type.get(dt, 0) + len(all_spans)
        for canon, spans in per_canon.items():
            n = len(merged(spans))
            if n:
                by_term[canon] = by_term.get(canon, 0) + n
    return {"occurrences": total, "by_doc_type": by_type,
            "by_term": dict(sorted(by_term.items(), key=lambda kv: -kv[1]))}


def score_human(run, whitelist):
    terms = whitelist_terms(whitelist)
    total_words = 0
    total_flags = 0
    hits = {"anchored": 0, "containment": 0}
    by_type = {}
    by_term = {}
    doc_term_pairs = set()
    toa_examples = []
    containment_only_examples = []
    corpus_dir = ROOT / "corpora" / REGISTER / "clean"
    for fname, data in run["files"].items():
        total_words += data["words"]
        total_flags += len(data["findings"])
        dt = by_type.setdefault(doc_type(fname), {"words": 0, "toa": 0, "toa_containment": 0})
        dt["words"] += data["words"]
        path = corpus_dir / fname
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        labelled = []  # (start, end, canonical term)
        for t, canon in terms:
            labelled += [(a, b, canon) for a, b in boundary_spans(lower, t)]
        term_spans = [(a, b) for a, b, _ in labelled]

        def main_term(span):
            """Canonical whitelist term a flag is attributed to, for the per-term
            and (document, term) counts. If the flag fully encloses one or more
            terms, the shortest enclosed term wins: it is the most specific, and
            for a word-ban rule the banned word sits inside it ('fairly' inside
            'present fairly', not 'in all material respects'). Otherwise the term
            with the largest overlap wins."""
            enclosed = [(b - a, canon) for a, b, canon in labelled
                        if span[0] <= a and b <= span[1]]
            if enclosed:
                return min(enclosed)[1]
            best, best_len = None, 0
            for a, b, canon in labelled:
                ov = min(span[1], b) - max(span[0], a)
                if ov > best_len:
                    best, best_len = canon, ov
            return best

        def record(f, ftext, span, anchored, contained):
            contained = contained or anchored  # containment is the superset rule
            if contained:
                hits["containment"] += 1
                dt["toa_containment"] += 1
            if anchored:
                hits["anchored"] += 1
                dt["toa"] += 1
                canon = main_term(span)
                by_term[canon] = by_term.get(canon, 0) + 1
                doc_term_pairs.add((fname, canon))
                if len(toa_examples) < 25:
                    toa_examples.append({"file": fname, "rule": f["rule"], "text": ftext})
            elif contained and len(containment_only_examples) < 25:
                containment_only_examples.append(
                    {"file": fname, "rule": f["rule"], "text": ftext, "chars": len(ftext)})

        # Flags carrying a verified character index are tested at that exact
        # position. Index-less flags (the prompt track emits quotes, not
        # offsets) are grouped by their exact text: crediting each one against
        # every occurrence would count all N flags as violations whenever any
        # single occurrence happens to sit inside a protected term.
        indexless = {}
        for f in data["findings"]:
            ftext = f["text"] or ""
            if f.get("rule") in DOC_LEVEL_RULES or not ftext:
                continue
            if index_valid(text, f):
                span = (f["index"], f["index"] + len(ftext))
                record(f, ftext, span, anchored_on_term(span, term_spans),
                       contains_term(span, term_spans))
            else:
                indexless.setdefault(ftext, []).append(f)

        for ftext, flags in indexless.items():
            occurrences = locate(text, ftext)
            anch = [r for r in occurrences if anchored_on_term(r, term_spans)]
            cont = [r for r in occurrences if contains_term(r, term_spans) or anchored_on_term(r, term_spans)]
            cred_anch = min(len(flags), len(anch))
            cred_cont = min(len(flags), len(cont))
            for i, f in enumerate(flags[:max(cred_anch, cred_cont)]):
                span = anch[i] if i < cred_anch else cont[i]
                record(f, f["text"], span, i < cred_anch, i < cred_cont)

    def per_1k(n, w):
        return round(n / w * 1000, 3) if w else None

    return {
        "words": total_words,
        "flags": total_flags,
        "flags_per_1k": round(total_flags / total_words * 1000, 2) if total_words else None,
        "toa_rule": "flag-anchored: protected terms cover >=50% of the flagged span",
        "toa_violations": hits["anchored"],
        "toa_per_1k": per_1k(hits["anchored"], total_words),
        "toa_containment": hits["containment"],
        "toa_containment_per_1k": per_1k(hits["containment"], total_words),
        # Granularity-neutral count: distinct (document, protected term) pairs
        # the tool flagged. Engines differ in reporting: one emits a flag per
        # occurrence, another dedupes per document, so per-flag rates partly
        # measure reporting style. This count does not.
        "toa_doc_term_pairs": len(doc_term_pairs),
        "toa_by_term": dict(sorted(by_term.items(), key=lambda kv: -kv[1])),
        "toa_doc_term_pairs_by_term": {
            t: sum(1 for _, c in doc_term_pairs if c == t)
            for t in sorted({c for _, c in doc_term_pairs})
        },
        "by_doc_type": {
            k: {"words": v["words"], "toa": v["toa"],
                "toa_per_1k": per_1k(v["toa"], v["words"]),
                "toa_containment": v["toa_containment"]}
            for k, v in sorted(by_type.items())
        },
        "toa_examples": toa_examples,
        "containment_only_examples": containment_only_examples,
    }


def aggregate_breakdown(per_run):
    """Mean matched (with min and max) per key across N runs.

    planted is identical in every run because it comes from the manifest, so
    only matched varies. Deterministic tools have one run and no spread.
    """
    keys = sorted({k for d in per_run for k in d})
    out = {}
    for k in keys:
        matched = [d[k]["matched"] for d in per_run if k in d]
        planted = max(d[k]["planted"] for d in per_run if k in d)
        mean = sum(matched) / len(matched)
        out[k] = {
            "matched_mean": round(mean, 2),
            "matched_mean_exact": mean,  # unrounded, so derived weightings reconcile with the headline
            "matched_min": min(matched),
            "matched_max": max(matched),
            "planted": planted,
            "recall": round(mean / planted, 6) if planted else None,
        }
    return out


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
            entry["n_runs"] = len(recalls)
            # Aggregate the tier and pattern breakdowns across every run, so
            # they reconcile with the headline mean. Publishing run 1 alone
            # would put a single-run breakdown under an N-run headline.
            entry["per_tier"] = aggregate_breakdown(
                [r["per_tier"] for r in entry["runs"]["seeded"]])
            entry["per_pattern"] = aggregate_breakdown(
                [r["per_pattern"] for r in entry["runs"]["seeded"]])
            # Claimed-patterns-only recall: the same per-run matches, restricted
            # to plants whose canonical pattern this tool's crosswalk row says
            # it claims. Full-taxonomy recall measures coverage of the canonical
            # taxonomy; this measures accuracy on what the tool attempts.
            ids = claimed.get(tool, set())
            per_run = []
            plants_claimed = 0
            for r in entry["runs"]["seeded"]:
                pp = r["per_pattern"]
                num = sum(pp[p]["matched"] for p in ids if p in pp)
                den = sum(pp[p]["planted"] for p in ids if p in pp)
                plants_claimed = den
                per_run.append(num / den if den else None)
            vals = [v for v in per_run if v is not None]
            if vals:
                entry["claimed_only"] = {
                    "patterns_claimed": len(ids),
                    "plants_claimed": plants_claimed,
                    "recall_mean": round(sum(vals) / len(vals), 4),
                    "recall_min": round(min(vals), 4),
                    "recall_max": round(max(vals), 4),
                }
        for run in human_runs.get(tool, []):
            entry["sha"] = entry["sha"] or run.get("sha")
            entry["runs"].setdefault("human", []).append(score_human(run, whitelist))
        out["tools"][tool] = entry

    # Weighting sensitivity. The canonical taxonomy's tier sizes mirror how the
    # drafts were written, and the same person authored drafts, taxonomy and
    # scorer. Reporting recall under alternative tier weightings shows which
    # conclusions are weighting-invariant and which are artifacts of composition.
    LEX = ("lex-1", "lex-2", "lex-3")
    JUDGMENT = ("phrasal", "structural")

    def pooled(pt, tiers):
        m = sum(pt[t]["matched_mean_exact"] for t in tiers if t in pt)
        n = sum(pt[t]["planted"] for t in tiers if t in pt)
        return m / n if n else None

    weightings = {
        "plant-weighted (published)": lambda pt: pooled(pt, list(pt)),
        "equal weight per tier": lambda pt: sum(
            v["matched_mean_exact"] / v["planted"] for v in pt.values()) / len(pt),
        "lexical tiers only": lambda pt: pooled(pt, LEX),
        "phrasal + structural only": lambda pt: pooled(pt, JUDGMENT),
    }
    sens = {}
    for name, fn in weightings.items():
        vals = {t: round(fn(e["per_tier"]), 4) for t, e in out["tools"].items() if e.get("per_tier")}
        ranking = sorted(vals, key=lambda t: -vals[t])
        gap = None
        if "avoid-ai-writing-skill" in vals and "avoid-ai-writing-detector" in vals:
            gap = round((vals["avoid-ai-writing-skill"] - vals["avoid-ai-writing-detector"]) * 100, 1)
        sens[name] = {"recall": vals, "ranking": ranking, "skill_minus_detector_points": gap}
    out["weighting_sensitivity"] = sens
    out["whitelist_stats"] = whitelist_stats(whitelist)

    stamp = out["date"]
    (ROOT / "results" / f"{REGISTER}_{stamp}.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    # markdown table
    lines = [
        f"# RegisterBench results: {REGISTER} ({stamp})",
        "",
        "RegisterBench measures rules, not writers. It never claims or implies AI",
        "authorship of any text. A flag on human text is not automatically wrong",
        "as style advice; the claim under test is that these rules remove AI",
        "tells, and rule fire density on verifiably pre-ChatGPT text is evidence",
        "of style preference rather than AI signal. Readers judge the rows.",
        "",
        "Recall assigns each quoted finding to at most one planted instance",
        "(maximum bipartite matching). Document-level rules are exempt, because",
        "one such flag legitimately covers every plant of its pattern. Tier and",
        "pattern breakdowns are means across all runs, matching the headline.",
        "",
        "| tool | sha | runs | recall (mean) | recall (min-max) | flags/1k human | ToA violations/1k |",
        "|---|---|---|---|---|---|---|",
    ]
    for tool, e in out["tools"].items():
        sha = (e["sha"] or "")[:8]
        rec = f"{e['recall_mean']:.1%}" if e.get("recall_mean") is not None else "n/a"
        n = e.get("n_runs", 0)
        rng = ("deterministic" if n == 1 else
               f"{e['recall_min']:.1%}-{e['recall_max']:.1%}"
               if e.get("recall_min") is not None else "n/a")
        h = e["runs"].get("human", [{}])
        f1k = h[0].get("flags_per_1k", "n/a")
        toa = h[0].get("toa_per_1k", "n/a")
        lines.append(f"| {tool} | {sha} | {n or 'n/a'} | {rec} | {rng} | {f1k} | {toa} |")
    lines.append("")

    lines += [
        "## Recall on claimed patterns only", "",
        "Same matches, restricted to plants whose canonical pattern the tool's",
        "crosswalk row claims. Full-taxonomy recall measures coverage of the",
        "canonical taxonomy; this measures accuracy on what each tool attempts.", "",
        "| tool | patterns claimed | plants claimed | full-taxonomy recall | claimed-only recall | claimed-only min-max |",
        "|---|---|---|---|---|---|",
    ]
    for tool, e in out["tools"].items():
        c = e.get("claimed_only")
        if not c:
            continue
        rng = ("deterministic" if e.get("n_runs") == 1 else
               f"{c['recall_min']:.1%}-{c['recall_max']:.1%}")
        lines.append(f"| {tool} | {c['patterns_claimed']}/29 | {c['plants_claimed']}/122 | "
                     f"{e['recall_mean']:.1%} | {c['recall_mean']:.1%} | {rng} |")
    lines.append("")

    sens = out["weighting_sensitivity"]
    names = list(sens)
    lines += [
        "## Weighting sensitivity", "",
        "Recall recomputed from the per-tier means under alternative tier",
        "weightings. Tier sizes mirror how the drafts were written, so a",
        "conclusion is only robust if it survives every column.", "",
        "| tool | " + " | ".join(names) + " |",
        "|---|" + "---|" * len(names),
    ]
    for tool in out["tools"]:
        if tool not in sens[names[0]]["recall"]:
            continue
        lines.append(f"| {tool} | " + " | ".join(
            f"{sens[n]['recall'][tool]:.1%}" for n in names) + " |")
    lines.append("| **skill minus detector (points)** | " + " | ".join(
        f"**{sens[n]['skill_minus_detector_points']}**" for n in names) + " |")
    lines.append("")

    lines += [
        "## Term-of-art violations under two matching rules", "",
        "Headline rule is flag-anchored: protected-term text must be at least half",
        "of the flagged span. Containment counts any flag that encloses a term,",
        "however wide the quote, which penalises tools that quote whole clauses.",
        "Rates are per 1,000 words; the by-type columns use that type's words.", "",
        "| tool | anchored /1k | containment /1k | anchored, opinions /1k | anchored, MD&A /1k | distinct (document, term) pairs |",
        "|---|---|---|---|---|---|",
    ]
    for tool, e in out["tools"].items():
        h = e["runs"].get("human")
        if not h:
            continue
        h = h[0]
        bt = h.get("by_doc_type", {})
        lines.append(
            f"| {tool} | {h['toa_per_1k']} | {h['toa_containment_per_1k']} | "
            f"{bt.get('opinion', {}).get('toa_per_1k', 'n/a')} | "
            f"{bt.get('mdna', {}).get('toa_per_1k', 'n/a')} | {h['toa_doc_term_pairs']} |")
    lines.append("")

    # per-tier recall, aggregated across runs
    for tool, e in out["tools"].items():
        if not e.get("per_tier"):
            continue
        n = e.get("n_runs", 1)
        basis = "single deterministic run" if n == 1 else f"mean of {n} runs"
        lines += [f"## {tool}: recall by tier ({basis})", "",
                  "| tier | matched/planted | recall | matched min-max |", "|---|---|---|---|"]
        for tier, v in e["per_tier"].items():
            spread = ("n/a" if n == 1 else
                      f"{v['matched_min']}-{v['matched_max']}")
            lines.append(
                f"| {tier} | {v['matched_mean']:g}/{v['planted']} "
                f"| {v['recall']:.1%} | {spread} |")
        lines.append("")
    (ROOT / "results" / f"{REGISTER}_{stamp}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"scored {len(out['tools'])} tools -> results/{REGISTER}_{stamp}.md")
    for tool, e in out["tools"].items():
        print(f"  {tool}: recall={e.get('recall_mean')}, "
              f"human runs={len(e['runs'].get('human', []))}, seeded runs={len(e['runs'].get('seeded', []))}")


if __name__ == "__main__":
    main()
