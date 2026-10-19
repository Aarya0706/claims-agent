# Explanation

## Disclosure

- **AI assistance and my contribution:** Claude (Anthropic) generated the initial scaffold for the agent, scorer, API and tests, and assisted with result analysis. My work included running all four live evaluation runs, inspecting the error reports, comparing v1 and v2, reviewing the test output, checking the reported metrics against the saved JSON artifacts, and documenting the results and limitations. I reviewed the implementation and the checks reported below.

- **Time spent:** Approximately 2.5 hours, including implementation, live evaluation runs, testing and documentation.

- **Development-set boundary check:** A simple sentence splitter based on `.`, `!` and `?` reproduced all 376 development gold boundaries. I observed this on the development set before designing v2, so the v2 design was informed by the development-set boundary analysis. The final-check labels were not available to me.

- **Final-check disclosure:** The inputs for the final-check answers are visible. I did not tune either version on them. Therefore, these runs should not be described as a fully blind benchmark.

- **Provider and data privacy:** I used the Gemini free tier and one API key across all four runs. The dataset contains fictional product information. Google may use free-tier inputs for model improvement, as noted in the assessment documentation. No API keys or `.env` values are included in the repository.

- **Dataset availability:** The CSV files are not committed to the repository. Their SHA-256 hashes are recorded in `data/HASHES.txt`. The repository is public for review, and the assessment datasets must be supplied separately and placed in `data/` before running the complete evaluation.

- **Source revision and reproducibility:** The v1 report records revision `2d4e8cda...`, which no longer exists in the visible Git history because I reset the history to remove the CSVs. The v1 run was executed from a working tree with uncommitted changes on top of that revision, including changes to `claims/agent.py`, `claims/runner.py` and `scripts/run_eval.py`. These included the one-turn repair retry added after a smoke-test failure. File modification times indicate that no source file under `claims/` or `scripts/` was modified after the v1 run began; however, I did not rerun v1 against the final commit, so exact source-revision reproducibility is not fully proven. The v2 report records revision `0c78877`. Both check runs record revision `d8f01c7` and were run with the `frozen-v1-v2` tag. A later commit added the check reports, test output and documentation.

## Fixed Across v1 and v2

Both versions used the Gemini provider, model `gemini-3.5-flash-lite`, the model's default temperature, `max_output_tokens=8192`, a 90-second provider-request timeout, a 6.5-second minimum interval between requests, three retries on HTTP 429, and a maximum of three model turns per answer. Both versions used the same CSV inputs and scorer.

Both versions also shared a one-turn repair retry for invalid JSON or output that failed validation. This was added after a smoke-test failure and was shared infrastructure, not the v1-to-v2 change.

The model's default temperature means the runs are not guaranteed to be bit-for-bit deterministic. Since only one development run was performed per version, the contribution of run-to-run variation could not be measured.

## v1 Baseline: Free-Quote Extraction

The v1 development run completed with the following results:

- Gold claims (G): 376
- Predicted claims (P): 344
- Exact span matches (M): 344
- Correctly classified matches (C): 336
- Joint F1: 0.933 (precision 0.977, recall 0.894)
- Extraction F1: 0.956 (precision 1.000, recall 0.915)
- Gold claim coverage: 0.894
- Missed gold claims: 32
- Unmatched predictions: 0
- Matched claims with incorrect labels: 8
- Answer-level errors: 1 (A19)

## Failure Investigated

The main findings from `runs/v1_development.md` were:

- The 32 missed gold claims were concentrated in `policy_scope` (6), `price_vs_shipping` (4), `inference` (4) and `negation` (3), with the remaining misses spread across other categories.
- Answer A19 failed with `invalid_output: final response is not valid JSON`, even after the repair retry. Its gold claims therefore counted as missed.
- Eight matched claims received incorrect labels. These were tagged as `unit_conversion` (5), `comparison` (3) and `arithmetic` (3); the tags can overlap. The most common label confusion was contradicted being predicted as supported (5 cases).
- There were no unmatched predictions, and extraction precision was 1.000. This indicated that missed claims and classification errors were more important than incorrect span boundaries in this run.

## The One Change in v2

The v2 prompt version is `v2-sentence-index`.

Instead of asking the model to reproduce each full claim as a free-text quote, Python first segments the answer into sentences and the model returns sentence indices. Python then derives the exact source spans and quotes from the original answer.

The objective was to reduce the dependence on exact quote reproduction and make it easier for the model to identify factual claims across the answer, including in cases such as A19. The classification instructions were not intended to change.

## Results: v1 vs v2

Both versions were evaluated on the same 40 development answers using the same scoring rules.

| Metric | v1 | v2 | Change |
|---|---:|---:|---:|
| Joint F1 | 0.933 | 0.876 | -0.057 |
| Joint precision | 0.977 | 0.931 | -0.046 |
| Joint recall | 0.894 | 0.827 | -0.066 |
| Extraction F1 | 0.956 | 0.938 | -0.018 |
| G / P / M / C | 376 / 344 / 344 / 336 | 376 / 334 / 333 / 311 | — |
| Missed gold claims | 32 | 43 | +11 |
| Matched wrong-label predictions | 8 | 22 | +14 |
| Unmatched predictions | 0 | 1 | +1 |
| Answer-level errors | 1 (A19) | 0 | -1 |

Of the claims classified correctly by v1, 51 were no longer correct in v2, while 26 became correct in v2, including nine claims in A19, where v1 had produced no accepted output. On like-for-like answers, v2 improved 17 claims and regressed 51.

The v2 change fixed the A19 output failure, but the overall evaluation regressed. Missed claims increased, particularly in `missing_fact`, `inference` and `feature_conflation`. Wrong-label predictions also increased, especially in `arithmetic` (3 to 9) and `comparison` (3 to 7). Contradicted-to-supported errors increased from 5 to 11, and four unknown-to-contradicted errors appeared.

Some identical claim wordings appeared among both improved and regressed predictions in different answers. This suggests that run-to-run model variation may explain part of the difference, but I did not rerun either version to measure that effect. I therefore cannot attribute the regression to a single cause.

The measured result is a regression, not an improvement. I did not retune v2 against the development results after seeing the comparison.

## Final-Check Runs: A41 to A50

Both versions were run on all 10 final-check answers using the frozen code. The saved check reports contain predictions and answer outcomes but no quality metrics, because the final-check labels were unavailable to me.

- **v1:** 10 of 10 answers completed successfully, 0 answer errors and 90 accepted claims.
- **v2:** 10 of 10 answers completed successfully, 0 answer errors and 82 accepted claims.

Both reports record revision `d8f01c7`. V2 accepted eight fewer claims than v1, consistent with the lower claim counts observed in the development comparison. Without final-check labels, I cannot determine which version performed better on that split.

## Tests Actually Run

The recorded command was `pytest -q -rs`.

- **Result:** 80 passed and 1 warning, with no skipped tests.
- The three PostgreSQL persistence and joined-retrieval tests in `tests/test_api_db.py` ran against a real local PostgreSQL 16 database (`TEST_DATABASE_URL` set). An earlier run without a database gave 77 passed and 3 skipped; the first `winget` install attempt failed with HTTP 403, so I installed PostgreSQL with the EDB installer instead.
- The saved test output is available in `runs/test_output.txt`.
- Fake-provider tests exercise controlled scenarios, but they do not replace the four required live model runs.

**Live model/tool exchange evidence:** The saved run JSON files do not contain the actual provider messages; their `trace_ref` fields are null. A genuine, sanitized exchange from a separate v1 call for answer A01 should be provided in `docs/sample_exchange.md`, with its capture method in `scripts/capture_exchange.py`. This separate capture must not be represented as part of the four saved runs, and its artifacts must be included in the repository before submission.

## Unfinished Work and Limitations

- V2 regressed relative to v1, and I did not have time to investigate and iterate further.
- I did not isolate the cause of the classification regression. Model variability may have contributed, but this was not measured.
- Only one development run was performed per version, so there is no estimate of run-to-run variance.
- The source revision for v1 cannot be reproduced exactly from the visible Git history, and v1 was not rerun against the final commit.
- Langfuse integration, concurrent execution and a React frontend were not implemented because they are optional in the assessment.