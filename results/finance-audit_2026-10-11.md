# RegisterBench results: finance-audit (2026-10-11)

RegisterBench measures rules, not writers. It never claims or implies AI
authorship of any text. A flag on human text is not automatically wrong
as style advice; the claim under test is that these rules remove AI
tells, and rule fire density on verifiably pre-ChatGPT text is evidence
of style preference rather than AI signal. Readers judge the rows.

Recall assigns each quoted finding to at most one planted instance
(maximum bipartite matching). Document-level rules are exempt, because
one such flag legitimately covers every plant of its pattern. Tier and
pattern breakdowns are means across all runs, matching the headline.

| tool | sha | runs | recall (mean) | recall (min-max) | flags/1k human | ToA violations/1k |
|---|---|---|---|---|---|---|
| avoid-ai-writing-detector | 27156c7a | 1 | 46.7% | deterministic | 1.09 | 0.144 |
| avoid-ai-writing-skill | 27156c7a | 3 | 72.7% | 71.3%-73.8% | 1.34 | 0.009 |
| no-ai-slop | 61c21c35 | 3 | 55.5% | 54.1%-56.6% | 0.55 | 0.0 |
| stop-slop | 8da1f030 | 3 | 59.8% | 59.8%-59.8% | 6.9 | 0.072 |
| the-antislop | 5edbf856 | 3 | 45.4% | 43.4%-46.7% | 0.7 | 0.0 |
| unslop-deterministic | 5af59d9f | 1 | 28.7% | deterministic | 2.06 | 0.341 |

## Recall on claimed patterns only

Same matches, restricted to plants whose canonical pattern the tool's
crosswalk row claims. Full-taxonomy recall measures coverage of the
canonical taxonomy; this measures accuracy on what each tool attempts.

| tool | patterns claimed | plants claimed | full-taxonomy recall | claimed-only recall | claimed-only min-max |
|---|---|---|---|---|---|
| avoid-ai-writing-detector | 20/29 | 99/122 | 46.7% | 56.6% | deterministic |
| avoid-ai-writing-skill | 28/29 | 120/122 | 72.7% | 73.1% | 71.7%-74.2% |
| no-ai-slop | 21/29 | 89/122 | 55.5% | 69.3% | 68.5%-69.7% |
| stop-slop | 17/29 | 81/122 | 59.8% | 63.4% | 61.7%-65.4% |
| the-antislop | 22/29 | 94/122 | 45.4% | 54.3% | 52.1%-56.4% |
| unslop-deterministic | 18/29 | 92/122 | 28.7% | 37.0% | deterministic |

## Weighting sensitivity

Recall recomputed from the per-tier means under alternative tier
weightings. Tier sizes mirror how the drafts were written, so a
conclusion is only robust if it survives every column.

| tool | plant-weighted (published) | equal weight per tier | lexical tiers only | phrasal + structural only |
|---|---|---|---|---|
| avoid-ai-writing-detector | 46.7% | 40.1% | 46.8% | 46.5% |
| avoid-ai-writing-skill | 72.7% | 63.2% | 57.5% | 82.6% |
| no-ai-slop | 55.5% | 43.5% | 44.7% | 65.3% |
| stop-slop | 59.8% | 52.4% | 37.6% | 75.1% |
| the-antislop | 45.4% | 40.9% | 21.3% | 59.6% |
| unslop-deterministic | 28.7% | 27.7% | 29.8% | 26.8% |
| **skill minus detector (points)** | **26.0** | **23.1** | **10.6** | **36.2** |

## Term-of-art violations under two matching rules

Headline rule is flag-anchored: protected-term text must be at least half
of the flagged span. Containment counts any flag that encloses a term,
however wide the quote, which penalises tools that quote whole clauses.
Rates are per 1,000 words; the by-type columns use that type's words.

| tool | anchored /1k | containment /1k | anchored, opinions /1k | anchored, MD&A /1k | distinct (document, term) pairs |
|---|---|---|---|---|---|
| avoid-ai-writing-detector | 0.144 | 0.144 | 0.554 | 0.064 | 14 |
| avoid-ai-writing-skill | 0.009 | 0.009 | 0.055 | 0.0 | 1 |
| no-ai-slop | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| stop-slop | 0.072 | 0.252 | 0.443 | 0.0 | 8 |
| the-antislop | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| unslop-deterministic | 0.341 | 0.341 | 0.996 | 0.214 | 14 |

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
| conversational | 3/4 | 75.0% | 3-3 |
| lex-1 | 21.67/23 | 94.2% | 21-22 |
| lex-2 | 5/12 | 41.7% | 5-5 |
| lex-3 | 0.33/12 | 2.8% | 0-1 |
| phrasal | 34.33/42 | 81.7% | 33-35 |
| structural | 24.33/29 | 83.9% | 24-25 |

## no-ai-slop: recall by tier (mean of 3 runs)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 0.33/4 | 8.3% | 0-1 |
| lex-1 | 13.67/23 | 59.4% | 13-14 |
| lex-2 | 5.67/12 | 47.2% | 5-7 |
| lex-3 | 1.67/12 | 13.9% | 1-2 |
| phrasal | 25.67/42 | 61.1% | 25-26 |
| structural | 20.67/29 | 71.3% | 19-22 |

## stop-slop: recall by tier (mean of 3 runs)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 2/4 | 50.0% | 1-3 |
| lex-1 | 9/23 | 39.1% | 8-10 |
| lex-2 | 3/12 | 25.0% | 1-5 |
| lex-3 | 5.67/12 | 47.2% | 5-6 |
| phrasal | 29/42 | 69.0% | 28-30 |
| structural | 24.33/29 | 83.9% | 23-25 |

## the-antislop: recall by tier (mean of 3 runs)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 3/4 | 75.0% | 3-3 |
| lex-1 | 8.67/23 | 37.7% | 8-9 |
| lex-2 | 0/12 | 0.0% | 0-0 |
| lex-3 | 1.33/12 | 11.1% | 1-2 |
| phrasal | 23/42 | 54.8% | 23-23 |
| structural | 19.33/29 | 66.7% | 18-20 |

## unslop-deterministic: recall by tier (single deterministic run)

| tier | matched/planted | recall | matched min-max |
|---|---|---|---|
| conversational | 2/4 | 50.0% | n/a |
| lex-1 | 12/23 | 52.2% | n/a |
| lex-2 | 2/12 | 16.7% | n/a |
| lex-3 | 0/12 | 0.0% | n/a |
| phrasal | 17/42 | 40.5% | n/a |
| structural | 2/29 | 6.9% | n/a |

