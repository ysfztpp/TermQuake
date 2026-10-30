# Import report: Google Sheet snapshot -> database

Written by `termquake import-sheet`. The data was imported exactly as typed in
the sheet; nothing was split, corrected or trimmed. This report lists what was
left out and what the team may want to look at.

- Entries: 523
- Terms (one per filled cell): 1502 (en 520, tr 523, es 459)
- Definitions: 14

## Left out

| Where | Language | Why |
|---|---|---|
| entry 470 | en | placeholder '#empty3' |
| entry 482 | en | placeholder '#empty1' |
| entry 486 | en | placeholder '#empty2' |

## Kept as typed, worth a look

- **Space at the start or end of the cell** (62): see queries/ to list them
- **Several terms in one cell, separated by ' / '** (223): see queries/ to list them
- **Letter i written as i + combining dot (looks like i̇)** (6): entry 403 (tr), entry 404 (tr), entry 405 (tr), entry 406 (tr), entry 407 (tr), entry 408 (tr)
- **Entry without a domain** (8): entry 465, entry 468, entry 469, entry 478, entry 482, entry 483, entry 484, entry 485
