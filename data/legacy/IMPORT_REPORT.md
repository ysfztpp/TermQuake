# Import report: Google Sheet snapshot -> database

Written by `termquake import-sheet`. The data was imported exactly as typed in
the sheet; nothing was split, corrected or trimmed. This report lists what was
left out and what the team may want to look at.

- Entries: 523
- Terms (one per filled cell): 12415 in 30 languages
  (en 520, tr 523, es 459, de 419, ru 522, fr 406, kmr 464, zza 286, ar 473, el 414, ja 464, he 464, it 477, hy 464, nl 375, zh-Hans 464, zh-Hant 464, bg 221, ko 465, fa 519, hi 464, pt 323, sv 413, ro 464, sr 143, mk 459, hu 459, fi 342, cs 152, pl 333)
- Definitions: 14

## Left out

| Where | Language | Why |
|---|---|---|
| entry 257 | fr | placeholder '#N/A' |
| entry 266 | fr | placeholder '#N/A' |
| entry 470 | en | placeholder '#empty3' |
| entry 470 | fa | placeholder '#خالی3' |
| entry 482 | en | placeholder '#empty1' |
| entry 482 | fa | placeholder '#خالی1' |
| entry 486 | en | placeholder '#empty2' |
| entry 486 | fa | placeholder '#خالی2' |

## Kept as typed, worth a look

- **Several terms in one cell, separated by ' / '** (1388): see queries/ to list them
- **Space at the start or end of the cell** (609): see queries/ to list them
- **Spreadsheet code for a control character (e.g. _x0002_)** (1): entry 211 (ko)
- **Invisible character in the cell** (1): entry 245 (sv)
- **Letter i written as i + combining dot (looks like i̇)** (6): entry 403 (tr), entry 404 (tr), entry 405 (tr), entry 406 (tr), entry 407 (tr), entry 408 (tr)
- **Entry without a domain** (8): entry 465, entry 468, entry 469, entry 478, entry 482, entry 483, entry 484, entry 485
