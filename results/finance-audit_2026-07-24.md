# slopbench results: finance-audit (2026-07-24)

slopbench measures rules, not writers. It never claims or implies AI
authorship of any text. A flag on human text is not automatically wrong
as style advice; the claim under test is that these rules remove AI
tells, and rule fire density on verifiably pre-ChatGPT text is evidence
of style preference rather than AI signal. Readers judge the rows.

| tool | sha | recall (mean) | recall (min-max) | flags/1k human | ToA violations/1k |
|---|---|---|---|---|---|
| avoid-ai-writing-detector | 27156c7a | 46.7% | 46.7%-46.7% | 0.51 | 0.081 |
| unslop-deterministic | 5af59d9f | 28.7% | 28.7%-28.7% | 2.06 | 0.189 |

## avoid-ai-writing-detector: recall by tier

| tier | matched/planted | recall |
|---|---|---|
| conversational | 2/4 | 50.0% |
| lex-1 | 20/23 | 87.0% |
| lex-2 | 2/12 | 16.7% |
| lex-3 | 0/12 | 0.0% |
| phrasal | 25/42 | 59.5% |
| structural | 8/29 | 27.6% |

## unslop-deterministic: recall by tier

| tier | matched/planted | recall |
|---|---|---|
| conversational | 2/4 | 50.0% |
| lex-1 | 12/23 | 52.2% |
| lex-2 | 2/12 | 16.7% |
| lex-3 | 0/12 | 0.0% |
| phrasal | 17/42 | 40.5% |
| structural | 2/29 | 6.9% |

