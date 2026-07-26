# Build notes and open decisions (session 2026-07-24)

Working log of methodology decisions made during P1 build. For Rizwan's review. Items marked REVIEW need a call before publication.

## Decisions taken

1. **Distractors in seeded drafts.** Terms of art retained from base filing text ("comprehensive income", "reasonable assurance") are recorded in the manifest as distractors, never counted in recall. Flags overlapping them feed the FP analysis. This gives term-of-art collision data inside the seeded set, not just the human corpus.

2. **Plant origin field.** Some pattern instances occur naturally in real filing prose (J&J's actual 10-K says "Leveraging the extensive resources" and "empowered and inspired"). Retained instances are marked `origin: retained` and count in recall the same as inserted ones; the split is reportable if it becomes interesting.

3. **lex-t3 density plants are sub-threshold by design for some engines.** Drafts plant density words at 3 occurrences per ~350 words (~0.9%). That crosses the-antislop's claimed gate (3+ per section) but sits far below avoid-ai-writing's engine gate (3% of word count, min 3, which is 10+ occurrences in a 350-word draft). Result: avoid-ai-writing detector scores 0% on lex-3 while its SKILL.md prose reads as if ~3 repeats matter. This threshold divergence is a finding, not a bug. Documented here so nobody "fixes" the drafts.

4. **Prose filter on human corpus.** Flattened HTML tables in MD&A sections would dilute flags/1k, so scoring uses `clean/` files (lines that are mostly numeric or heading fragments dropped, raw/ kept as provenance). Filter: scripts/clean_corpus.py.

5. **unslop invocation.** intensity=full (maximum deterministic rule coverage), structural=off, soul=off (those are rewrites, not detections). Voice profiles never touch the deterministic layer, so runs are voice-neutral without further steps.

6. **Recall matching is span-based, not attribution-based.** A plant counts as recalled if any rule fires on its span, even if the tool names it differently than the crosswalk expects. Crosswalk attribution is used for analysis, not for recall credit. Rationale: tools disagree on taxonomy; punishing naming differences would measure vocabulary, not detection.

7. **Whitelist addition.** "comprehensive income" added as its own term (ASC 220) after observing Tier 1 "comprehensive" firing on real KO and DE audit opinions. Whitelist status remains pending_review.

## REVIEW items for Rizwan

- **Whitelist final review** before publication (brief, open item). Note "materiality" is listed but bare "material"/"materially" are excluded from the starter set; they occur constantly in ordinary filing prose and would swamp the ToA metric. Confirmed 2026-07-24: leave them excluded.
- **Corpus gaps.** KO and DE MD&A extraction failed (unusual heading structure) and WMT/PG 10-Ks fell outside the submissions-API pagination window. Corpus is 18 docs / 111k clean words, comfortably above the 10-doc / 20k-word floor, so not blocking. Could be fixed for completeness.
- **PCAOB inspection reports** (PDFs) are in the brief's corpus spec but not yet fetched. The EDGAR material alone exceeds targets. Add later if wanted.

## Prompt track: completed 2026-07-25 (in-session subagent path)

All 192 detect-only passes done: 4 prompt tools x 18 human-corpus files (72), plus 4 prompt tools x 10 seeded drafts x 3 independent runs (120). Ran via a Workflow script spawning one Claude Code subagent per (tool, file) or (tool, draft, run), model pinned to `sonnet` (resolves to claude-sonnet-5), schema-forced structured output. Results ingested by `scripts/ingest_prompt_full_run.py` into the same raw_*.json schema the code-track runners produce, then scored by `scripts/score.py`.

**Fidelity caveat stands regardless of completeness**: this is the subagent path, not the raw-API path. Claude Code injects its own system prompt, so each tool's ruleset rode as agent task instructions rather than a literal system prompt. `runners/prompt_track/run_prompt_tool.py` remains the protocol-exact API harness for anyone who wants a fully canonical rerun (needs `ANTHROPIC_API_KEY`, `--approved` flag, roughly under $30 for the finance slice at claude-sonnet-5 pricing).

**Why this took four resume attempts**: the fan-out is expensive by volume, not by model tier — 192 full-document subagent passes, several against the largest corpus file (~20k words), repeatedly hit the Claude Max session usage cap before finishing. Each `Workflow(..., resumeFromRunId: "wf_9628a91e-89d")` call replayed already-completed jobs from cache for free and only retried what had failed, so nothing was wasted across attempts, but it took spanning a full overnight reset cycle (roughly 8:10pm -> 1:50am -> 9:20am -> 9:40pm Toronto resets) to clear the last ~65 jobs. Lesson for any future large fan-out like this: pass `effort: 'low'` on mechanical detect-and-quote agent calls — none of these calls needed deep reasoning, and the default inherited effort tier likely multiplied token cost substantially, especially on the large documents.

**Headline finding** (numbers corrected 2026-07-26 after the scoring-defect fixes below; the figures first published on 2026-07-25 were inflated): judgment-based prompt detection beats regex on this taxonomy. avoid-ai-writing's own SKILL.md read by an LLM scores 72.7% recall vs 46.7% for its own regex detector engine on the identical rule catalog, a 26.0-point gap concentrated in structural patterns regex cannot reach. stop-slop is the most aggressive tool on real filing text (6.9 flags/1k, highest ToA violation rate at 0.243/1k), mostly its adverb and passive-voice rules firing on mandated audit language.

Recall variance across the real N=3 runs was tight (widest spread: the-antislop at 43.4%-46.7%; stop-slop returned an identical 73/122 all three times), suggesting the prompt track is reasonably stable run-to-run on this task at this model tier.

**N asymmetry, disclosed**: the 192 passes give the seeded drafts N=3 but the human corpus N=1 per tool (72 passes = 4 tools x 18 files, single pass each). So prompt-track recall carries a spread and prompt-track flags/1k and ToA/1k do not. Nothing published is false, since spread is only shown for recall, but the human-corpus columns for the four prompt tools are single-run point estimates. Fix is either a disclosure line (done in README Limitations) or 144 more passes to bring the human corpus to N=3.

**Two scoring defects found and fixed 2026-07-26**, both surfaced by an adversarial multi-agent review of this repo (60 raw findings, 37 refuted, 23 survived). (1) Recall credited one finding to unlimited plants, and overlap was measured against the shorter span, so a paragraph-long quote scored a perfect match on every plant inside it; a synthetic tool quoting whole drafts scored 122/122. Now maximum bipartite matching, one plant per quoted finding, document-level rules exempt. Moved recall 0.8 to 8.5 points by tool and reordered two rows. (2) Term-of-art matching used plain substring, so "qualified opinion" matched inside "unqualified opinion"; now word-bounded, and index-less flags capped at min(flags, colliding occurrences). Lesson: I validated the scorer by checking whether its output looked plausible, never by attacking the matching mechanism. The whole-draft-quote test takes ten minutes to write and belonged in the repo before any number was published.

## Prompt-track design notes

- Uniform detect-only instruction appended to each tool's verbatim skill files; requests JSON `{rule, quote}` pairs. the-antislop's own "audit only" mode and no-ai-slop's detect mode align with this; stop-slop has no native detect mode, so the instruction does more work there.
- stop-slop needs all four files (SKILL.md + 3 references); no-ai-slop needs SKILL.md + eval.md. Confirmed against each repo's own instructions.
