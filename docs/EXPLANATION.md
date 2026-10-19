# Explanation

Search this file for `FILL:` before submitting. Those few spots need facts only I (the author) know.

## Disclosure
- Built with help from Claude (Anthropic). I reviewed the code and ran the checks listed below. FILL: one line on what you wrote or changed yourself.
- Time spent: FILL: hours.
- Splitter check: a plain `.`/`!`/`?` splitter reproduces all 376 development gold boundaries. That was observed on the development set before v2 was written, so v2's design was informed by development gold boundaries. No final-check labels exist to me.
- Final-check inputs are visible. FILL: "I did not tune either version on them." (or describe what you did). This is not a fully blind benchmark.
- Provider: Gemini free tier. Google may use free-tier inputs for model improvement; the dataset is fictional. FILL: "I used one key for all runs." (or describe any key switch).
- The CSVs are not committed. Their SHA-256 hashes are in `data/HASHES.txt`. The repository is private; the reviewers have the CSVs and can place them in `data/`.
- The v1 report records revision `2d4e8cda...`. I reset the git history afterwards (to remove the CSVs), so that hash no longer exists. v1 ran on the same code as the current commit unless noted otherwise. The v2 report records revision `0c78877`, which is in the repository.

## Fixed across v1 and v2
Provider Gemini (free tier), model `gemini-3.5-flash-lite`, temperature model default, `max_output_tokens` 8192, provider timeout 90 s, 6.5 s minimum between requests, 3 retries on HTTP 429, max 3 turns, same CSVs and scorer. Both v1 and v2 include a one-turn repair retry when the model's JSON fails validation. It was added after a smoke-test failure and is shared infrastructure, not the v1-to-v2 change. Runs are not bit-for-bit deterministic, so differences smaller than run-to-run noise should not be over-claimed.

## v1 baseline (free-quote extraction): development results
G=376 P=344 M=344 C=336 | joint F1 0.933 (P 0.977, R 0.894) | extraction F1 0.956 (P 1.000, R 0.915) | answer errors 1 (A19, invalid JSON) | missed 32 | unmatched 0 | wrong labels 8

## Failure investigated (from `runs/v1_development.md`)
- 32 gold claims were missed (extraction recall 0.915), led by policy_scope (6), price_vs_shipping (4), inference (4) and negation (3).
- A19 failed with `invalid_output: final response is not valid JSON`, even after the repair retry. All of A19's gold claims count as missed.
- 8 matched claims had the wrong label (unit_conversion 5, comparison 3, arithmetic 3), mostly contradicted predicted as supported (5).
- v1 had 0 unmatched predictions and extraction precision 1.000, so span boundaries were not the problem.

## The one change in v2
v2 (`v2-sentence-index`): Python segments the answer into sentences, and the model selects sentence indices instead of reproducing free-text quotes. The aim was to remove the model's dependence on reproducing exact long quotes (a possible source of the A19 failure and of recall gaps) and to make it decide on every sentence. The labeling instructions were not meant to change.

## Results v1 to v2 (development, identical inputs and scoring)

| metric | v1 | v2 | delta |
|---|---|---|---|
| Joint F1 | 0.933 | 0.876 | -0.057 |
| Joint precision | 0.977 | 0.931 | -0.046 |
| Joint recall | 0.894 | 0.827 | -0.066 |
| Extraction F1 | 0.956 | 0.938 | -0.018 |
| G / P / M / C | 376 / 344 / 344 / 336 | 376 / 334 / 333 / 311 | |
| Missed gold claims | 32 | 43 | +11 |
| Matched wrong-label | 8 | 22 | +14 |
| Unmatched predictions | 0 | 1 (A18:2173:2236) | +1 |
| Answer errors | 1 (A19) | 0 | -1 |

- Of the claims correct in v1, 51 were no longer correct in v2; 26 became correct in v2, 9 of them in A19, where v1 produced no output. On like-for-like answers v2 improved 17 claims and regressed 51.
- v2 fixed the A19 failure, but it is a regression overall: more misses (largest increases in missing_fact, inference and feature_conflation) and more wrong labels (arithmetic 3 to 9, comparison 3 to 7, plus new condition_scope, date_scope and historical_scope errors). Contradicted-to-supported errors rose from 5 to 11, and 4 unknown-to-contradicted errors are new.
- The same claim wordings (for example the "one hundred metres" Bluetooth claim and the free-delivery claim) appear in both the improved and regressed lists for different answers. So run-to-run variance at the default temperature probably explains part of the difference. I did not rerun either version to measure it, so I cannot say how much. The net result is still worse for v2, and I report it as a regression, not as a win.
- I did not retune v2 against the development set after seeing these results.

## Check runs (A41 to A50)
Both versions were run on the 10 final-check answers with the frozen code (git tag `frozen-v1-v2`). Quality metrics are null because I have no labels. v1 check: 10 of 10 answers ok, 0 errors, 90 accepted predictions. v2 check: 10 of 10 answers ok, 0 errors, 82 accepted predictions. Both ran on revision d8f01c7. v2 accepted 8 fewer claims than v1, similar to the development pattern, but without labels I cannot say which is better.

## Tests actually run (not just written)
- `pytest -q -rs`: 77 passed, 3 skipped, 1 warning (httpx deprecation in Starlette's TestClient). The 3 skipped tests are the PostgreSQL persistence tests in tests/test_api_db.py, skipped because TEST_DATABASE_URL was not set. I tried to install PostgreSQL locally (winget download failed with HTTP 403), so they were not run against a real PostgreSQL. Output is in runs/test_output.txt.
- Fake-provider tests do not replace the live runs.

## Unfinished / limitations
- v2 is a regression and I did not iterate on it (time limit).
- I did not isolate why labeling got worse, even though the change targeted extraction; part of it may be run-to-run variance.
- One run per version at the default temperature; no variance measurement.
- No Langfuse, no concurrency, no React (all optional).
- FILL: anything else not done (for example the API or database paths not exercised against a real PostgreSQL).