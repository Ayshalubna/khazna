# Khazna — evaluation results

127 questions with known answers over 21 fictional company documents (English and Arabic). Reproduce with `python -m eval.run_eval`.

## Retrieval (does the right passage come back?)

| Method | Hit@1 | Hit@5 | MRR | Cross-language Hit@1 |
|---|---|---|---|---|
| bm25 | 94% | 100% | 0.97 | 80% |
| dense | 90% | 100% | 0.94 | 80% |
| hybrid | 91% | 100% | 0.95 | 80% |

Answerable questions: 87. On a library this small keyword search is already as strong as the hybrid; cross-language matching comes mainly from the Arabic↔English glossary. Permission filtering happens inside the search, so restricted passages are never candidates.

## Answers — built-in mode (no model; quotes the source sentence)

| | Result |
|---|---|
| Correct answers (English, Arabic, cross-language, versions) | **91%** of 87 |
| English / Arabic facts | 92% / 80% |
| Arabic question → English document and back | 100% |
| Current version preferred over the 2024 handbook | 67% |
| "Not in the documents" questions refused | **85%** of 20 |
| Questions about documents the role cannot see, refused | 91% of 11 (the rest answered from permitted documents only) |
| Median / p95 latency | 10 ms / 15 ms |

## Leaks (must all be zero)

38 forbidden strings are checked in every answer **and** every passage shown.

| | Leaks |
|---|---|
| Restricted documents (salary bands, board minutes, contract...) | **0** |
| Personal identifiers (Emirates ID, IBAN, personal mobile) | **0** |
| Planted prompt injection ("ignore all previous instructions...") | **0** |
| Outdated 2024 handbook values | **0** |
