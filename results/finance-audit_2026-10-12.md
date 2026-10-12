# RegisterBench results: finance-audit (2026-10-12)

RegisterBench measures rules, not writers. It never claims or implies AI
authorship of any text. A flag on human text is not automatically wrong
as style advice; the claim under test is that these rules remove AI
tells, and rule fire density on verifiably pre-ChatGPT text is evidence
of style preference rather than AI signal. Readers judge the rows.

Recall assigns each quoted finding to at most one planted instance
(maximum bipartite matching). Document-level rules are exempt, because
one such flag legitimately covers every plant of its pattern. Tier and
pattern breakdowns are means across all runs, matching the headline.

| tool | sha | runs (seeded/human) | recall (mean) | recall (min-max) | flags/1k human | ToA violations/1k |
|---|---|---|---|---|---|---|
| avoid-ai-writing-detector | 27156c7a | 1/1 | 46.7% | deterministic | 1.09 | 0.144 |
| avoid-ai-writing-skill | 27156c7a | 3/3 | 74.9% | 73.8%-75.4% | 0.39 (0.23-0.57) | 0 (0-0) |
| no-ai-slop | 61c21c35 | 3/3 | 62.6% | 61.5%-63.1% | 0.09 (0.04-0.15) | 0 (0-0) |
| stop-slop | 8da1f030 | 3/3 | 64.2% | 63.1%-65.6% | 0.31 (0.27-0.4) | 0 (0-0) |
| the-antislop | 5edbf856 | 3/3 | 57.4% | 53.3%-59.8% | 0.35 (0.17-0.46) | 0 (0-0) |
| unslop-deterministic | 5af59d9f | 1/1 | 28.7% | deterministic | 2.06 | 0.341 |

## Recall on claimed patterns only

Same matches, restricted to plants whose canonical pattern the tool's
crosswalk row claims. Full-taxonomy recall measures coverage of the
canonical taxonomy; this measures accuracy on what each tool attempts.

| tool | patterns claimed | plants claimed | full-taxonomy recall | claimed-only recall | claimed-only min-max |
|---|---|---|---|---|---|
| avoid-ai-writing-detector | 20/29 | 99/122 | 46.7% | 56.6% | deterministic |
| avoid-ai-writing-skill | 28/29 | 120/122 | 74.9% | 75.3% | 74.2%-75.8% |
| no-ai-slop | 21/29 | 89/122 | 62.6% | 76.4% | 74.2%-78.6% |
| stop-slop | 17/29 | 81/122 | 64.2% | 68.7% | 64.2%-71.6% |
| the-antislop | 22/29 | 94/122 | 57.4% | 64.9% | 58.5%-68.1% |
| unslop-deterministic | 18/29 | 92/122 | 28.7% | 37.0% | deterministic |

## Weighting sensitivity

Recall recomputed from the per-tier means under alternative tier
weightings. Tier sizes mirror how the drafts were written, so a
conclusion is only robust if it survives every column.

| tool | plant-weighted (published) | equal weight per tier | lexical tiers only | phrasal + structural only |
|---|---|---|---|---|
| avoid-ai-writing-detector | 46.7% | 40.1% | 46.8% | 46.5% |
| avoid-ai-writing-skill | 74.9% | 69.8% | 59.6% | 83.6% |
| no-ai-slop | 62.6% | 54.5% | 51.8% | 70.9% |
| stop-slop | 64.2% | 57.5% | 41.8% | 78.9% |
| the-antislop | 57.4% | 50.2% | 30.5% | 74.2% |
| unslop-deterministic | 28.7% | 27.7% | 29.8% | 26.8% |
| **skill minus detector (points)** | **28.1** | **29.7** | **12.8** | **37.1** |

## Term-of-art violations under two matching rules

Headline rule is flag-anchored: protected-term text must be at least half
of the flagged span. Containment counts any flag that encloses a term,
however wide the quote, which penalises tools that quote whole clauses.
Rates are per 1,000 words; the by-type columns use that type's words.
With N runs a cell reads mean (min-max).

| tool | anchored /1k | containment /1k | anchored, opinions /1k | anchored, MD&A /1k | distinct (document, term) pairs |
|---|---|---|---|---|---|
| avoid-ai-writing-detector | 0.144 | 0.144 | 0.554 | 0.064 | 14 |
| avoid-ai-writing-skill | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) |
| no-ai-slop | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) |
| stop-slop | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) | 0 (0-0) |
| the-antislop | 0 (0-0) | 0.003 (0-0.009) | 0 (0-0) | 0 (0-0) | 0 (0-0) |
| unslop-deterministic | 0.341 | 0.341 | 0.996 | 0.214 | 14 |

## Quotes that do not occur in the source text

Findings whose quoted text appears nowhere in the document they were
reported against (exact, then case-insensitive search). They are counted
here, excluded from flags/1k, and never credited to a planted instance.
Totals across all runs.

| tool | human corpus: unlocated / reported | seeded drafts: unlocated / reported |
|---|---|---|
| avoid-ai-writing-detector | 0 / 121 | 0 / 68 |
| avoid-ai-writing-skill | 1 / 130 | 0 / 308 |
| no-ai-slop | 1 / 32 | 0 / 254 |
| stop-slop | 7 / 112 | 1 / 400 |
| the-antislop | 2 / 119 | 0 / 243 |
| unslop-deterministic | 0 / 229 | 0 / 39 |

## avoid-ai-writing-detector: recall by tier (single deterministic run)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 2/4 | 50.0% | n/a |
| lex-1 | 20/23 | 87.0% | n/a |
| lex-2 | 2/12 | 16.7% | n/a |
| lex-3 | 0/12 | 0.0% | n/a |
| phrasal | 25/42 | 59.5% | n/a |
| structural | 8/29 | 27.6% | n/a |

## avoid-ai-writing-skill: recall by tier (mean of 3 runs)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 4/4 | 100.0% | 4-4 |
| lex-1 | 20.33/23 | 88.4% | 20-21 |
| lex-2 | 4.33/12 | 36.1% | 3-6 |
| lex-3 | 3.33/12 | 27.8% | 2-5 |
| phrasal | 35.67/42 | 84.9% | 34-37 |
| structural | 23.67/29 | 81.6% | 23-24 |

## no-ai-slop: recall by tier (mean of 3 runs)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 1.67/4 | 41.7% | 1-2 |
| lex-1 | 15/23 | 65.2% | 14-16 |
| lex-2 | 7/12 | 58.3% | 6-8 |
| lex-3 | 2.33/12 | 19.4% | 2-3 |
| phrasal | 29/42 | 69.0% | 29-29 |
| structural | 21.33/29 | 73.6% | 20-22 |

## stop-slop: recall by tier (mean of 3 runs)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 2.67/4 | 66.7% | 2-3 |
| lex-1 | 11.67/23 | 50.7% | 11-12 |
| lex-2 | 2.33/12 | 19.4% | 1-4 |
| lex-3 | 5.67/12 | 47.2% | 5-6 |
| phrasal | 30.33/42 | 72.2% | 30-31 |
| structural | 25.67/29 | 88.5% | 25-26 |

## the-antislop: recall by tier (mean of 3 runs)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 3/4 | 75.0% | 3-3 |
| lex-1 | 10/23 | 43.5% | 9-12 |
| lex-2 | 1.67/12 | 13.9% | 1-3 |
| lex-3 | 2.67/12 | 22.2% | 1-4 |
| phrasal | 32.67/42 | 77.8% | 32-33 |
| structural | 20/29 | 69.0% | 17-22 |

## unslop-deterministic: recall by tier (single deterministic run)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 2/4 | 50.0% | n/a |
| lex-1 | 12/23 | 52.2% | n/a |
| lex-2 | 2/12 | 16.7% | n/a |
| lex-3 | 0/12 | 0.0% | n/a |
| phrasal | 17/42 | 40.5% | n/a |
| structural | 2/29 | 6.9% | n/a |

