# RegisterBench results: finance-audit (2026-07-26)

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
| avoid-ai-writing-detector | 27156c7a | 1 | 46.7% | deterministic | 0.51 | 0.081 |
| avoid-ai-writing-skill | 27156c7a | 3 | 72.7% | 71.3%-73.8% | 1.34 | 0.009 |
| no-ai-slop | 61c21c35 | 3 | 55.5% | 54.1%-56.6% | 0.55 | 0.0 |
| stop-slop | 8da1f030 | 3 | 59.8% | 59.8%-59.8% | 6.9 | 0.243 |
| the-antislop | 5edbf856 | 3 | 45.4% | 43.4%-46.7% | 0.7 | 0.0 |
| unslop-deterministic | 5af59d9f | 1 | 28.7% | deterministic | 2.06 | 0.171 |

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
| phrasal | 34.33/42 | 81.8% | 33-35 |
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

