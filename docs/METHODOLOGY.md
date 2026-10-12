# RegisterBench methodology

How the benchmark is built, scored and run, in full. The [README](../README.md) carries the summary; [FINDINGS.md](FINDINGS.md) carries the detailed results. [`NOTES.md`](../NOTES.md) is the working history.

## The Measurement Principle

> **A tool's own fixtures share its author's blind spots. Recall on planted ground truth and flag behavior on verifiably human text are two different questions, and a benchmark has to answer both.**

Recall alone rewards a ruleset for firing constantly. Flag density alone rewards a ruleset for firing never. Reported together, on ground truth that was planted by hand before any tool ran, they describe a tool honestly. Neither number is a verdict on its own.

**On what a flag on human text means.** The human corpora predate November 2022, so no flag on them can be an AI catch. That does not automatically make a flag *wrong* as style advice. The claim these tools make is removing AI tells. A rule that fires densely on a 2020 10-K is demonstrating that it encodes a style preference, not an AI signal. Both metrics are reported and readers judge the rows.

**RegisterBench never claims or implies AI authorship of any text, anywhere.** It has no authorship-detection component, produces no "AI risk" score, and takes no position on who or what wrote any document it processes. It measures rules against a manifest.

**The audit trail for the ground truth:** every one of the 122 planted instances was recorded in [`seeded/finance-audit/manifest.json`](../seeded/finance-audit/manifest.json) at the moment it was written into a draft, with its exact span, canonical pattern ID, tier, and whether it was inserted or retained from the source filing. [`scripts/verify_manifest.py`](../scripts/verify_manifest.py) re-locates every span in every draft and fails loudly on drift. No plant was reconstructed after the fact, and no scoring run can silently move the target.

## Where is the Judgment?

This is the architectural through-line, adapted from the *"Where is the AI?"* enumeration in [FinAgent OS](https://github.com/RZ-Logic/finagent-os). Every automated stage of the benchmark is deterministic except prompt-track detection, which is bounded at N=3 with mean, min, and max reported. Two stages are human judgments rather than computation; they are recorded at the time they were made so they can be audited, which is not the same as being deterministic.

| # | Stage | Deterministic? | What it does |
|---|---|:-:|---|
| 1 | **Corpus acquisition** | ✅ | EDGAR submissions API by CIK, filing-date window, Item 7 and audit-opinion section slicing. Accession numbers and retrieval date written to [`PROVENANCE.md`](../corpora/finance-audit/PROVENANCE.md) per file. |
| 2 | **Prose filtering** | ✅ | Line-level filter dropping numeric-majority and heading-fragment lines from flattened filing tables. `raw/` is preserved untouched as the provenance record. |
| 3 | **Seeding** | 📝 *recorded judgment* | Patterns planted by hand into lightly adapted real filing text. Never model-generated, which would contaminate the ground truth. |
| 4 | **Manifest verification** | ✅ | Every span re-located, word counts and plant counts range-checked, every pattern ID validated against the crosswalk. Exits nonzero on any drift. |
| 5 | **Crosswalk** | 📝 *recorded judgment, blind double-coded* | 29 canonical pattern IDs mapped to each tool's own rule identifiers, recording which patterns each tool claims at all. Coded independently by two coders per tool reading only that tool's source; 98.9% agreement, disagreements adjudicated. Per-cell evidence in [`coding_record.json`](../crosswalk/coding_record.json). |
| 6 | **Code-track detection** | ✅ | `avoid-ai-writing` `analyzeText()` and `unslop` `humanize_deterministic_with_report()`, both SHA-pinned. Byte-identical across runs. |
| **7** | **Prompt-track detection** | **❌ stochastic** | Each tool's ruleset files verbatim as the API `system` prompt, uniform detect-only instruction appended, model pinned to `claude-sonnet-5` with thinking and effort left at the model's defaults. **N=3 independent runs per document on both corpora** through the Message Batches API, mean/min/max reported, served model recorded in every result file. v0.1.0's prompt-track numbers came from a subagent path instead; v0.1.1 replaces them, and the difference turned out to be a finding (see [Limitations](#limitations)). |
| 8 | **Validation and matching** | ✅ | A response with any malformed finding is rejected rather than repaired. A quote that occurs nowhere in its document is reported and excluded. Located spans are matched to the manifest at 0.5 character overlap, or by quoted-text containment; document-level rules (density, rates, rhythm) match by crosswalked pattern. Unmatched flags are logged separately. |
| 9 | **Scoring** | ✅ | Recall overall, by tier, by pattern. Flags per 1,000 words. Term-of-art violation rate against the citation-backed whitelist. |

Six deterministic stages, two recorded judgments, and one stochastic stage, bounded and reported with its spread.

> **The principle:** A benchmark whose own pipeline is stochastic cannot distinguish a tool's variance from its own. Isolate the stochasticity to the single stage that genuinely requires it, pin the model, run it N times, and publish the spread so readers can see how much of any gap is noise.

## Components and tools under test

### Component overview

| Component | What it is | Role of the model |
|-----------|-----------|:-:|
| **Corpus** ([`corpora/finance-audit/`](../corpora/finance-audit/)) | 18 documents, 111,313 clean words. 10-K MD&A sections and audit opinions from 10 issuers, filed 2020-07-30 to 2021-03-24 (fiscal years ending 2020). Accession numbers and URLs per file. | None |
| **Term-of-art whitelist** ([`whitelist.json`](../corpora/finance-audit/whitelist.json)) | 14 defined terms, each with a PCAOB, FASB ASC, SEC or statutory citation (or, for `pervasive`, ISA 705 / AU-C 705) and a note on the collision it creates, plus a `deliberately_excluded` block recording register words that were considered and rejected. | None |
| **Seeded drafts** ([`seeded/finance-audit/`](../seeded/finance-audit/)) | 10 drafts, 330 to 397 words, 122 planted instances across a 29-pattern taxonomy spanning 6 tiers. Manual planting, recorded at write time. | None |
| **Crosswalk** ([`crosswalk/patterns.json`](../crosswalk/patterns.json)) | Canonical IDs mapped to all 6 tool faces, with claimed-versus-unclaimed recorded per pattern. | None |
| **Code-track runners** ([`runners/code_track/`](../runners/code_track/)) | Node and Python invocations, SHA-pinned, emitting a normalized findings schema. | None |
| **Prompt-track harness** ([`runners/prompt_track/`](../runners/prompt_track/)) | Anthropic API harness: Message Batches for the canonical run, a synchronous path for smoke tests. Ruleset files verbatim as system prompt, detect-only instruction appended, N=3, model-pinned. Gated behind `--approved` because it spends money. | Detection only |
| **Scorer** ([`scripts/score.py`](../scripts/score.py)) | Recall (overall, by tier, by pattern), flags per 1k, term-of-art rate, prompt-track variance. | None |

### Tools under test

Six faces across five repositories. `avoid-ai-writing` appears twice by design, because it ships both a prose ruleset and a regex engine, and the whole point is that those are different artifacts.

| Tool | Track | Pinned SHA | What it is |
|---|:-:|---|---|
| [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) SKILL.md | prompt | `27156c7a` | 3 vocabulary tiers, 6 context profiles, tolerance matrix |
| [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) detector | code | `27156c7a` | 45-category deterministic engine, zero dependencies |
| [stop-slop](https://github.com/hardikpandya/stop-slop) | prompt | `8da1f030` | SKILL.md plus 3 reference files, distribution leader |
| [no-ai-slop](https://github.com/petergyang/no-ai-slop) | prompt | `61c21c35` | 17 named patterns, first-class detect mode |
| [the-antislop](https://github.com/aplaceforallmystuff/the-antislop) | prompt | `5edbf856` | Wikipedia-derived tiers, additive point scoring |
| [unslop](https://github.com/MohamedAbdallah-14/unslop) deterministic layer | code | `5af59d9f` | 15 Python regex rule families, detect and rewrite |

## Reading the tables


**The metrics.** Three describe what a tool catches, two describe what it disturbs.

| Metric | What it measures | Higher is |
|---|---|:-:|
| **Recall (mean)** | Of the 122 pattern instances planted by hand into the seeded drafts, the share a tool flagged. Each quoted finding is credited to at most one plant (see [matching](#build-decisions--lessons-learned), decision 1). Averaged across 3 independent runs for prompt-track tools. | better |
| **Recall range** | Lowest and highest single-run recall across those 3 runs, so readers can see how much of any gap between tools is run-to-run noise. Deterministic engines produce one value and no spread. | narrower |
| **Claimed-only recall** | The same matches, restricted to plants whose canonical pattern the tool's crosswalk row says it claims. Full recall measures coverage of the whole taxonomy; this measures accuracy on what the tool attempts. A tool that claims little loses less here. | better |
| **Flags/1k human** | Total flags a tool raised per 1,000 words of the human corpus. Because that corpus predates November 2022, no flag on it can be an AI catch, so this is a measure of how readily a ruleset fires on ordinary filing prose. For prompt-track tools it is a mean across 3 runs, with the range beside it, and on this corpus it mostly records whether the model returned any findings at all (see [What the data shows](FINDINGS.md#what-the-data-shows)). Findings whose quote does not occur in the document are excluded and reported separately (see [FINDINGS.md](FINDINGS.md#quotes-that-do-not-occur-in-the-source-text)). | context |
| **Term-of-art violations/1k** | Flags on the human corpus whose flagged text is at least half protected regulatory phrasing from the [whitelist](../corpora/finance-audit/whitelist.json), per 1,000 words. These are phrases a filer is not free to rewrite, so a flag here is the least defensible kind. The half-coverage rule stops a wide quote that merely encloses a term, flagged for some other reason, from counting. Reported two ways: per flag, and as distinct (document, term) pairs, because engines differ in whether they report every occurrence or once per analyzed chunk. | lower |

Flags per 1k has no "good" direction on its own, which is the point of reporting it next to recall rather than instead of it. A tool that never fires scores well on it and badly on recall.

**The six tiers.** The 29-pattern canonical taxonomy is grouped by *what kind of thing* a pattern is, because that determines what sort of detection can find it. Tier sizes are uneven because they mirror how the planted drafts were written, not an attempt at balance.

| Tier | Plants | What it is | Examples from the drafts |
|---|:-:|---|---|
| **lex-1** | 23 | Single words or fixed short phrases flagged unconditionally, wherever they appear. | `seamless`, `daunting`, `cutting-edge`, `testament to`, `utilizes` |
| **lex-2** | 12 | Vocabulary flagged only when several co-occur in a passage, the cluster-gated tier. | `foster`, `cornerstone`, `harnessing`, `multifaceted`, `poised` |
| **lex-3** | 12 | Ordinary words flagged only above a repetition threshold, the density-gated tier. | `significant`, `innovative`, `effective`, `dynamic` |
| **phrasal** | 42 | Multi-word formulas with a recognisable shape rather than a fixed string. | "marking a pivotal moment", "experts believe", "Here's the thing:", "in order to" |
| **structural** | 29 | Sentence and paragraph shapes. No fixed string exists to match, so finding these requires reading form rather than tokens. | "The question isn't X. It's Y.", "Demand collapsed. Fleets parked.", em-dash rhythm, false agency |
| **conversational** | 4 | Chat-assistant residue left in a document that is not a chat. | "I hope this summary helps", "That's a great question", "As of my last update" |

Cells in the [recall-by-tier table](FINDINGS.md#recall-by-tier) are recall percentages; for prompt-track tools they are means across 3 runs. The tier split is the most diagnostic view in this repo: it is where the [executable-subset gap](FINDINGS.md#the-executable-subset-gap) becomes visible, because deterministic engines hold their own on the lexical tiers and collapse on the structural one.

## Stack

| Layer | Tool | Why |
|-------|------|-----|
| Corpus source | SEC EDGAR submissions API + Archives | Public domain, machine-addressable by CIK, filing dates are the provenance. No scraping of anything gated. |
| Corpus extraction | Python stdlib `html.parser` | 18 documents does not justify a dependency. Block-level tag handling is enough to recover paragraph structure from filing HTML. |
| Code-track invocation | Node 18+ (`require`), Python 3.10+ (direct import) | Each engine called through its own documented API rather than its CLI, which bypasses file-type gates and keeps the findings schema stable. |
| Prompt-track invocation | Anthropic Message Batches API (canonical run) and Messages API (smoke tests), stdlib `urllib` | Model pinned, and the model the API reports serving recorded in every result file. Batches run at half price with each ruleset's system prompt cached. The batch runner resumes after any interruption without resending a saved response, and refuses to submit unless the caller states the exact request count. No SDK dependency. |
| Scoring | Python stdlib | Span arithmetic and set membership. Nothing here needs pandas. |
| Result format | JSON per run, Markdown per register | Raw findings are diffable and re-scorable without re-running any tool. |

**No infrastructure novelty.** Everything here is stdlib, one HTTP API, and five cloned repositories. The contribution is the application layer: the seeded-manifest methodology, the citation-backed term-of-art whitelist, the crosswalk that lets six different taxonomies be compared under one protocol, and the decision to measure both faces of a two-faced tool.

## Reproduction

Node 18+ and Python 3.10+ are the only requirements. The code track needs no package installs, because both engines are dependency-free.

Commands below use `python3`. On Windows use the `py` launcher instead; every script is stdlib-only and otherwise platform-independent. All commands run from the repository root.

### Clone the tools at their pinned commits

SHAs are recorded in [`crosswalk/patterns.json`](../crosswalk/patterns.json) and in every result file. Clone into a sibling `tools/` directory, or set `REGISTERBENCH_TOOLS_DIR` to point elsewhere.

```bash
mkdir -p ../tools
git clone https://github.com/conorbronsdon/avoid-ai-writing ../tools/avoid-ai-writing && git -C ../tools/avoid-ai-writing checkout 27156c7a
git clone https://github.com/MohamedAbdallah-14/unslop        ../tools/unslop            && git -C ../tools/unslop            checkout 5af59d9f
git clone https://github.com/hardikpandya/stop-slop           ../tools/stop-slop         && git -C ../tools/stop-slop         checkout 8da1f030
git clone https://github.com/petergyang/no-ai-slop            ../tools/no-ai-slop        && git -C ../tools/no-ai-slop        checkout 61c21c35
git clone https://github.com/aplaceforallmystuff/the-antislop ../tools/the-antislop      && git -C ../tools/the-antislop      checkout 5edbf856
```

### Rebuild the corpus and verify the ground truth

The corpus ships in the repo, so this step is only needed to re-derive it from source. EDGAR requires a descriptive User-Agent, which the script sets.

```bash
python3 scripts/fetch_finance_corpus.py    # EDGAR download, writes PROVENANCE.md
python3 scripts/clean_corpus.py            # prose filter, writes clean/ from raw/
python3 scripts/verify_manifest.py         # re-locates all 122 spans, exits nonzero on drift
python3 -m unittest discover -s tests      # offline suite: mocked API, no key, no network
```

### Run the code track and score

```bash
node runners/code_track/run_avoid_ai_writing.js results/raw_aaw_seeded_finance.json seeded/finance-audit
node runners/code_track/run_avoid_ai_writing.js results/raw_aaw_human_finance.json  corpora/finance-audit/clean
python3 runners/code_track/run_unslop.py           results/raw_unslop_seeded_finance.json seeded/finance-audit
python3 runners/code_track/run_unslop.py           results/raw_unslop_human_finance.json  corpora/finance-audit/clean
python3 scripts/score.py finance-audit
```

`score.py` reads every `results/raw_*.json`, infers seeded-versus-human from the filenames it finds, and writes a dated Markdown table plus a full JSON detail file. It will score whatever raw files are present, so the code track reproduces standalone without the prompt track.

### Run the prompt track

This spends money against an Anthropic API key and is gated behind an explicit flag. The harness reads the key from `REGISTERBENCH_API_KEY`, set in the environment or in a gitignored `.env` at the repo root (template in [`.env.example`](../.env.example)). It deliberately ignores `ANTHROPIC_API_KEY`: other tools read that name, Claude Code among them, and a dedicated one keeps the benchmark key and its spend limit scoped to this harness.

```bash
cp .env.example .env
python3 runners/prompt_track/run_prompt_tool.py --approved --smoke avoid-ai-writing-skill seeded/finance-audit/fin-10.md
python3 runners/prompt_track/run_prompt_batch.py plan
python3 runners/prompt_track/run_prompt_batch.py submit --approved --expect 336
python3 runners/prompt_track/run_prompt_batch.py wait
python3 runners/prompt_track/run_prompt_batch.py assemble
python3 scripts/score.py finance-audit
```

`--smoke` makes one call on one file and prints the model actually served, the stop reason and token usage, without writing anything `score.py` reads.

[`run_prompt_batch.py`](../runners/prompt_track/run_prompt_batch.py) is the canonical path: all 336 requests (4 tools, 28 documents, 3 runs) through the Message Batches API. `submit` refuses unless `--expect` matches the number of requests it would send, and `--only` takes globs over request IDs such as `aawskill-human-F_2021_mdna-r1` for a partial run. `wait` polls and saves every response; `assemble` writes `results/raw_<short>_<set>_run<n>.json` (for example `raw_aawskill_seeded_run1.json`) and refuses if any billed response hit `max_tokens`, failed to parse, or came from a different ruleset, system prompt, model or `max_tokens` than the rest. An interrupted run resumes without resending anything already saved. Raw API responses are archived under `results/prompt_runs/`, which is gitignored. The synchronous harness, [`run_prompt_tool.py`](../runners/prompt_track/run_prompt_tool.py), is for smoke tests and short inputs, and refuses inputs over 5,000 words. Directory inputs skip `README.md`, `PROVENANCE.md` and `NOTES.md` on both paths, as the code-track runners do. The v0.1.1 run cost $7.04 at batch prices.

## Build Decisions & Lessons Learned

Ten non-obvious choices and the alternatives rejected.

### 1. Recall is span-based, not attribution-based, and each quoted finding is consumed once

A plant counts as recalled if *any* rule fires on its span, even when the tool names that rule something the crosswalk did not predict. The crosswalk is used for analysis, never for span-level recall credit.

The alternative was requiring the tool's rule name to map to the canonical pattern ID before granting credit. Rejected because these six tools disagree profoundly on taxonomy: what `stop-slop` calls "Binary Contrasts", `no-ai-slop` calls "Binary contrasts", `the-antislop` calls "Language 8: Negative parallelisms", and `avoid-ai-writing` calls "It's not X, it's Y structures". Requiring name agreement would have scored vocabulary alignment rather than detection ability, and would have quietly penalised whichever tool happened to name things least like my crosswalk.

**Span-based matching needs one guard, and v0.1 initially shipped without it.** Overlap is measured against the shorter of the two spans, so a plant fully contained in a longer quote scores a perfect match. Combined with unlimited reuse of a single finding, that made a paragraph-long quote count as having located every plant inside it. An adversarial review of this repo demonstrated the ceiling: a synthetic tool emitting one finding per draft containing the whole draft scored 122/122. Recall now assigns quoted findings to plants by maximum bipartite matching, so each finding is credited at most once. Maximum matching rather than a greedy scan, because greedy would make a tool's score depend on the order plants happen to appear in the manifest.

Document-level rules are deliberately exempt from consumption. A flag that says "you overuse em dashes" describes the whole document, so it legitimately covers every plant of its canonical pattern, and this is the one place crosswalk attribution does grant credit. Applying strict consumption there instead would have introduced an equal and opposite understatement. Correcting this moved published recall by 0.8 to 8.5 points depending on how verbose a tool's quoting style is, and it reordered two rows.

**The same confound existed on the human corpus and was fixed later than it should have been.** Term-of-art violations originally counted any flag that overlapped a protected term at half of the shorter span, so any quote enclosing a term counted, however wide. That is the identical `min()` denominator, applied in the opposite direction: it punished wide quoting instead of rewarding it. On v0.1.0's subagent-path data, `stop-slop`, whose passive-voice and list rules were the only rules in the cohort whose quotes enclosed protected opinion wording without targeting it, was credited with 27 violations and the worst rate in the cohort. Of the 19 the stricter rule removed, 17 were quotes flagged for something else that happened to contain a protected phrase. The rule now requires protected-term text to make up at least half of the flagged span, and both counts are published. The fix is not perfect: on that same data, two of `stop-slop`'s adverb flags on the opinion sentence quoted the whole clause and fell under the threshold (protected text 37% and 32% of the quote), so quote width still matters at the margin. In the canonical v0.1.1 run the question barely arises on the human corpus: no prompt-track flag targets protected text there, and the one `the-antislop` quote that encloses a protected term while flagging something else is correctly excluded (see [What the data shows](FINDINGS.md#what-the-data-shows)). The rule is built for data where the model returns more findings on the human corpus.

> **The principle:** Decide what your metric is allowed to be confounded by. A detection benchmark that punishes naming differences is partly a naming benchmark. One that rewards or punishes quote length is partly a verbosity benchmark. Neither is visible in the headline number, so both have to be designed out on purpose, and a guard added on one metric has to be checked for on every other metric that uses the same arithmetic.

### 2. Distractors live in the manifest as first-class entries

Terms of art retained from the real base text (`comprehensive income`, `reasonable assurance`, `critical audit matter`, `significant deficiency`) are recorded in the manifest as `distractors`, structurally separate from `plants`. They are never counted in recall. Flags landing on them are kept in the raw outputs for the false-positive analysis; v0.1.1 reads them by hand rather than scoring them, and automated distractor scoring is on the roadmap.

The simpler design was to keep the seeded set clean and measure false positives only on the human corpus. Rejected because the interesting collisions are register-specific, and a term-of-art collision inside a seeded draft is evidence that a tool cannot distinguish planted slop from mandated language *in the same document*. That is a sharper claim than the same collision found on a separate corpus. It paid off in v0.1.1: with `stop-slop` the model returned an empty list for every real audit opinion in all three runs, but it returned findings on the seeded drafts, and its adverb ban flagged *fairly* in a retained opinion sentence in fin-03 in two of three runs. The distractors caught a collision the human corpus did not show.

> **The principle:** Ground truth is not only what you planted. Recording what you deliberately left alone turns your test set into two experiments instead of one.

### 3. Both faces of `avoid-ai-writing` are measured, and it is the only tool treated this way

`avoid-ai-writing` occupies two rows because it ships two artifacts: a prose ruleset intended for a model to read, and a regex engine intended to run in CI. Measuring only one would have produced a materially misleading number in either direction.

This is the decision the headline finding depends on. Had I scored only the engine, `avoid-ai-writing` would rank fifth of six and the conclusion would have been "the most rigorous ruleset underperforms". Had I scored only the SKILL.md, it ranks first and the 28-point executable-subset gap stays invisible.

> **The principle:** Benchmark artifacts, not projects. A repository is not a unit of measurement; the thing that runs is.

### 4. The density tier reads 0/12 for two tools and the drafts were not changed to fix it

Density-gated words (`significant`, `innovative`, `effective`) are planted at roughly 3 occurrences per 350-word draft, near 0.9%. `avoid-ai-writing`'s engine gates that tier at 3% of word count with a floor of 3, which in a 350-word draft means 10 or more occurrences. It therefore correctly does not fire, and scores 0/12.

The temptation was to raise plant density until the gate opened. Rejected: the drafts are 300 to 600 words because that is the length the brief specifies and the length real filing excerpts run. A rule whose threshold cannot be reached at realistic document length within a realistic register is a finding about the threshold. `stop-slop` reaches 47.2% on the same tier, but incidentally: its catches come from sentence-level rules such as the adverb ban and false agency, not from any density logic. The prose face of `avoid-ai-writing` reaches 27.8%, partly because the model reading its Tier 3 rule sometimes treats three repeats of `significant` or `dynamic` as density, which the engine's 3% gate never will, and partly by the same incidental route. A model applying a threshold loosely is not density detection either. Nobody in this cohort is doing density detection well, and the row is honest about that rather than tuned to flatter it.

The same reasoning applies to `str-em-dash`, and it was not spotted until a completeness review of this repo. All four plants are paired dashes, giving exactly 2 em dashes per draft. `unslop` caps at 2 per paragraph and scores 0/4, because the plant density sits exactly at, not above, the threshold it documents. `the-antislop` ships an em-dash overuse rule too, and the model reading it fires that rule on 2.33 of 4 plants on average: sometimes it treats two dashes as overuse and sometimes it does not. Among the deterministic rules only the detector fires, and it does so with a document-level rate flag rather than a located span; the prose skill catches all four from quoted spans. This matters more than the `lex-3` case because it lands in the `structural` tier, which is the tier the executable-subset argument rests on.

> **The principle:** When ground truth and a tool's threshold disagree, check which one is unrealistic before changing either. Sometimes the finding is the threshold. Check this for every tier, not just the one where it is obvious.

### 5. Long documents are chunked, because a tool that refuses input is not a tool that found nothing

`avoid-ai-writing`'s engine caps input at 10,000 words (`MAX_WORDS`, `detector/patterns.js:718`) and returns `Text too long` with zero issues above it. Four MD&A documents in this corpus exceed that. v0.1.0 recorded those zeros as results while keeping all 66,128 of their words in the flags-per-1,000 denominator, so the engine was credited with perfect silence on 59% of a corpus it never read. Its published rate of 0.51 was really 1.09, and `unslop`, which has no such cap, read every one of those documents. The comparison was not like-for-like.

Inputs over the cap are now split at paragraph boundaries into sub-9,000-word chunks and analyzed in pieces, with offsets shifted back into document coordinates. Document-level rules report a rate rather than a located span, so they would otherwise fire once per chunk; they are deduplicated by rule and text across chunks of the same document. The runner exits nonzero if any chunk still trips the cap, so this cannot silently regress.

The honest cost of the fix is that document-level rules now see a 9,000-word window rather than the whole document, which slightly changes what "uniform paragraph length" or "low type-token ratio" means. Dropping the four documents instead would have been simpler and worse: the finance-specific language this register exists to test is concentrated in exactly those long MD&A sections.

> **The principle:** A tool declining to answer and a tool answering "nothing here" are different events, and a benchmark that conflates them rewards refusal. Check what your harness does with every non-answer a tool can return.

### 6. The human corpus is prose-filtered, and `raw/` is kept anyway

Filing HTML flattens financial tables into number-heavy lines. Left in, they inflate the denominator of flags per 1,000 words and make every tool look more precise than it is. [`scripts/clean_corpus.py`](../scripts/clean_corpus.py) drops numeric-majority and short heading-fragment lines. All scoring runs against `clean/`.

`raw/` ships alongside it, untouched, because the filter is a judgment call and a reader who disagrees with it needs to be able to re-derive the numbers under a different one.

> **The principle:** Any preprocessing step that moves a headline metric has to ship with its own input. A cleaned corpus without its raw counterpart is an unfalsifiable number.

### 7. `unslop` runs with its structural and soul passes disabled

`unslop`'s deterministic layer at `intensity=full` covers the widest rule set, but two of its passes (`structural`, `soul`) split long sentences and insert contractions. Those are rewrites, not detections. Counting them as flags would have credited it for finding slop when it was reformatting prose.

Its voice-profile machinery needed no special handling: the deterministic path ignores voice parameters entirely, so the runs are voice-neutral by construction rather than by configuration. Verified in source before relying on it.

> **The principle:** When a tool blends detection and rewriting, the benchmark has to draw the line the tool does not. Read the source to find out where the line actually is rather than trusting the flag name.

### 8. The crosswalk was re-coded blind, because the person who wrote the drafts also wrote the map

The crosswalk decides which patterns each tool "claims", and claimed-only recall inherits every decision in it. v0.1.0's crosswalk was hand-authored by the same person who wrote the seeded drafts and the scorer, which is exactly the setup in which a benchmark quietly favours its expectations. A completeness review found five mappings wrong against the tools' own source, three of them under-crediting `avoid-ai-writing` on rules its SKILL.md states explicitly.

Patching those five would have fixed the known errors and left the method unchanged. Instead every cell was re-coded from scratch. For each of the six tool faces, two coders read only that tool's source, never the existing crosswalk, under one written claim standard applied identically to every tool. One worked pattern-first, the other rule-first, so they could not share a blind spot through a shared reading order. They agreed on 172 of 174 cells (98.9%); the two disagreements were adjudicated against source. A later review flagged three cells as applying the standard inconsistently between tools, and each went to a fresh 3-adjudicator vote: two decisions were upheld, and one cell both coders had agreed on (the-antislop crediting a hidden-truth header rule as novelty inflation) was overturned 0 votes to 3, so the same reading now applies to the-antislop and stop-slop. The final map differs from the hand-authored version in 15 claim decisions, in both directions and across five of the six tools, which is the signature of noise in a hand-built map rather than of a thumb on the scale. Every cell's evidence, with file, line and quote, is in [`coding_record.json`](../crosswalk/coding_record.json).

> **The principle:** When an artifact encodes judgment and its author also authored the thing it judges, fixing the errors someone found is not enough. Re-derive it by a method that cannot inherit the author's priors, and publish the agreement rate so readers can see how much judgment was involved.

### 9. The canonical run kept the model's defaults after the model started returning empty lists for real filings

v0.1.0's prompt-track numbers came from subagents rather than the protocol-exact API harness, so v0.1.1 reran all of it as specified: 336 requests, model pinned, thinking and effort left at the model's defaults. A probe before the full run showed three of the four rulesets returning an empty list on the longest filing, with no thinking. Diagnostics on `stop-slop` then ruled out length, and showed that neither a neutral scope sentence nor a framed user turn changes it; maximum effort thought until it hit the 64,000-token cap without answering.

The alternative was to change the protocol until the model returned findings: a stronger instruction, forced effort, or filing text disguised as a draft. Each would have measured a protocol nobody ships, tuned by me until it produced the result I expected. The pinned protocol stayed, the empty lists are published as results, and the diagnostics are recorded in [`NOTES.md`](../NOTES.md) so a reader can see what was tested and what it ruled out; the cause of the empty lists remains open. One response did need handling: it spent 6,930 tokens thinking and then returned no text at all. That is a missing answer, not an empty list, so it was resent rather than scored as zero findings. The harness refuses to assemble results while any billed response is unusable, for exactly that case.

> **The principle:** When the system under test starts behaving unexpectedly, the instinct is to fix the harness until it behaves. Change the protocol only for a defect in the protocol. An empty list is a result to measure; a response with no answer in it is a non-answer to retry. Those are different events, and build decision 5 already drew the same line for a tool that refuses input.

### 10. A quote that is not in the text is not a flag on the text

Prompt-track tools report findings as quotes. v0.1.1 counted every returned finding toward flags per 1,000 words, and it parsed responses leniently: an element without a quote was dropped, so `[{}]` or `["bad response"]` became an empty result. An external review of the public repository showed both paths with synthetic inputs and found 11 of 393 human-corpus quotes that occur nowhere in their documents.

The cheap fix was to drop those findings silently, or to label them hallucinations and move on. Instead the provenance was checked first: the corpus files are unchanged since before the run, and each quote is verbatim in the raw API response, so they are the model's own non-verbatim output, not input drift. They are now counted, published in their own table, excluded from flag density and never credited to a plant, and the parser rejects any response with a malformed element rather than repairing it. The change moved three flags/1k means by 0.01 to 0.03 and three of their run-range bounds by 0.01 to 0.02, and restated the v0.1.0 `stop-slop` comparison figure from 6.90 to 6.86; nothing else changed, and the raw evidence was left exactly as returned.

> **The principle:** Validate what a model returns against what it was given before counting it, and when the two disagree, report the disagreement instead of resolving it quietly in either direction. A lenient parser and an unchecked quote fail the same way: they turn a malformed answer into a clean one.

## Limitations

The gaps a reviewer would find, surfaced here so they don't have to dig. Most of this section exists because an adversarial multi-agent review of this repo produced 60 findings, of which 37 were refuted and 23 survived verification, followed by a completeness review aimed at benchmark-design bias. The scoring defects, crosswalk errors and quoting-granularity confound those reviews confirmed are fixed and the numbers in [FINDINGS.md](FINDINGS.md) are the corrected ones; what remains is listed below.

### Wired but not yet complete

- **Prompt-track human-corpus columns mostly record whether the model returned findings at all.** The pinned model returns an empty list for 13 to 17 of 18 filings per run, so the prompt rows' flags/1k and term-of-art rates depend more on which documents got non-empty answers than on rule precision. Read them as "what this model returns with this ruleset at its defaults on filing prose", not as evidence that a ruleset is safe on regulated language, and not as evidence of why the lists are empty. The rule text that flagged the opinion sentence in v0.1.0 is unchanged, and on the API it flagged that sentence inside seeded draft fin-03, where the model returned findings, in two of three runs. Recall on the seeded drafts is unaffected: all 120 seeded passes returned findings.
- **The canonical protocol is one execution path of several.** The protocol puts each ruleset in the API `system` parameter. These rulesets ship as agent skills and are usually run inside agent harnesses that wrap them in other instructions. v0.1.0's subagent path was one such wrapper, and on the same text it produced human-corpus flag rates up to about twenty times higher (`stop-slop` 6.86 against 0.31 under the same quote rule). v0.1.1 measures the protocol, not every way a user might invoke a skill; the v0.1.0 data stays in git history and [`NOTES.md`](../NOTES.md) for comparison, and a measured execution-path comparison is on the roadmap.
- **Full-taxonomy recall counts patterns a tool never claimed.** All 122 plants are scored against all 6 tools, so a narrowly scoped ruleset is charged for patterns it never attempts. `the-antislop` makes no claim on hollow intensifiers or rhetorical setups, and averages 0.33 of 5 and 1 of 2 on them, caught incidentally by other rules. The claimed-only column corrects for this and is published beside full recall rather than instead of it, because each answers a different question: what a user gets, versus how well a tool does what it sets out to do. Claimed-only recall is only as good as the crosswalk that defines "claimed", which is why that crosswalk is double-coded (build decision 8).
- **Term-of-art matching is whole-phrase and case-insensitive, with no morphology.** Variants are enumerated explicitly in [`whitelist.json`](../corpora/finance-audit/whitelist.json) rather than stemmed. This under-counts rather than over-counts, which is the safer direction for a false-positive claim. Word boundaries are enforced, which matters more than it sounds: without them `qualified opinion` matches inside `unqualified opinion`, the opposite meaning, and that alone accounted for 9 spurious violations before it was fixed.
- **Seven of fourteen whitelist terms have zero corpus occurrences.** `significant deficiency`, `going concern`, `pervasive`, `qualified opinion`, `adverse opinion`, `comprehensive basis of accounting`, and `materiality` never appear in these 18 documents, so the term-of-art metric is effectively driven by the remaining seven, led by `critical audit matter` (54), `reasonable assurance` (37), `in all material respects` (24), and `comprehensive income` (21). Counts merge nested variants, so `comprehensive income` inside `other comprehensive income` is one occurrence. The unused entries are retained for the other registers and for corpus expansion, but they are currently carrying no weight.
- **Term-of-art density is concentrated in the audit opinions, and the headline rate understates it.** 149 of the 170 whitelist occurrences sit in the 10 opinion documents, which are only 16.2% of the corpus by word count. Measured against opinion text alone the rates are several times higher (`unslop` 0.996 rather than 0.341; the detector 0.554 rather than 0.144). Tool ordering is identical either way, so this is an interpretability limit rather than a fairness one. [`score.py`](../scripts/score.py) now reports the opinion and MD&A rates separately.
- **The term-of-art rule still depends on quote width at the margin.** Requiring protected text to be half the flagged span removes wide quotes flagged for something else, but it also drops a correct flag that happens to be quoted wide. On v0.1.0's subagent-path data two of `stop-slop`'s adverb flags on the opinion sentence were excluded this way. No canonical v0.1.1 number turns on a correct flag being dropped this way: on the human corpus no prompt-track flag targets protected text, and the one `the-antislop` quote that encloses a term was flagged for something else and is correctly excluded. It will matter on any path where the model applies a rule like the adverb ban to real opinion wording. A rule that tested only the flagged token inside a quote would avoid this, but prompt-track tools return quotes rather than the token they targeted, so the benchmark cannot see it.
- **Per-flag term-of-art rates partly measure reporting style.** `unslop` reports every occurrence and the detector reports once per analyzed chunk, so their per-flag rates differ (0.341 against 0.144) while the protected phrases they flag are identical. The (document, term) pair count beside each rate removes this; read the two together.
- **The `pervasive` entry cites the wrong framework for this corpus.** Pervasiveness is the ISA 705 and AU-C 705 threshold, not a PCAOB AS 3105 construction, and these are all PCAOB issuer audits. The entry is annotated and flagged for review rather than silently dropped. Zero corpus occurrences, so no published number depends on it.

### Deliberately deferred

- **Bare `material` and `materially` are excluded from the whitelist.** `materiality` (SAB 99) and `material weakness` (AS 2201) are protected; the standalone adjective and adverb are not. They occur constantly in ordinary filing prose ("material adverse effect", "materially affect our results"), and protecting them would make almost every tool flag on them count as a term-of-art violation, inflating the metric past usefulness. Adding them correctly requires context-sensitive matching, which is v0.2.
- **PCAOB inspection reports are not in the corpus.** The brief specifies them alongside EDGAR material. The 18 EDGAR documents already clear the 10-document and 20,000-word floors by a wide margin, so they were cut for v0.1 rather than partially done. They are PDFs and need a different extraction path.
- **No statistical significance testing.** With N=3 and 122 plants, the reported ranges are descriptive spread, not confidence intervals. Ordering claims rest on non-overlapping observed ranges, which is weaker than a significance test. Two rows are explicitly *not* ordered on that basis: `stop-slop`'s worst run and `no-ai-slop`'s best both matched 77 of 122 plants, so the middle of the headline table has a tie in it rather than a rank.
- **One of the 336 canonical responses was resent.** It spent 6,930 tokens thinking and returned no text block. Scoring it as zero findings would have been a guess, so it was discarded and resent under the same protocol (build decision 9). Its cost stays in the reported total, and the event is logged in [`NOTES.md`](../NOTES.md).

### Scope and fixtures by design

- **Each row measures the component tested, not the whole project.** The `unslop` row is its deterministic layer with the structural and soul passes off (build decision 7), not its full editing workflow, and the prompt rows are the API protocol, not every way an agent skill can be invoked.
- **One register of four ships in v0.1.** finance-audit went first because it is where false positives are most defensible to demonstrate: the collisions land on phrases with regulatory citations rather than on taste. casual-email, social, and technical-docs are built on the same harness and are the v0.2 deliverable. Cross-register claims are not yet available and are not made.
- **122 plants across 10 drafts is a methodology demonstration, not a production-scale evaluation.** Per-pattern cells are single-digit; the tier-level and headline numbers are where the sample supports weight. Per-pattern rows are published because they locate *where* a tool fails, not to support a claim about a 2/3 versus 3/3 difference.
- **Two MD&A extractions failed and are absent.** Coca-Cola and Deere use heading structures the Item 7 slicer does not match, so both contribute audit opinions only. Two further issuers fell outside the submissions-API recent-filings window. The gap is documented rather than silently backfilled.

Items with planned work have an entry in the [README roadmap](../README.md#%EF%B8%8F-roadmap).

## Prior Art & Acknowledgements

RegisterBench measures other people's work, so the acknowledgements are load-bearing. Every tool **under test** was cloned, read, and run at a pinned commit (SHAs in [`crosswalk/patterns.json`](../crosswalk/patterns.json)). The remaining entries below are method and literature debts rather than measured artifacts, and each one taught the benchmark something.

- **[conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing)**: the reference implementation of this genre. Three-tier vocabulary gating, six context profiles with an explicit tolerance matrix, and honest false-positive epistemics citing Liang et al. and Jabarian & Imas. Its `detector/CATEGORIES.md` maintains a deliberate skill-only list, which is what makes the executable-subset gap measurable rather than merely observable. It is also the target of the planned PR.
- **[MohamedAbdallah-14/unslop](https://github.com/MohamedAbdallah-14/unslop)**: proof that self-measurement in this space is possible and already being done seriously. CI-gated offline benchmarks, blind LLM-judge evaluation, and a refusal to make detector-defeat claims that the data does not support. Its comparison table conceding that a competitor's blind human-preference result is *"not publicly measured"* is the observation that defined this project's scope, generalised across the cohort.
- **[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop)**: the false-agency and narrator-from-a-distance patterns, both of which entered the canonical taxonomy as `str-false-agency`.
- **[petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop)**: pattern operationalisation style, and a detect mode that explicitly refuses to guess at authorship. The correct epistemics, stated plainly, before this benchmark existed to reward them.
- **[aplaceforallmystuff/the-antislop](https://github.com/aplaceforallmystuff/the-antislop)**: the tier-by-function idea, and the "horoscope test" as a compact statement of what generic prose actually fails at.
- **[sam-paech/slop-forensics](https://github.com/sam-paech/slop-forensics)**: corpus over-representation against a human baseline as a *method*, and the insight that the resulting word lists are decaying assets tied to model generations while the method is not. Directly responsible for this repo pinning every SHA, model string, and date.
- **[Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)**: the canonical taxonomy with per-pattern study citations, and the *"Ineffective indicators"* section, which is the evidence base against hard global bans. Transition words in isolation, formal prose, and correct grammar are documented non-signals.
- **Classifier false-positive literature** (Liang et al. on non-native English writers, the HC3 and RAID lineage): the prior art for measuring false positives in this domain at all. Those benchmarks target GPTZero-class *classifiers*. RegisterBench targets *rulesets*, and that distinction is the positioning.
- **[FASB ASC 220 and ASC 205-40](https://asc.fasb.org/), [PCAOB AS 2201, AS 2415, AS 3101, AS 3105, AS 3305](https://pcaobus.org/oversight/standards/auditing-standards), SEC SAB 99, Regulation S-K Item 303 and Regulation G, ISA 705 / AU-C 705**: every entry in the term-of-art whitelist carries a citation to one of these. The false-positive argument in this repo is only as good as those references.

Adopted patterns are cited above. RegisterBench extends them by combining cross-tool comparison under one protocol, flag behavior on verifiably pre-ChatGPT human text, and register-level splits, I found no earlier work in this space that combines all three, though that search was not exhaustive.
