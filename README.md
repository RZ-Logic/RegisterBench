<p align="center">
  <img src="assets/banner.svg" alt="RegisterBench: independent, cross-tool, register-split measurement of anti-AI-slop rulesets" width="100%"/>
</p>

<h1 align="center">RegisterBench</h1>

<p align="center">
  <strong>Every published number in this niche is self-graded.<br/>
  RegisterBench measures rules, not writers.</strong>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License: MIT"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"/></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/Node-18%2B-339933?style=for-the-badge&logo=nodedotjs&logoColor=white" alt="Node 18+"/></a>
  <img src="https://img.shields.io/badge/Tools_under_test-6-7C3AED?style=for-the-badge" alt="6 tools under test"/>
  <img src="https://img.shields.io/badge/Model-claude--sonnet--5_(pinned)-D97706?style=for-the-badge" alt="Model pinned"/>
  <img src="https://img.shields.io/badge/Status-v0.1.1-orange?style=for-the-badge" alt="Status v0.1.1"/>
</p>

<p align="center">
  <a href="#-why-i-built-this">Why</a> •
  <a href="#%EF%B8%8F-the-measurement-principle">Principle</a> •
  <a href="#-where-is-the-judgment">Where is the Judgment?</a> •
  <a href="#-what-ships-in-v01">What Ships</a> •
  <a href="#-v011-results-finance-audit">Results</a> •
  <a href="#-the-executable-subset-gap">Executable-Subset Gap</a> •
  <a href="#-stack">Stack</a> •
  <a href="#-how-to-read-this-repo">How to Read</a> •
  <a href="#-reproduction">Reproduction</a> •
  <a href="#%EF%B8%8F-build-decisions--lessons-learned">Build Decisions</a> •
  <a href="#-limitations">Limitations</a> •
  <a href="#%EF%B8%8F-roadmap">Roadmap</a> •
  <a href="#-prior-art--acknowledgements">Prior Art</a>
</p>

---

## 🧭 Why I Built This

I'm an ACCA with audit roots who pivoted into AI automation architecture. Working in audit, you learn that *"the policy says X"* and *"the code does X"* are different sentences, and the second one is the only one that matters when the regulator shows up.

That gap turns out to be the central finding of this repo, and it is measurable. The anti-AI-slop ecosystem ships rulesets as prose documents. The most rigorous of them, `avoid-ai-writing`, also ships a deterministic regex engine that implements the executable subset of the same catalog. Nobody had measured the distance between the two faces. On this register the prose read by a model beats its own engine under **every scoring cut tested**: by 28.1 points of recall on the published weighting (74.9% against 46.7%), by 18.7 on the patterns each face claims, and by between 12.8 and 37.1 points across alternative tier weightings. Same repository, same pinned commit, same rules. The document says X. The code does a demonstrably narrower X. The size of the gap depends on how you weight the taxonomy; its direction does not.

The second gap is the one my audit background is actually for. Several tools in this space maintain word lists that fire on regulated financial language. On 111,313 words of real pre-ChatGPT SEC filings, Tier 1 `comprehensive` fires on **`comprehensive income`**, a term defined in FASB ASC 220, and Tier 1 `leverage`, which the ruleset's own table scopes to the verb, fires on Caterpillar's **"covenant leverage ratio"**, a contractually defined debt covenant. A filer cannot rewrite either. No existing benchmark would have caught this, because measuring it requires knowing which phrases are legally load-bearing.

The third finding was not one I went looking for. Run through the API exactly as the protocol specifies, the pinned model mostly declines to apply the four prose rulesets to real filings at all: it returns an empty list for 13 to 17 of the 18 documents per run, almost always without thinking, while giving every synthetic draft a full pass. One tool's adverb ban flagged **"present fairly, in all material respects"**, the auditor's opinion sentence prescribed by PCAOB AS 3101.08, when it ran inside an agent harness. On the raw API it still flagged that sentence inside a seeded draft, but never in any of the ten real audit opinions, because the model returned an empty list for each of them. How a ruleset is executed moved its flag rate on the same text roughly twentyfold.

**On why measurement and not another editor.** The ecosystem has two maintained, capable editors already. What it does not have is a neutral scorekeeper: nearly every published number is a tool's own rules run against that tool's own fixtures. `unslop` is the only tool in the cohort that publishes benchmark numbers at all, and even its comparison table concedes that the blind human-preference result is *"not publicly measured"* for a competitor. That is the gap this fills.

This project sits alongside a portfolio thesis on defensible AI in regulated finance:

- **[FinAgent OS](https://github.com/RZ-Logic/finagent-os)**: *governance.* SOX-defensible properties enforced as Postgres triggers and missing-by-design tool surfaces.
- **[regulated-rag](https://github.com/RZ-Logic/regulated-rag)**: *retrieval.* Citation grounding and refusal enforced in code rather than promised in prompts.
- **RegisterBench** (this repo): *measurement.* The same discipline turned outward, applied to somebody else's published claims.

---

## 🛡️ The Measurement Principle

> **A tool's own fixtures cannot measure that tool. Recall on planted ground truth and flag behavior on verifiably human text are two different questions, and a benchmark has to answer both.**

Recall alone rewards a ruleset for firing constantly. Flag density alone rewards a ruleset for firing never. Reported together, on ground truth that was planted by hand before any tool ran, they describe a tool honestly. Neither number is a verdict on its own.

**On what a flag on human text means.** The human corpora predate November 2022, so no flag on them can be an AI catch. That does not automatically make a flag *wrong* as style advice. The claim these tools make is removing AI tells. A rule that fires densely on a 2019 10-K is demonstrating that it encodes a style preference, not an AI signal. Both metrics are reported and readers judge the rows.

**RegisterBench never claims or implies AI authorship of any text, anywhere.** It has no authorship-detection component, produces no "AI risk" score, and takes no position on who or what wrote any document it processes. It measures rules against a manifest.

**The empirical proof of the ground truth:** every one of the 122 planted instances was recorded in [`seeded/finance-audit/manifest.json`](seeded/finance-audit/manifest.json) at the moment it was written into a draft, with its exact span, canonical pattern ID, tier, and whether it was inserted or retained from the source filing. [`scripts/verify_manifest.py`](scripts/verify_manifest.py) re-locates every span in every draft and fails loudly on drift. No plant was reconstructed after the fact, and no scoring run can silently move the target.

---

## 🎯 Where is the Judgment?

This is the architectural through-line, adapted from the *"Where is the AI?"* enumeration in [FinAgent OS](https://github.com/RZ-Logic/finagent-os). Every stage of the benchmark is deterministic except the prompt-track detection stage itself, and that one is bounded at N=3 with mean, min, and max reported.

| # | Stage | Deterministic? | What it does |
|---|---|:-:|---|
| 1 | **Corpus acquisition** | ✅ | EDGAR submissions API by CIK, filing-date window, Item 7 and audit-opinion section slicing. Accession numbers and retrieval date written to [`PROVENANCE.md`](corpora/finance-audit/PROVENANCE.md) per file. |
| 2 | **Prose filtering** | ✅ | Line-level filter dropping numeric-majority and heading-fragment lines from flattened filing tables. `raw/` is preserved untouched as the provenance record. |
| 3 | **Seeding** | ✅ *(manual, recorded at write time)* | Patterns planted by hand into lightly adapted real filing text. Never model-generated, which would contaminate the ground truth. |
| 4 | **Manifest verification** | ✅ | Every span re-located, word counts and plant counts range-checked, every pattern ID validated against the crosswalk. Exits nonzero on any drift. |
| 5 | **Crosswalk** | ✅ *(blind double-coded)* | 29 canonical pattern IDs mapped to each tool's own rule identifiers, recording which patterns each tool claims at all. Coded independently by two coders per tool reading only that tool's source; 98.9% agreement, disagreements adjudicated. Per-cell evidence in [`coding_record.json`](crosswalk/coding_record.json). |
| 6 | **Code-track detection** | ✅ | `avoid-ai-writing` `analyzeText()` and `unslop` `humanize_deterministic_with_report()`, both SHA-pinned. Byte-identical across runs. |
| **7** | **Prompt-track detection** | **❌ stochastic** | Each tool's ruleset files verbatim as the API `system` prompt, uniform detect-only instruction appended, model pinned to `claude-sonnet-5` with thinking and effort left at the model's defaults. **N=3 independent runs per document on both corpora** through the Message Batches API, mean/min/max reported, served model recorded in every result file. v0.1.0's prompt-track numbers came from a subagent path instead; v0.1.1 replaces them, and the difference turned out to be a finding (see [Limitations](#-limitations)). |
| 8 | **Flag matching** | ✅ | Character-overlap at threshold 0.5 against the manifest span, or quoted-text containment. Document-level rules (density, rates, rhythm) match by crosswalked pattern. Unmatched flags logged separately. |
| 9 | **Scoring** | ✅ | Recall overall, by tier, by pattern. Flags per 1,000 words. Term-of-art violation rate against the citation-backed whitelist. |

Eight deterministic stages, one stochastic stage, bounded and reported with its spread.

> **The principle:** A benchmark whose own pipeline is stochastic cannot distinguish a tool's variance from its own. Isolate the stochasticity to the single stage that genuinely requires it, pin the model, run it N times, and publish the spread so readers can see how much of any gap is noise.

---

## 🧱 What Ships in v0.1

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│   One seeded draft (fin-04, adapted from Delta's FY2020 10-K MD&A):        │
│                                                                            │
│     Base text        ← real pre-2022 filing prose, source cited            │
│       │                                                                    │
│       ├─ plant  str-staccato-fragments   "Demand collapsed. Fleets         │
│       │                                   parked. Cash burned."            │
│       ├─ plant  phr-significance-inflation "a watershed moment for the     │
│       │                                     industry"                      │
│       ├─ plant  str-false-agency          "The market decided for us."     │
│       ├─ plant  lex-t1-vocab              "daunting"                       │
│       └─ ... 12 plants total, spans recorded at write time. Tier coverage  │
│           is complete across the 10-draft set, not within any one draft.   │
│                                                                            │
│     distractor      ← "unprecedented", retained from the real filing.      │
│                       Never counted in recall. Flags on it are kept        │
│                       in the raw outputs and read by hand in v0.1.1.       │
│                                                                            │
│     6 tools × detect-only  ← 2 deterministic engines, 4 prompt rulesets    │
│       │                      at N=3 each                                   │
│       ▼                                                                    │
│     Span match at 0.5 overlap → recall per tier, per pattern               │
│                                                                            │
│   Separately, the same 6 tools run over 111,313 words of real filings      │
│   with zero plants, where every flag is a style preference by construction. │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Component overview

| Component | What it is | Role of the model |
|-----------|-----------|:-:|
| **Corpus** ([`corpora/finance-audit/`](corpora/finance-audit/)) | 18 documents, 111,313 clean words. 10-K MD&A sections and audit opinions from 10 issuers, filed 2020-07-30 to 2021-03-24 (fiscal years ending 2020). Accession numbers and URLs per file. | None |
| **Term-of-art whitelist** ([`whitelist.json`](corpora/finance-audit/whitelist.json)) | 14 defined terms, each with a PCAOB, FASB ASC, SEC or statutory citation (or, for `pervasive`, ISA 705 / AU-C 705) and a note on the collision it creates, plus a `deliberately_excluded` block recording register words that were considered and rejected. | None |
| **Seeded drafts** ([`seeded/finance-audit/`](seeded/finance-audit/)) | 10 drafts, 330 to 397 words, 122 planted instances across a 29-pattern taxonomy spanning 6 tiers. Manual planting, recorded at write time. | None |
| **Crosswalk** ([`crosswalk/patterns.json`](crosswalk/patterns.json)) | Canonical IDs mapped to all 6 tool faces, with claimed-versus-unclaimed recorded per pattern. | None |
| **Code-track runners** ([`runners/code_track/`](runners/code_track/)) | Node and Python invocations, SHA-pinned, emitting a normalized findings schema. | None |
| **Prompt-track harness** ([`runners/prompt_track/`](runners/prompt_track/)) | Anthropic API harness: Message Batches for the canonical run, a synchronous path for smoke tests. Ruleset files verbatim as system prompt, detect-only instruction appended, N=3, model-pinned. Gated behind `--approved` because it spends money. | Detection only |
| **Scorer** ([`scripts/score.py`](scripts/score.py)) | Recall (overall, by tier, by pattern), flags per 1k, term-of-art rate, prompt-track variance. | None |

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

---

## 📊 v0.1.1 Results: finance-audit

Prompt-track detection completed 2026-10-12 (UTC) through the Message Batches API, model `claude-sonnet-5`, 336 requests, $7.04 at batch prices; code-track detection is deterministic. Crosswalk dated 2026-10-11, scoring 2026-10-12. 122 planted instances across 10 drafts; 111,313 words of human corpus. Full tables: [`results/finance-audit_2026-10-12.md`](results/finance-audit_2026-10-12.md) · raw per-tool findings: [`results/raw_*.json`](results/).

### Reading the tables

**The metrics.** Three describe what a tool catches, two describe what it disturbs.

| Metric | What it measures | Higher is |
|---|---|:-:|
| **Recall (mean)** | Of the 122 pattern instances planted by hand into the seeded drafts, the share a tool flagged. Each quoted finding is credited to at most one plant (see [matching](#%EF%B8%8F-build-decisions--lessons-learned), decision 1). Averaged across 3 independent runs for prompt-track tools. | better |
| **Recall range** | Lowest and highest single-run recall across those 3 runs, so readers can see how much of any gap between tools is run-to-run noise. Deterministic engines produce one value and no spread. | narrower |
| **Claimed-only recall** | The same matches, restricted to plants whose canonical pattern the tool's crosswalk row says it claims. Full recall measures coverage of the whole taxonomy; this measures accuracy on what the tool attempts. A tool that claims little loses less here. | better |
| **Flags/1k human** | Total flags a tool raised per 1,000 words of the human corpus. Because that corpus predates November 2022, no flag on it can be an AI catch, so this is a measure of how readily a ruleset fires on ordinary filing prose. For prompt-track tools it is a mean across 3 runs, with the range beside it, and on this corpus it mostly measures whether the model engaged at all (see [What the data shows](#what-the-data-shows)). | context |
| **Term-of-art violations/1k** | Flags on the human corpus whose flagged text is at least half protected regulatory phrasing from the [whitelist](corpora/finance-audit/whitelist.json), per 1,000 words. These are phrases a filer is not free to rewrite, so a flag here is the least defensible kind. The half-coverage rule stops a wide quote that merely encloses a term, flagged for some other reason, from counting. Reported two ways: per flag, and as distinct (document, term) pairs, because engines differ in whether they report every occurrence or once per document. | lower |

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

Cells in the tier table below are recall percentages; for prompt-track tools they are means across 3 runs. The tier split is the most diagnostic view in this repo: it is where the [executable-subset gap](#-the-executable-subset-gap) becomes visible, because deterministic engines hold their own on the lexical tiers and collapse on the structural one.

### Headline

| Tool | Track | Recall (mean) | Recall range | Claimed-only recall | Flags/1k human | Term-of-art /1k (doc-term pairs) |
|---|:-:|---|---|---|---|---|
| avoid-ai-writing skill | prompt | **74.9%** | 73.8% to 75.4% | 75.3% (28/29 patterns) | 0.39 (0.23 to 0.57) | 0 (0) |
| stop-slop | prompt | 64.2% | 63.1% to 65.6% | 68.7% (17/29) | 0.34 (0.27 to 0.42) | 0 (0) |
| no-ai-slop | prompt | 62.6% | 61.5% to 63.1% | **76.4%** (21/29) | 0.10 (0.05 to 0.15) | 0 (0) |
| the-antislop | prompt | 57.4% | 53.3% to 59.8% | 64.9% (22/29) | 0.36 (0.19 to 0.46) | 0 (0) |
| avoid-ai-writing detector | code | 46.7% | deterministic | 56.6% (20/29) | 1.09 | 0.144 (14) |
| unslop deterministic | code | 28.7% | deterministic | 37.0% (18/29) | 2.06 | 0.341 (14) |

### What survives every cut, and what does not

A benchmark whose taxonomy, drafts and scorer share one author owes readers a test of whether its conclusions are artifacts of that authorship. Recall is recomputed below under four tier weightings and on claimed patterns only. Full tables: [`results/finance-audit_2026-10-12.md`](results/finance-audit_2026-10-12.md).

| Cut | skill minus its own detector | rank 1 | rank order below rank 1 |
|---|---|---|---|
| Plant-weighted (published) | **+28.1** | aaw skill | stop-slop, no-ai-slop, the-antislop, detector, unslop |
| Equal weight per tier | **+29.7** | aaw skill | stop-slop, no-ai-slop, the-antislop, detector, unslop |
| Lexical tiers only | **+12.8** | aaw skill | no-ai-slop, detector, stop-slop, the-antislop, unslop |
| Phrasal + structural only | **+37.1** | aaw skill | stop-slop, the-antislop, no-ai-slop, detector, unslop |
| Claimed patterns only | **+18.7** | no-ai-slop | aaw skill, stop-slop, the-antislop, detector, unslop |

**Two conclusions are invariant: `avoid-ai-writing`'s prose beats its own regex engine in every cut, and `unslop` ranks last in every cut.** A third holds almost everywhere: the prose ranks first in all four weightings but second on claimed patterns, where `no-ai-slop` edges it, 76.4% to 75.3%, because `no-ai-slop` claims fewer patterns and is accurate on the ones it claims. **Everything else moves.** The size of the executable-subset gap ranges from 12.8 to 37.1 points depending on how the tiers are weighted, because the engine is competitive on vocabulary and collapses on structure, so any weighting that favours structure widens it. Equal tier weighting happens to reproduce the published order exactly. Each of the other three reorders some of rows 1 to 5: phrasal and structural alone swaps rows 3 and 4, lexical tiers alone lifts the detector to third, and claimed patterns alone moves the skill off rank 1. Read the headline table's ordering below rank 1 as a property of this taxonomy's composition, not of the tools.

### Recall by tier

Percentages, because prompt-track cells are 3-run means. Planted counts per tier are in the tier table above. Full fractions and per-run spread: [`results/finance-audit_2026-10-12.md`](results/finance-audit_2026-10-12.md).

| Tier | aaw skill | stop-slop | no-ai-slop | the-antislop | aaw detector | unslop |
|---|---|---|---|---|---|---|
| lex-1 (always-flag vocabulary) | **88.4%** | 50.7% | 65.2% | 43.5% | 87.0% | 52.2% |
| lex-2 (cluster-gated vocabulary) | 36.1% | 19.4% | **58.3%** | 13.9% | 16.7% | 16.7% |
| lex-3 (density-gated vocabulary) | 27.8% | **47.2%** | 19.4% | 22.2% | 0.0% | 0.0% |
| phrasal | **84.9%** | 72.2% | 69.0% | 77.8% | 59.5% | 40.5% |
| structural | 81.6% | **88.5%** | 73.6% | 69.0% | 27.6% | 6.9% |
| conversational | **100.0%** | 66.7% | 41.7% | 75.0% | 50.0% | 50.0% |

### What the data shows

**On genuine filings, the model mostly declines to run the prose rulesets at all.** Per run, the four prompt tools return an empty list for 13 to 17 of the 18 human documents. 182 of the 187 empty answers came back with zero thinking tokens, while every one of the 120 seeded-draft passes returned findings. When the model does engage, it is mostly on the same few long MD&As: Delta, Johnson & Johnson and Ford account for 20 of the 29 non-empty answers, which range from 1 to 47 flags. `stop-slop` skips 17 filings in every run and returns 30 to 47 flags on one, Delta's MD&A. Diagnostics on `stop-slop`, recorded in [`NOTES.md`](NOTES.md), rule out length. A 264-word excerpt of Ford's audit opinion gets an empty list with no thinking; six seeded drafts joined into one 2,194-word document get 59 findings after 18,759 thinking tokens. The seeded drafts are adapted from the same kind of filing text, so what separates them from the filings is the planted patterns, not the register: the model appears to triage authentic filing prose as clean before applying any rule. The triage is not absolute, as Delta's MD&A shows. Adding a sentence telling the model to apply each rule whatever the text's source changed nothing, framing the input as "Text to audit:" changed nothing, and maximum effort thought until it hit the 64,000-token cap without answering. The protocol was left as pinned, because this is what the model does with these rulesets at its defaults. The consequence for reading the table: prompt-track flags/1k and term-of-art rates on this corpus measure the model's triage of authentic filing prose more than the rules' precision. They are not evidence that these rulesets are safe on regulated prose.

**The execution path is the largest effect in the human-corpus columns.** v0.1.0 ran the same rulesets, at the same commits, on the same model, as task instructions to agent subagents. On that path `stop-slop` fired 6.90 times per 1,000 words of filing prose; on the canonical API path it fires 0.34. Nothing about the rules changed. A reader comparing these tools on false positives is mostly comparing how each one gets invoked, which is why the canonical protocol is pinned and the v0.1.0 data is kept in git history rather than averaged in.

**Between the two engines, which read every document the same way every time, recall and flag density are decoupled.** `unslop` fires 2.06 times per 1,000 words of filing prose, nearly twice the detector's 1.09, and recalls 28.7% against the detector's 46.7%. Firing more did not buy coverage. Recall measures whether a ruleset *covers* the taxonomy and flag density measures whether its rules are *indiscriminate*; they are different properties.

**Rule design shows in the tier split.** `stop-slop` leads the structural tier (88.5%) and the density-gated tier (47.2%) with almost no word list: its vocabulary table is 11 business-jargon entries (`references/phrases.md`) that overlap the canonical always-flag list at one term (`game-changer`). Its density-tier catches come incidentally from sentence-level rules, not density logic: the -ly adverb ban hits `effectively` and `significantly` directly, and adverb, false-agency, vague-declarative and quotable flags quote the text around the other planted words. Its 50.7% lex-1 figure is lifted by the adverb ban catching all 5 hollow intensifiers in every run, while it averages 6.7 of the 18 always-flag vocabulary plants. `no-ai-slop` is the reverse case: its "words to cut" list makes it the only tool above 50% on the cluster-gated tier (58.3%).

**Regulated language collides with rulesets in two distinct ways, and every collision in the canonical run comes from a deterministic engine.** The systematic collision is `comprehensive`, a Tier 1 always-replace word, firing on `comprehensive income`, a term defined in FASB ASC 220 that occurs 21 times in the corpus, including Delta's loss-year caption "Comprehensive (Loss)/Income". The detector and `unslop` both flag it in the same 12 documents. `unslop`'s per-flag rate is higher only because it reports every occurrence (21 flags) where the detector reports once per analyzed chunk, which is once per document except for the long MD&As split under build decision 5 (13 flags); counted as distinct (document, term) pairs, the two engines are identical at 14 each across `comprehensive income` and the leverage terms below. Per-flag rates partly measure reporting style, which is why both counts are published.

The precise collision is `leverage`, and it is the one with the cleanest fix. `avoid-ai-writing`'s word table scopes the entry to `leverage (verb)`, and its guidance on inflected forms says to judge by context when a variant "carries a distinct, legitimate meaning". Its regex engine cannot do that, so it fires on the finance noun: Caterpillar's *"covenant leverage ratio was 6.74 to 1"*, a contractually defined covenant metric, and Ford's *"Leverage."* section heading introducing its debt-to-equity disclosure. Applying the prescribed replacement yields "covenant use ratio". `unslop` makes the same error, flagging 17 occurrences across the same two filings. Notably the engine is also sometimes right: 3M's *"businesses share technology and leverage common fundamental strengths"* is genuine verb use and a fair flag. The distinction is exactly the one a regex cannot draw and a context profile could.

**The most serious collision first published, `stop-slop`'s, does not reproduce on the canonical path's human corpus, but it does reproduce on the canonical path.** v0.1.0 reported its blanket adverb ban flagging *fairly* in **"present fairly, in all material respects"**, the auditor's opinion wording prescribed by PCAOB AS 3101.08, in all 10 audit opinions. Flagging a defined accounting term is embarrassing; flagging the opinion sentence would break the filing. That result came from the subagent path. On the API the model returns an empty list for every one of those real opinions in all three runs, so the rule never gets the chance to misfire there. Where the model does read the text, it misfires as before: the same sentence is retained as a distractor in seeded draft fin-03, and the adverb ban flagged *fairly* there in two of three runs. The risk is demonstrated, not refuted; the human corpus simply hid it. All four prompt tools score zero term-of-art violations on the human corpus in every run. One `the-antislop` flag in one run encloses a protected term while flagging something else, which is the whole of its 0.003 containment rate.

**Variance separates most rows, but not the two in the middle.** The widest spread across three independent runs is `the-antislop`, 8 plants apart (53.3% to 59.8%); the prose skill and `no-ai-slop` vary by 2 plants each. The skill is separated from every other tool, and `the-antislop`'s worst run sits above the detector. `stop-slop` and `no-ai-slop` are not separated: `stop-slop`'s worst run and `no-ai-slop`'s best both matched 77 of 122 plants (63.1%), so those two rows are a tie rather than an ordering and should not be read as a rank. The spread is published precisely so that distinction is visible.

---

## 🔬 The executable-subset gap

The most interesting result is the one where a single repository competes against itself.

`avoid-ai-writing` ships a 714-line SKILL.md and a 45-category regex engine. Same commit, same rule catalog, same taxonomy. Scored against the same 122 plants, the prose reaches 74.9% and the engine reaches 46.7%, a gap of **28.1 points** on the published weighting. The gap is positive under every cut in [the robustness table](#what-survives-every-cut-and-what-does-not) but its size is not fixed: 12.8 points on lexical tiers alone, 37.1 on phrasal and structural alone. Where it concentrates is the whole story.

Skill cells are means across 3 runs; detector cells are a single deterministic run.

### Where string matching holds its own

| Pattern | Skill | Detector |
|---|---|---|
| `lex-t1-vocab` (delve, robust, seamless, testament to) | 16.33/18 | **18/18** |
| `phr-filler-wordy` (in order to, due to the fact that) | 3.67/4 | **4/4** |
| `phr-generic-conclusion` (only time will tell) | 4/4 | 4/4 |
| `phr-hedge-stack` (could potentially, may eventually) | 4/4 | 4/4 |
| `str-em-dash` | 4/4 | 4/4 |
| `str-formatting-slop` (bold overuse) | 2/2 | 2/2 |
| `phr-transition` (Moreover, Furthermore, Firstly) | **5.33/7** | 5/7 |

On six of these seven patterns the engine is not merely adequate, it is perfect, and on two of the fixed lists it beats the prose outright: 18 of 18 always-flag words against a mean of 16.33, and 4 of 4 wordy fillers against 3.67. Regex is the right tool for "does the token `delve` appear", and a model reading the same table occasionally lets one through. Transition words go the other way by a third of a plant, which is within run-to-run noise.

### Where the engine reaches zero

| Pattern | Skill | Detector |
|---|---|---|
| `phr-throat-clearing` ("Here's the thing:", "Let me be clear:") ¹ | 4/4 | **0/4** |
| `str-staccato-fragments` ("Demand collapsed. Fleets parked.") | 3/4 | **0/4** |
| `str-negative-parallelism` ("The question isn't X. It's Y.") | 3/3 | **0/3** |
| `str-negative-listing` ("Not a slogan. Not a poster. An operating system.") | 2/2 | **0/2** |
| `str-rhetorical-setup` ("So what changed this year?") ¹ | 2/2 | **0/2** |
| `con-chatbot-artifact` ("I hope this summary helps") ¹ | 2/2 | **0/2** |
| `str-rule-of-three` | 2.33/4 | **0/4** |
| `phr-signposting-meta` ("In this memorandum, we'll walk through") ¹ | 1.67/3 | **0/3** |
| `phr-false-range` ("from startups to superpowers") | 1.33/2 | **0/2** |
| `str-colon-reveal` ("The takeaway: cloud is the business.") | 1/2 | **0/2** |
| `str-false-agency` ("The market decided for us.") | 1/2 | **0/2** |
| `str-synonym-cycling` | 0.33/1 | **0/1** |

¹ The engine has a rule for this pattern; it did not fire on these drafts' wording.

Outside the density tier (build decision 4), twelve patterns where the engine never fires and the prose does. For eight of them the engine has no rule. For four (throat-clearing, signposting, rhetorical questions, chatbot residue) it has a rule, but the rule's fixed phrase list did not match these drafts' wording, which is a finding about regex brittleness rather than about absence. At the tier level the same split appears cleanly: structural recall is 81.6% for the prose and 27.6% for the engine.

One caveat on that 27.6%, surfaced by a completeness review of this repo. Six of the engine's eight structural matches come from document-level rules, which report a rate rather than locate a span: four `em-dash` matches whose flag text is a bare rate such as `"2 em dashes in 371 words"`, and one `formatting` flag credited to both formatting plants in the same draft. Scored on located spans alone, the engine's structural recall is 2/29, identical to `unslop`. The concession is deliberate and is described in build decision 1, and it runs *against* the headline by making the engine look better, so it is not inflating the gap. But the honest reading of that cell is that the engine mostly does not locate structural slop; it reports that some exists.

### This is documented architecture, not a defect

The repository's own [`detector/CATEGORIES.md`](https://github.com/conorbronsdon/avoid-ai-writing/blob/main/detector/CATEGORIES.md) maintains a "skill-only" list of rules it implements in prose but not in the engine, naming them as LLM-judgment patterns, and it covers several of the eight no-rule patterns above (contrast structures, false ranges, synonym cycling, punchline fragments). The maintainer is not claiming the engine is complete, and RegisterBench is not accusing it of being incomplete. The contribution is putting a number on a boundary that both sides already knew existed, and showing how much that number depends on what you count. On the published weighting it is 28.1 points. On the patterns each face claims it is 18.7, because the engine claims 20 patterns and the prose claims 28, so full-taxonomy scoring charges the engine for patterns it never attempts. The 18.7 is the fairer measure of implementation distance; the 28.1 is the fairer measure of what a user gets from each face.

Not all 28 points are pure judgment, and the honest decomposition matters. 11.5 points come from the eight patterns where the engine has no rule at all. 7.9 come from the four where it has a rule that did not fire on these plants. 2.7 come from the density tier, where the prose reaches 27.8% and the engine 0.0% (see build decision 4). 1.9 come from cluster gating: the engine's gate costs it 19.4 points of `lex-t2-cluster` recall against the prose reading the same word list. The remaining 4.1 is the net of scattered partial differences, after subtracting the two patterns where the engine beats the prose.

That number is useful in three directions. For a user, it says a regex pre-commit hook is a floor rather than a substitute. For the maintainer, it locates where engine investment would pay. For anyone comparing tools, it says an artifact's execution mode matters as much as its rule count, and a benchmark that measures only one face of a two-faced tool is measuring the wrong thing.

> **The principle:** When a project ships both a specification and an implementation of that specification, they are two artifacts and they deserve two measurements. The distance between them is not a footnote, it is a finding.

---

## 🔌 Stack

| Layer | Tool | Why |
|-------|------|-----|
| Corpus source | SEC EDGAR submissions API + Archives | Public domain, machine-addressable by CIK, filing dates are the provenance. No scraping of anything gated. |
| Corpus extraction | Python stdlib `html.parser` | 18 documents does not justify a dependency. Block-level tag handling is enough to recover paragraph structure from filing HTML. |
| Code-track invocation | Node 18+ (`require`), Python 3.10+ (direct import) | Each engine called through its own documented API rather than its CLI, which bypasses file-type gates and keeps the findings schema stable. |
| Prompt-track invocation | Anthropic Message Batches API (canonical run) and Messages API (smoke tests), stdlib `urllib` | Model pinned, and the model the API reports serving recorded in every result file. Batches run at half price with each ruleset's system prompt cached. The batch runner resumes after any interruption without resending a saved response, and refuses to submit unless the caller states the exact request count. No SDK dependency. |
| Scoring | Python stdlib | Span arithmetic and set membership. Nothing here needs pandas. |
| Result format | JSON per run, Markdown per register | Raw findings are diffable and re-scorable without re-running any tool. |

**No infrastructure novelty.** Everything here is stdlib, one HTTP API, and five cloned repositories. The contribution is the application layer: the seeded-manifest methodology, the citation-backed term-of-art whitelist, the crosswalk that lets six different taxonomies be compared under one protocol, and the decision to measure both faces of a two-faced tool.

---

## 📖 How to Read This Repo

For a reviewer with limited time:

1. **[The "Where is the Judgment?" table](#-where-is-the-judgment)** above. ~90 seconds. The benchmark's stance on its own stochasticity, in one table.
2. **[The executable-subset gap](#-the-executable-subset-gap)** above. ~4 minutes. The headline finding and why it is a finding rather than an accusation.
3. **[`corpora/finance-audit/whitelist.json`](corpora/finance-audit/whitelist.json)**. ~3 minutes. 14 defined terms with citations, and the words deliberately left out. This is the file that makes the false-positive claims defensible rather than aesthetic.
4. **[`seeded/finance-audit/manifest.json`](seeded/finance-audit/manifest.json)** next to any draft, for example [`fin-04.md`](seeded/finance-audit/fin-04.md). ~4 minutes. The ground truth in raw form, including the `distractors` block that keeps retained terms of art out of recall.
5. **[`scripts/score.py`](scripts/score.py)**. ~5 minutes. Span matching and the three metrics. `DOC_LEVEL_RULES` is where document-scoped rules are handled separately from quoted spans.

Total core read: ~17 minutes.

If you want depth on one cut: [`NOTES.md`](NOTES.md) carries the working log, including every methodology decision, the reason the density tier reads 0/12 for two tools, and the full account of what the prompt-track run cost to complete.

---

## 🔁 Reproduction

Node 18+ and Python 3.10+ are the only requirements. The code track needs no package installs, because both engines are dependency-free.

Commands below use `python3`. On Windows use the `py` launcher instead; every script is stdlib-only and otherwise platform-independent. All commands run from the repository root.

### Clone the tools at their pinned commits

SHAs are recorded in [`crosswalk/patterns.json`](crosswalk/patterns.json) and in every result file. Clone into a sibling `tools/` directory, or set `REGISTERBENCH_TOOLS_DIR` to point elsewhere.

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

This spends money against an Anthropic API key and is gated behind an explicit flag. The harness reads the key from `REGISTERBENCH_API_KEY`, set in the environment or in a gitignored `.env` at the repo root (template in [`.env.example`](.env.example)). It deliberately ignores `ANTHROPIC_API_KEY`: other tools read that name, Claude Code among them, and a dedicated one keeps the benchmark key and its spend limit scoped to this harness.

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

[`run_prompt_batch.py`](runners/prompt_track/run_prompt_batch.py) is the canonical path: all 336 requests (4 tools, 28 documents, 3 runs) through the Message Batches API. `submit` refuses unless `--expect` matches the number of requests it would send, and `--only` takes globs over request IDs such as `aawskill-human-F_2021_mdna-r1` for a partial run. `wait` polls and saves every response; `assemble` writes `results/raw_<short>_<set>_run<n>.json` (for example `raw_aawskill_seeded_run1.json`) and refuses if any billed response hit `max_tokens`, failed to parse, or came from a different ruleset, system prompt, model or `max_tokens` than the rest. An interrupted run resumes without resending anything already saved. Raw API responses are archived under `results/prompt_runs/`, which is gitignored. The synchronous harness, [`run_prompt_tool.py`](runners/prompt_track/run_prompt_tool.py), is for smoke tests and short inputs, and refuses inputs over 5,000 words. Directory inputs skip `README.md`, `PROVENANCE.md` and `NOTES.md` on both paths, as the code-track runners do. The v0.1.1 run cost $7.04 at batch prices.

---

## 🛠️ Build Decisions & Lessons Learned

Nine non-obvious choices and the alternatives rejected.

### 1. Recall is span-based, not attribution-based, and each quoted finding is consumed once

A plant counts as recalled if *any* rule fires on its span, even when the tool names that rule something the crosswalk did not predict. The crosswalk is used for analysis, never for span-level recall credit.

The alternative was requiring the tool's rule name to map to the canonical pattern ID before granting credit. Rejected because these six tools disagree profoundly on taxonomy: what `stop-slop` calls "Binary Contrasts", `no-ai-slop` calls "Binary contrasts", `the-antislop` calls "Language 8: Negative parallelisms", and `avoid-ai-writing` calls "It's not X, it's Y structures". Requiring name agreement would have scored vocabulary alignment rather than detection ability, and would have quietly penalised whichever tool happened to name things least like my crosswalk.

**Span-based matching needs one guard, and v0.1 initially shipped without it.** Overlap is measured against the shorter of the two spans, so a plant fully contained in a longer quote scores a perfect match. Combined with unlimited reuse of a single finding, that made a paragraph-long quote count as having located every plant inside it. An adversarial review of this repo demonstrated the ceiling: a synthetic tool emitting one finding per draft containing the whole draft scored 122/122. Recall now assigns quoted findings to plants by maximum bipartite matching, so each finding is credited at most once. Maximum matching rather than a greedy scan, because greedy would make a tool's score depend on the order plants happen to appear in the manifest.

Document-level rules are deliberately exempt from consumption. A flag that says "you overuse em dashes" describes the whole document, so it legitimately covers every plant of its canonical pattern, and this is the one place crosswalk attribution does grant credit. Applying strict consumption there instead would have introduced an equal and opposite understatement. Correcting this moved published recall by 0.8 to 8.5 points depending on how verbose a tool's quoting style is, and it reordered two rows.

**The same confound existed on the human corpus and was fixed later than it should have been.** Term-of-art violations originally counted any flag that overlapped a protected term at half of the shorter span, so any quote enclosing a term counted, however wide. That is the identical `min()` denominator, applied in the opposite direction: it punished wide quoting instead of rewarding it. On v0.1.0's subagent-path data, `stop-slop`, whose passive-voice and list rules were the only rules in the cohort whose quotes enclosed protected opinion wording without targeting it, was credited with 27 violations and the worst rate in the cohort. Of the 19 the stricter rule removed, 17 were quotes flagged for something else that happened to contain a protected phrase. The rule now requires protected-term text to make up at least half of the flagged span, and both counts are published. The fix is not perfect: on that same data, two of `stop-slop`'s adverb flags on the opinion sentence quoted the whole clause and fell under the threshold (protected text 37% and 32% of the quote), so quote width still matters at the margin. In the canonical v0.1.1 run the question barely arises on the human corpus: no prompt-track flag targets protected text there, and the one `the-antislop` quote that encloses a protected term while flagging something else is correctly excluded (see [What the data shows](#what-the-data-shows)). The rule is built for data where the model engages more.

> **The principle:** Decide what your metric is allowed to be confounded by. A detection benchmark that punishes naming differences is partly a naming benchmark. One that rewards or punishes quote length is partly a verbosity benchmark. Neither is visible in the headline number, so both have to be designed out on purpose, and a guard added on one metric has to be checked for on every other metric that uses the same arithmetic.

### 2. Distractors live in the manifest as first-class entries

Terms of art retained from the real base text (`comprehensive income`, `reasonable assurance`, `critical audit matter`, `significant deficiency`) are recorded in the manifest as `distractors`, structurally separate from `plants`. They are never counted in recall. Flags landing on them are kept in the raw outputs for the false-positive analysis; v0.1.1 reads them by hand rather than scoring them, and automated distractor scoring is on the roadmap.

The simpler design was to keep the seeded set clean and measure false positives only on the human corpus. Rejected because the interesting collisions are register-specific, and a term-of-art collision inside a seeded draft is evidence that a tool cannot distinguish planted slop from mandated language *in the same document*. That is a sharper claim than the same collision found on a separate corpus. It paid off in v0.1.1: the model declined every real audit opinion, but it read the seeded drafts, and `stop-slop`'s adverb ban flagged *fairly* in a retained opinion sentence in fin-03 in two of three runs. The distractors caught a collision the human corpus could not show.

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

Filing HTML flattens financial tables into number-heavy lines. Left in, they inflate the denominator of flags per 1,000 words and make every tool look more precise than it is. [`scripts/clean_corpus.py`](scripts/clean_corpus.py) drops numeric-majority and short heading-fragment lines. All scoring runs against `clean/`.

`raw/` ships alongside it, untouched, because the filter is a judgment call and a reader who disagrees with it needs to be able to re-derive the numbers under a different one.

> **The principle:** Any preprocessing step that moves a headline metric has to ship with its own input. A cleaned corpus without its raw counterpart is an unfalsifiable number.

### 7. `unslop` runs with its structural and soul passes disabled

`unslop`'s deterministic layer at `intensity=full` covers the widest rule set, but two of its passes (`structural`, `soul`) split long sentences and insert contractions. Those are rewrites, not detections. Counting them as flags would have credited it for finding slop when it was reformatting prose.

Its voice-profile machinery needed no special handling: the deterministic path ignores voice parameters entirely, so the runs are voice-neutral by construction rather than by configuration. Verified in source before relying on it.

> **The principle:** When a tool blends detection and rewriting, the benchmark has to draw the line the tool does not. Read the source to find out where the line actually is rather than trusting the flag name.

### 8. The crosswalk was re-coded blind, because the person who wrote the drafts also wrote the map

The crosswalk decides which patterns each tool "claims", and claimed-only recall inherits every decision in it. v0.1.0's crosswalk was hand-authored by the same person who wrote the seeded drafts and the scorer, which is exactly the setup in which a benchmark quietly favours its expectations. A completeness review found five mappings wrong against the tools' own source, three of them under-crediting `avoid-ai-writing` on rules its SKILL.md states explicitly.

Patching those five would have fixed the known errors and left the method unchanged. Instead every cell was re-coded from scratch. For each of the six tool faces, two coders read only that tool's source, never the existing crosswalk, under one written claim standard applied identically to every tool. One worked pattern-first, the other rule-first, so they could not share a blind spot through a shared reading order. They agreed on 172 of 174 cells (98.9%); the two disagreements were adjudicated against source. A later review flagged three cells as applying the standard inconsistently between tools, and each went to a fresh 3-adjudicator vote: two decisions were upheld, and one cell both coders had agreed on (the-antislop crediting a hidden-truth header rule as novelty inflation) was overturned 0 votes to 3, so the same reading now applies to the-antislop and stop-slop. The final map differs from the hand-authored version in 15 claim decisions, in both directions and across five of the six tools, which is the signature of noise in a hand-built map rather than of a thumb on the scale. Every cell's evidence, with file, line and quote, is in [`coding_record.json`](crosswalk/coding_record.json).

> **The principle:** When an artifact encodes judgment and its author also authored the thing it judges, fixing the errors someone found is not enough. Re-derive it by a method that cannot inherit the author's priors, and publish the agreement rate so readers can see how much judgment was involved.

### 9. The canonical run kept the model's defaults after the model started declining real filings

v0.1.0's prompt-track numbers came from subagents rather than the protocol-exact API harness, so v0.1.1 reran all of it as specified: 336 requests, model pinned, thinking and effort left at the model's defaults. A probe before the full run showed three of the four rulesets returning an empty list on the longest filing, with no thinking. Diagnostics on `stop-slop` then ruled out length, and showed that neither a neutral scope sentence nor a framed user turn changes it; maximum effort thought until it hit the 64,000-token cap without answering.

The alternative was to change the protocol until the model engaged: a stronger instruction, forced effort, or filing text disguised as a draft. Each would have measured a protocol nobody ships, tuned by me until it produced the result I expected. The pinned protocol stayed, the empty lists are published as results, and the diagnostics are recorded in [`NOTES.md`](NOTES.md) so a reader can see the cause rather than infer it. One response did need handling: it spent 6,930 tokens thinking and then returned no text at all. That is a missing answer, not an empty list, so it was resent rather than scored as zero findings. The harness refuses to assemble results while any billed response is unusable, for exactly that case.

> **The principle:** When the system under test starts behaving unexpectedly, the instinct is to fix the harness until it behaves. Change the protocol only for a defect in the protocol. A model declining a task is behavior to measure; a model returning nothing is a non-answer to retry. Those are different events, and build decision 5 already drew the same line for a tool that refuses input.

---

## 🫡 Limitations

The gaps a reviewer would find, surfaced here so they don't have to dig. Most of this section exists because an adversarial multi-agent review of this repo produced 60 findings, of which 37 were refuted and 23 survived verification, followed by a completeness review aimed at benchmark-design bias. The scoring defects, crosswalk errors and quoting-granularity confound those reviews confirmed are fixed and the numbers above are the corrected ones; what remains is listed below.

### Wired but not yet complete

- **Prompt-track human-corpus columns measure the model's triage of authentic filing prose, not only the rules.** The pinned model returns an empty list for 13 to 17 of 18 filings per run, so the prompt rows' flags/1k and term-of-art rates mostly record whether it engaged, and on which documents. Read them as "what this model does with this ruleset at its defaults on filing prose", not as evidence that a ruleset is safe on regulated language. The rule text that flagged the opinion sentence in v0.1.0 is unchanged, and on the API it still flags that sentence where the model reads it, inside seeded draft fin-03. Recall on the seeded drafts is unaffected: all 120 seeded passes returned findings.
- **The canonical protocol is one execution path of several.** The protocol puts each ruleset in the API `system` parameter. These rulesets ship as agent skills and are usually run inside agent harnesses that wrap them in other instructions. v0.1.0's subagent path was one such wrapper, and on the same text it produced human-corpus flag rates up to twenty times higher. v0.1.1 measures the protocol, not every way a user might invoke a skill; the v0.1.0 data stays in git history and [`NOTES.md`](NOTES.md) for comparison, and a measured execution-path comparison is on the roadmap.
- **Full-taxonomy recall counts patterns a tool never claimed.** All 122 plants are scored against all 6 tools, so a narrowly scoped ruleset is charged for patterns it never attempts. `the-antislop` makes no claim on hollow intensifiers or rhetorical setups, and averages 0.33 of 5 and 1 of 2 on them, caught incidentally by other rules. The claimed-only column corrects for this and is published beside full recall rather than instead of it, because each answers a different question: what a user gets, versus how well a tool does what it sets out to do. Claimed-only recall is only as good as the crosswalk that defines "claimed", which is why that crosswalk is double-coded (build decision 8).
- **Term-of-art matching is whole-phrase and case-insensitive, with no morphology.** Variants are enumerated explicitly in [`whitelist.json`](corpora/finance-audit/whitelist.json) rather than stemmed. This under-counts rather than over-counts, which is the safer direction for a false-positive claim. Word boundaries are enforced, which matters more than it sounds: without them `qualified opinion` matches inside `unqualified opinion`, the opposite meaning, and that alone accounted for 9 spurious violations before it was fixed.
- **Seven of fourteen whitelist terms have zero corpus occurrences.** `significant deficiency`, `going concern`, `pervasive`, `qualified opinion`, `adverse opinion`, `comprehensive basis of accounting`, and `materiality` never appear in these 18 documents, so the term-of-art metric is effectively driven by the remaining seven, led by `critical audit matter` (54), `reasonable assurance` (37), `in all material respects` (24), and `comprehensive income` (21). Counts merge nested variants, so `comprehensive income` inside `other comprehensive income` is one occurrence. The unused entries are retained for the other registers and for corpus expansion, but they are currently carrying no weight.
- **Term-of-art density is concentrated in the audit opinions, and the headline rate understates it.** 149 of the 170 whitelist occurrences sit in the 10 opinion documents, which are only 16.2% of the corpus by word count. Measured against opinion text alone the rates are several times higher (`unslop` 0.996 rather than 0.341; the detector 0.554 rather than 0.144). Tool ordering is identical either way, so this is an interpretability limit rather than a fairness one. [`score.py`](scripts/score.py) now reports the opinion and MD&A rates separately.
- **The term-of-art rule still depends on quote width at the margin.** Requiring protected text to be half the flagged span removes wide quotes flagged for something else, but it also drops a correct flag that happens to be quoted wide. On v0.1.0's subagent-path data two of `stop-slop`'s adverb flags on the opinion sentence were excluded this way. No canonical v0.1.1 number turns on a correct flag being dropped this way: on the human corpus no prompt-track flag targets protected text, and the one `the-antislop` quote that encloses a term was flagged for something else and is correctly excluded. It will matter on any path where the model applies a rule like the adverb ban to real opinion wording. A rule that tested only the flagged token inside a quote would avoid this, but prompt-track tools return quotes rather than the token they targeted, so the benchmark cannot see it.
- **Per-flag term-of-art rates partly measure reporting style.** `unslop` reports every occurrence and the detector reports once per analyzed chunk, so their per-flag rates differ (0.341 against 0.144) while the protected phrases they flag are identical. The (document, term) pair count beside each rate removes this; read the two together.
- **The `pervasive` entry cites the wrong framework for this corpus.** Pervasiveness is the ISA 705 and AU-C 705 threshold, not a PCAOB AS 3105 construction, and these are all PCAOB issuer audits. The entry is annotated and flagged for review rather than silently dropped. Zero corpus occurrences, so no published number depends on it.

### Deliberately deferred

- **Bare `material` and `materially` are excluded from the whitelist.** `materiality` (SAB 99) and `material weakness` (AS 2201) are protected; the standalone adjective and adverb are not. They occur constantly in ordinary filing prose ("material adverse effect", "materially affect our results"), and protecting them would make almost every tool flag on them count as a term-of-art violation, inflating the metric past usefulness. Adding them correctly requires context-sensitive matching, which is v0.2.
- **PCAOB inspection reports are not in the corpus.** The brief specifies them alongside EDGAR material. The 18 EDGAR documents already clear the 10-document and 20,000-word floors by a wide margin, so they were cut for v0.1 rather than partially done. They are PDFs and need a different extraction path.
- **No statistical significance testing.** With N=3 and 122 plants, the reported ranges are descriptive spread, not confidence intervals. Ordering claims rest on non-overlapping observed ranges, which is weaker than a significance test. Two rows are explicitly *not* ordered on that basis: `stop-slop`'s worst run and `no-ai-slop`'s best both matched 77 of 122 plants, so the middle of the headline table has a tie in it rather than a rank.
- **One of the 336 canonical responses was resent.** It spent 6,930 tokens thinking and returned no text block. Scoring it as zero findings would have been a guess, so it was discarded and resent under the same protocol (build decision 9). Its cost stays in the reported total, and the event is logged in [`NOTES.md`](NOTES.md).

### Scope and fixtures by design

- **One register of four ships in v0.1.** finance-audit went first because it is where false positives are most defensible to demonstrate: the collisions land on phrases with regulatory citations rather than on taste. casual-email, social, and technical-docs are built on the same harness and are the v0.2 deliverable. Cross-register claims are not yet available and are not made.
- **122 plants across 10 drafts is a methodology demonstration, not a production-scale evaluation.** Per-pattern cells are single-digit; the tier-level and headline numbers are where the sample supports weight. Per-pattern rows are published because they locate *where* a tool fails, not to support a claim about a 2/3 versus 3/3 difference.
- **Two MD&A extractions failed and are absent.** Coca-Cola and Deere use heading structures the Item 7 slicer does not match, so both contribute audit opinions only. Two further issuers fell outside the submissions-API recent-filings window. The gap is documented rather than silently backfilled.

Items with planned work have a roadmap entry below.

---

## 🗺️ Roadmap

- [ ] **v0.2: the upstream PR to `avoid-ai-writing`.** New `regulated` context profile, tolerance-matrix rows, word-table exception list with a citation per term, hedging and significance-inflation carve-outs for defined-term usage, auto-detection cues, and detector fixtures passing `npm test`. Argued from the finance-audit data above. This is the second deliverable of the project and the more important one.
- [x] **v0.1.1: canonical prompt-track rerun through the API harness.** Done 2026-10-12: all 336 requests through the Message Batches API at N=3 on both corpora, replacing the subagent-path numbers.
- [ ] **v0.2: execution-path comparison.** Run the same rulesets through an agent harness alongside the API protocol and publish both, since v0.1.0 to v0.1.1 showed the path moves human-corpus flag rates by up to twentyfold on identical text.
- [ ] **v0.2: casual-email register.** Enron corpus (CMU release), prose bodies, personal names redacted.
- [ ] **v0.2: social register.** Pre-2022 Hacker News comments and personal-blog posts.
- [ ] **v0.2: technical-docs register.** OSS documentation at git tags dated 2021 or earlier, commit dates as provenance.
- [ ] **v0.2: score distractor flags.** The manifest records every retained term of art in the seeded drafts; v0.1.1 reads flags on them by hand. Scoring them would publish the in-document collision rate that caught `stop-slop` on the canonical path.
- [ ] **v0.2: context-sensitive term-of-art matching.** Enables protecting bare `material` and `materially` in their defined senses without swamping the metric.
- [ ] **v0.3: PCAOB inspection reports** added to the finance-audit corpus, with a PDF extraction path.
- [ ] **v0.3: cross-register comparison.** The claim the four-register set exists to support: which rules are register-invariant and which are a single register's style preference wearing a general rule's clothing.
- [ ] **v0.3: model-generation decay measurement.** The `slop-forensics` insight is that slop lists are decaying assets tied to model generations while the method is not. Re-running a pinned protocol against successive model generations measures that decay directly.

---

## 🙏 Prior Art & Acknowledgements

RegisterBench measures other people's work, so the acknowledgements are load-bearing. Every tool **under test** was cloned, read, and run at a pinned commit (SHAs in [`crosswalk/patterns.json`](crosswalk/patterns.json)). The remaining entries below are method and literature debts rather than measured artifacts, and each one taught the benchmark something.

- **[conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing)**: the reference implementation of this genre. Three-tier vocabulary gating, six context profiles with an explicit tolerance matrix, and honest false-positive epistemics citing Liang et al. and Jabarian & Imas. Its `detector/CATEGORIES.md` maintains a deliberate skill-only list, which is what makes the executable-subset gap measurable rather than merely observable. It is also the target of the planned PR.
- **[MohamedAbdallah-14/unslop](https://github.com/MohamedAbdallah-14/unslop)**: proof that self-measurement in this space is possible and already being done seriously. CI-gated offline benchmarks, blind LLM-judge evaluation, and a refusal to make detector-defeat claims that the data does not support. Its comparison table conceding that a competitor's blind human-preference result is *"not publicly measured"* is the observation that defined this project's scope, generalised across the cohort.
- **[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop)**: the false-agency and narrator-from-a-distance patterns, both of which entered the canonical taxonomy as `str-false-agency`.
- **[petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop)**: pattern operationalisation style, and a detect mode that explicitly refuses to guess at authorship. The correct epistemics, stated plainly, before this benchmark existed to reward them.
- **[aplaceforallmystuff/the-antislop](https://github.com/aplaceforallmystuff/the-antislop)**: the tier-by-function idea, and the "horoscope test" as a compact statement of what generic prose actually fails at.
- **[sam-paech/slop-forensics](https://github.com/sam-paech/slop-forensics)**: corpus over-representation against a human baseline as a *method*, and the insight that the resulting word lists are decaying assets tied to model generations while the method is not. Directly responsible for this repo pinning every SHA, model string, and date.
- **[Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)**: the canonical taxonomy with per-pattern study citations, and the *"Ineffective indicators"* section, which is the evidence base against hard global bans. Transition words in isolation, formal prose, and correct grammar are documented non-signals.
- **Classifier false-positive literature** (Liang et al. on non-native English writers, the HC3 and RAID lineage): the prior art for measuring false positives in this domain at all. Those benchmarks target GPTZero-class *classifiers*. RegisterBench targets *rulesets*, and that distinction is the positioning.
- **[FASB ASC 220 and ASC 205-40](https://asc.fasb.org/), [PCAOB AS 2201, AS 2415, AS 3101, AS 3105, AS 3305](https://pcaobus.org/oversight/standards/auditing-standards), SEC SAB 99, Regulation S-K Item 303 and Regulation G, ISA 705 / AU-C 705**: every entry in the term-of-art whitelist carries a citation to one of these. The false-positive argument in this repo is only as good as those references.

Adopted patterns are cited above. RegisterBench extends them by combining cross-tool comparison under one protocol, flag behavior on verifiably pre-ChatGPT human text, and register-level splits, which no published work in this space had done together.

---

## 📜 License

MIT: see [`LICENSE`](./LICENSE). Use this, fork it, take the methodology into your own work. If you benchmark something with it, the acknowledgement is a link back; the value to me is neutral measurement becoming normal in this space.

---

## 💬 Contact

**Rizwan Ahmed, ACCA**
Founder, Velocyt Consulting · Mississauga, ON

- Website: [velocyt.ca](https://velocyt.ca)
- GitHub: [@RZ-Logic](https://github.com/RZ-Logic)

Also built: __[FinAgent OS](https://github.com/RZ-Logic/finagent-os)__ (governance pillar, SOX-defensible AI for crypto-finance) · __[regulated-rag](https://github.com/RZ-Logic/regulated-rag)__ (retrieval pillar, citation grounding as architecture) · __[Immi-OS](https://github.com/RZ-Logic/immi-os)__ (immigration automation, real clients) · __[JobSignal Engine](https://github.com/RZ-Logic/jobsignal-engine)__ (autonomous job-search pipeline)

---

<p align="center">
  <em>If you find this useful, a star helps others find it.</em>
  <br/><br/>
  <sub>Built in Toronto by an audit-trained ACCA who wanted to know whether the rulesets telling everyone how to write had ever been measured by anyone but themselves.</sub>
</p>
