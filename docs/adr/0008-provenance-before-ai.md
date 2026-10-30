# 0008. Provenance and review status before any AI-generated content

**Status:** deferred by [0010](0010-four-tables-raw-data.md): the provenance and review columns are added back before any AI-generated content enters the database.

## Context
The next step is filling gaps and standardising entries with machine
translation and LLMs. The article argues that crisis terminology needs human
verification for accuracy and trust, and that AI output must never pass as
expert-validated.

## Decision
Every term and definition carries `origin` (`legacy_import`, `human`, `mt`,
`llm`), `origin_detail` (model, prompt version) and `review_status`
(`unreviewed`, `proposed`, `approved`, `rejected`). AI output enters as
`proposed` and is published only after approval through the voting rule
(`review_vote`, score ≥ +2).

## Consequences
- AI can do bulk drafting safely; experts review instead of typing.
- The provenance is exportable, so a release can state exactly how much of
  each language is human-verified.
