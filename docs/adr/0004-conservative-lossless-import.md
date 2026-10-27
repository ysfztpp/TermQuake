# 0004. Conservative, lossless import with a QA worklist

**Status:** accepted, October 2026

## Context
An audit of the sheet found the legend's symbols used inconsistently: "/" for
synonyms, gender endings and two concepts in one cell; "-" for acronyms and
derivations; "()" for acronyms, optional words, disambiguators and
explanations. It also found placeholder cells (#empty), duplicate entries,
invisible characters and broken Turkish dotted-i.

## Decision
Split only the unambiguous case (a "/" with a space on at least one side,
never in expressions). Keep everything else verbatim and record a `qa_issue`
with a severity. Repair only pure encoding damage automatically. Store every
original cell in `import_raw`. Publish the findings as
`data/export/QA_REPORT.md`, by entry number.

## Consequences
- Nothing a volunteer wrote is silently lost or reinterpreted.
- Some terms on the site still contain brackets or dashes until the
  standardisation step resolves them, with review.
- The QA report doubles as the team's worklist and progress measure.
