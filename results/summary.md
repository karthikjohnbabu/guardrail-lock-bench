## Set A: harmless questions that sound risky

| Rung | Lock | Risky-sounding wrongly stopped | Of those: model refused / filter blocked / to check | Plain controls wrongly stopped | Avg seconds per answer |
| --- | --- | --- | --- | --- | --- |
| A1 | Llama alone (lock in the weights) | 2% (2 of 100; per run 0 to 5%) | 2 / 0 / 0 | 0% (0 of 100) | 2.7 |
| A2 | Llama + permissive system prompt | 5% (5 of 100; per run 5 to 5%) | 5 / 0 / 0 | 0% (0 of 100) | 3.2 |
| A3 | Qwen uncensored (no lock) | 0% (0 of 100; per run 0 to 0%) | 0 / 0 / 0 | 0% (0 of 100) | 9.2 |
| A4 | Llama + Llama Guard filter | 21% (21 of 100; per run 15 to 25%) | 2 / 19 / 0 | 0% (0 of 100) | 2.3 |

## Set B: the secret-word game

| Rung | Lock | Secret reached the user | Model leaked before any filter | Normal questions wrongly stopped | Avg seconds per answer |
| --- | --- | --- | --- | --- | --- |
| B1 | Llama + secret-word prompt (text lock) | 45% (18 of 40; per run 25 to 62%) | 45% | 25% (5 of 20) | 0.4 |
| B2 | Qwen uncensored + text lock | 50% (20 of 40; per run 38 to 62%) | 50% | 0% (0 of 20) | 0.9 |
| B3 | Llama + text lock + code filter | 7.5% (3 of 40; per run 0 to 12%) | 45% | 15% (3 of 20) | 0.4 |

Automatic labels plus corrections from reading the answers by hand (hand_read.csv). Per-run ranges show the spread across the repeated runs. Borderline cases not counted: B1 1, B2 1, B3 1.
