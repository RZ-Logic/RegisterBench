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

- **Whitelist final review** before publication (brief, open item). Note "materiality" is listed but bare "material"/"materially" are excluded from the starter set; they occur constantly in ordinary filing prose and would swamp the ToA metric. Decide whether to add them with occurrence-context matching.
- **Prompt-track billing path (resolved 2026-07-24).** The `--approved` gate exists because the harness hits api.anthropic.com with an API key, which bills a pay-as-you-go API account, separate from Rizwan's Claude subscription. Two paths: (a) canonical reproducible run needs an API key with credits, model claude-sonnet-5, roughly under $30 for the finance slice; (b) in-session subagent run is covered by the Claude membership at no extra cost but is a fidelity compromise (Claude Code injects its own system prompt, so each tool's SKILL.md rides as user-message content rather than the literal system prompt, and third-party reproduction requires Claude Code). Recommendation: (a) for published numbers, (b) acceptable for a preview. Model pin updated from the brief's claude-sonnet-4-6 to claude-sonnet-5.
- **Corpus gaps.** KO and DE MD&A extraction failed (unusual heading structure) and WMT/PG 10-Ks fell outside the submissions-API pagination window. Corpus is 18 docs / 111k clean words, comfortably above the 10-doc / 20k-word floor, so not blocking. Could be fixed for completeness.
- **PCAOB inspection reports** (PDFs) are in the brief's corpus spec but not yet fetched. The EDGAR material alone exceeds targets. Add later if wanted.

## Prompt-track design notes (for when budget is approved)

- Uniform detect-only instruction appended to each tool's verbatim skill files; requests JSON `{rule, quote}` pairs. the-antislop's own "audit only" mode and no-ai-slop's detect mode align with this; stop-slop has no native detect mode, so the instruction does more work there (worth a line in the results writeup).
- stop-slop needs all four files (SKILL.md + 3 references); no-ai-slop needs SKILL.md + eval.md. Confirmed against each repo's own instructions.
