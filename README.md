# RegisterBench

The first independent, cross-tool, register-split benchmark of anti-AI-slop rulesets. Working name; final name pending.

Every published number in this niche is self-graded: each tool's own rules run on each tool's own fixtures. RegisterBench publishes what no tool has: (a) cross-tool comparison under one protocol, (b) flag behavior on verifiably human pre-ChatGPT text, and (c) register-level splits.

## What RegisterBench does not do

RegisterBench measures rules, not writers. It never claims or implies AI authorship of any text, anywhere. The human corpora predate November 2022, so no flag on them can be an AI catch. A flag on human text is not automatically wrong as style advice either. The claim these tools make is removing AI tells. A rule that fires densely on a 2001 email or a 2019 10-K encodes a style preference, not an AI signal. We report both metrics and let readers judge.

## Tools under test

| tool | track | pinned SHA |
|---|---|---|
| [stop-slop](https://github.com/hardikpandya/stop-slop) | prompt | 8da1f030 |
| [no-ai-slop](https://github.com/petergyang/no-ai-slop) | prompt | 61c21c35 |
| [the-antislop](https://github.com/aplaceforallmystuff/the-antislop) | prompt | 5edbf856 |
| [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) SKILL.md | prompt | 27156c7a |
| [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) detector engine | code | 27156c7a |
| [unslop](https://github.com/MohamedAbdallah-14/unslop) deterministic layer | code | 5af59d9f |

## Headline results: finance-audit register (partial, code track only)

Dated 2026-07-24. Prompt-track runs pending. Full tables in `results/`.

| tool | recall (122 seeded instances) | flags/1k words, human corpus | term-of-art violations/1k |
|---|---|---|---|
| avoid-ai-writing detector | 46.7% | 0.51 | 0.081 |
| unslop deterministic | 28.7% | 2.06 | 0.189 |

The human corpus is 111k words of pre-November-2022 SEC filing prose (10-K MD&A sections and audit opinions, 2019-2021). Both engines flag defined regulatory terms of art on real filings: "comprehensive" fires on "statements of comprehensive income" (a GAAP-mandated statement name), and density rules collide with "significant deficiency" (a defined PCAOB term). The whitelist in `corpora/finance-audit/whitelist.json` cites the standard behind each protected term.

## Two measurement axes

**Recall on seeded drafts.** Base drafts are lightly adapted from real pre-2022 SEC filing text (never LLM-generated, source filing cited per draft). Slop patterns from a canonical 29-pattern taxonomy are planted manually and recorded in `seeded/{register}/manifest.json` at write time: draft id, pattern id, exact span, tier, and whether the instance was inserted or retained from the base text. Recall = planted instances flagged / planted instances, reported per tool, per tier, per pattern.

**Flag behavior on human text.** Two metrics on pre-November-2022 corpora: flags per 1,000 words (rule fire density) and term-of-art violation rate (flags landing inside a per-register whitelist of defined terms, each with a regulatory citation).

## Execution protocol

**Code track (deterministic).** avoid-ai-writing's `analyzeText` API and unslop's `humanize_deterministic_with_report` (intensity full, structural and soul passes off, which makes runs voice-neutral by construction). Commit SHAs pinned in every result file.

**Prompt track (stochastic).** Each tool's skill files verbatim as system prompt, one uniform detect-only instruction appended, fixed model `claude-sonnet-5`, N=3 runs per draft, mean/min/max reported. Model string and date recorded in every result file.

**Flag matching.** `crosswalk/patterns.json` maps each tool's rule names to canonical pattern IDs and records which patterns each tool claims at all, so recall tables can distinguish "missed" from "out of scope". Flags match planted spans by character overlap (threshold 0.5) or quoted-text containment. Unmatched flags are logged and feed the false-positive analysis.

## Reproduction

```
git clone <the five tool repos> ../tools/   # SHAs in crosswalk/patterns.json
py scripts/fetch_finance_corpus.py          # EDGAR download, writes PROVENANCE.md
py scripts/clean_corpus.py                  # prose filter for scoring
py scripts/verify_manifest.py               # manifest integrity check
node runners/code_track/run_avoid_ai_writing.js results/raw_aaw_seeded.json seeded/finance-audit
py runners/code_track/run_unslop.py results/raw_unslop_seeded.json seeded/finance-audit
py scripts/score.py finance-audit
```

Node 18+ and Python 3.10+ are the only requirements. No package installs needed for the code track.

## Registers

finance-audit (this release), casual-email, social, technical-docs (planned). Finance-audit ships first because it is where false positives are most defensible to demonstrate: the collisions land on defined terms with regulatory citations.

## License

MIT. See `LICENSE`.
