# Seeded drafts: synthetic test fixtures, not real filings

**Every `.md` file in this directory is synthetic. Do not attribute any sentence in them to any company, auditor, officer, or filing.**

These are benchmark fixtures. Each draft starts from lightly adapted public-domain text from a real SEC filing, then has slop patterns planted into it by hand. The result deliberately mixes three kinds of sentence:

1. Real filing prose, adapted (public domain, source recorded per draft in [`manifest.json`](manifest.json) under `base_file`).
2. Real figures carried over from that filing.
3. **Invented sentences written solely to carry a planted pattern.** These are not statements any issuer made.

A reader cannot tell the three apart by looking, and that is intentional: the drafts have to read as plausible filing prose for the benchmark to measure anything. It also means these files are unsafe to quote.

## Concretely, what is fabricated

The invented material includes assertions that would be materially significant if they were real. For example:

- **`fin-06.md`** is framed as a memorandum to an audit committee and adapted from a Deere & Company opinion. Its internal-control conclusions, close-cycle metrics, and the statement that no material weakness existed are **invented**. Deere made no such statements in this form.
- **`fin-09.md`** mixes genuine Johnson & Johnson Credo language with an **invented** retention and productivity claim.
- **`fin-01.md`** carries Apple's real reported net sales figure alongside **invented** surrounding commentary.

The same applies to every other draft. Company names, filing dates, and auditor references appear because the base text came from real public filings, not because the surrounding assertions are real.

## Why this file exists

The methodology is documented in the repository [`README.md`](../../README.md) and every planted instance is recorded in [`manifest.json`](manifest.json). But a `.md` file rendered on its own, scraped, or indexed by a search engine carries none of that context. `corpora/` ships a `PROVENANCE.md` for exactly this reason; this is the equivalent for `seeded/`.

RegisterBench measures rules, not writers, and it makes no claim about who or what wrote any text. That principle cuts both ways: it also means the project should not leave fabricated corporate disclosure lying around unlabelled.

## What is real

- The base text provenance, per draft, in `manifest.json` (`base_file`), tracing to a real filing recorded in [`corpora/finance-audit/PROVENANCE.md`](../../corpora/finance-audit/PROVENANCE.md) with its accession number.
- The planted-instance ground truth: 122 entries with exact spans, canonical pattern IDs, tiers, and whether each was inserted or retained from the base text.
- The `distractors` blocks, which record real terms of art deliberately left in place and excluded from recall scoring.
