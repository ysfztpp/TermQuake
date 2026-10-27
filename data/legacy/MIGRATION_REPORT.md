# Migration report: legacy Google Sheet -> SQL database

Written once by `termquake migrate`. Lists what the legacy sheet contained that
could not be imported as-is. Content questions (ambiguous separators, duplicates,
missing translations) are tracked in data/QA_REPORT.md instead.

- Entries imported: 523
- Terms imported: 14004 (ar 492, bg 244, cs 158, de 489, el 445, en 594, es 572, fa 573, fi 355, fr 447, he 545, hi 577, hu 524, hy 561, it 618, ja 469, kmr 476, ko 536, mk 511, nl 410, pl 357, pt 364, ro 519, ru 637, sr-Cyrl 144, sv 453, tr 575, zh-Hans 547, zh-Hant 513, zza 299)
- Definitions imported: 14

| Where | Language | Finding |
|---|---|---|
| entry 9 | ko | info: duplicate_in_cell: 의료지원 |
| entry 245 | sv | info: removed_invisible_chars: stödkonstruktion |
| entry 257 | fr | error: placeholder_value: cell contains '#N/A'; ignored |
| entry 266 | fr | error: placeholder_value: cell contains '#N/A'; ignored |
| entry 403 | tr | info: fixed_dotted_i: iç organlar |
| entry 404 | tr | info: fixed_dotted_i: iltihap / inflamasyon |
| entry 405 | tr | info: fixed_dotted_i: inme |
| entry 406 | tr | info: fixed_dotted_i: insülin iğnesi |
| entry 407 | tr | info: fixed_dotted_i: ishal |
| entry 408 | tr | info: fixed_dotted_i: iskemi |
| entry 470 | en | error: placeholder_value: cell contains '#empty3'; ignored |
| entry 482 | en | error: placeholder_value: cell contains '#empty1'; ignored |
| entry 486 | en | error: placeholder_value: cell contains '#empty2'; ignored |
