# 0004. Conservative, lossless import with a QA worklist

**Status:** superseded by [0010](0010-four-tables-raw-data.md), 30 October 2026: the data is now imported exactly as typed.

## Context
An audit of the sheet found the legend's symbols used inconsistently: "/" for
synonyms, gender endings and two concepts in one cell; "-" for acronyms and
derivations; "()" for acronyms, optional words, disambiguators and
explanations. It also found placeholder cells (#empty), duplicate entries,
invisible characters and broken Turkish dotted-i.

## Decision
Split only the unambiguous case (a "/" with a space on at least one side,
never in expressions). Keep everything else verbatim and record a `qa_issue`
with a severity. Repair only pure encoding damage automatically. Keep every
original cell (as committed CSV in `data/legacy/`; an earlier draft used an
`import_raw` table). Publish the findings as `data/QA_REPORT.md`, by entry
number.

## Consequences
- Nothing a volunteer wrote is silently lost or reinterpreted.
- Some terms on the site still contain brackets or dashes until the
  standardisation step resolves them, with review.
- The QA report doubles as the team's worklist and progress measure.
