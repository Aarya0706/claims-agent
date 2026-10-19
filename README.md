# Claim extraction & classification agent (Kasparro FSE assessment)

A Python agent that reads a long answer about speaker products, extracts each factual claim sentence with exact
source spans, and labels each one `supported | contradicted | unknown` against `brand_facts.csv`. The model
must request facts through real tool calling (`get_brand_facts`). A deterministic harness scores extraction and
classification, and a thin FastAPI service stores runs in PostgreSQL.

- Provider: Gemini free tier, model **`gemini-3.5-flash-lite`** (all four recorded runs used this model and the model's default temperature).
- Versions: dataset `long-brand-answers-50-v4`, facts `speaker-catalogue-v4`, evaluator `sentence-spans-and-labels-v4`.
- v1 = free-quote extraction (baseline). v2 = Python sentence segmentation, model selects sentence indices (candidate).
- Write-up, disclosure of AI help, limitations: [`docs/EXPLANATION.md`](docs/EXPLANATION.md).

## Results at a glance

Development split (A01 to A40, 376 gold claims), identical inputs, scorer, model and settings:

| | v1 | v2 |
|---|---|---|
| Joint F1 | **0.933** | 0.876 |
| Extraction F1 | **0.956** | 0.938 |
| Missed gold claims | 32 | 43 |
| Wrong-label matches | 8 | 22 |
| Unmatched predictions | 0 | 1 |
| Answer errors | 1 (A19) | 0 |

v2 fixed the A19 invalid-output failure but is a regression overall; see `docs/EXPLANATION.md` for the analysis and
caveats (one run per version, default temperature). Check split (A41 to A50): both versions completed 10 of 10
answers with 0 errors (v1: 90 accepted predictions, v2: 82); quality metrics are null because the labels are private.

## Evidence in this repository

| Evidence | Path |
|---|---|
| v1 and v2 development runs (predictions, outcomes, metrics, error buckets) | `runs/v1_development.{json,md}`, `runs/v2_development.{json,md}` |
| v1 and v2 check runs (predictions, outcomes, counts; no quality scores) | `runs/v1_check.{json,md}`, `runs/v2_check.{json,md}` |
| v1 vs v2 comparison (regressions and improvements) | `runs/comparison.md` |
| Smoke test (3 answers, not a deliverable) | `runs/v1_development_limit3.{json,md}` |
| Actual test output (`77 passed, 3 skipped`) | `runs/test_output.txt` |
| One real, sanitized model/tool exchange | `docs/sample_exchange.md` |
| Explanation, disclosure, limitations | `docs/EXPLANATION.md` |

The check runs and v2 development run record the git revision they ran on. The code was frozen and tagged
`frozen-v1-v2` before the check runs.

## Layout

| Path | Role |
|---|---|
| `claims/agent.py` | At most 3 model turns, tool executor, Python offset location, strict output validation, one-turn JSON repair retry |
| `claims/prompts.py` | v1 (free quote) and v2 (sentence index) prompts |
| `claims/provider.py` | `GeminiProvider` (default), `AnthropicProvider` (optional, paid), `FakeProvider` (tests) |
| `claims/data.py` | CSV loading with a real parser; `ai_answer` is never stripped or re-saved |
| `claims/scorer.py` | Deterministic exact-span scorer (extraction and joint precision/recall/F1) |
| `claims/runner.py` | Sequential run to a JSON record; gold is joined only after predictions exist |
| `claims/api.py`, `db.py`, `schema.sql` | Thin FastAPI service and PostgreSQL persistence (`runs`, `answer_results`, `claim_results`) |
| `scripts/run_eval.py`, `compare.py` | Live runs and the v1-vs-v2 report |
| `scripts/capture_exchange.py` | Captures one real model/tool exchange into `docs/sample_exchange.md` |
| `scripts/list_models.py` | Lists Gemini models available to your key |
| `tests/` | Controlled tests (fake provider, scorer arithmetic, validation, API, PostgreSQL) |
| `data/` | The issued CSVs go here (see "Data files") |

## Setup

Requires Python 3.12 and a free Gemini API key from <https://aistudio.google.com/apikey>.
Dependencies are in `requirements.txt`.

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` (never commit it):
```
GEMINI_API_KEY=your-key
CLAIMS_PROVIDER=gemini
GEMINI_MODEL=gemini-3.5-flash-lite
```
`python scripts/list_models.py` shows the models your key can use. Keep the **same model** for all four runs.
Do not use `gemini-2.5-*` (shut down 16 Oct 2026).

## Data files

The issued `answers.csv`, `brand_facts.csv` and `development_gold.csv` are **not committed**. Place them in `data/`
(or point `DATA_DIR` at their folder). Their SHA-256 hashes are in `data/HASHES.txt`, and every run record also stores
the file hashes it used.

## Running the evaluation

```powershell
python scripts/run_eval.py --version v1 --split development --limit 3   # smoke test only
python scripts/run_eval.py --version v1 --split development             # artifact 1
python scripts/run_eval.py --version v2 --split development             # artifact 2
python scripts/compare.py                                               # runs/comparison.md
# freeze code (git commit + tag), then:
python scripts/run_eval.py --version v1 --split check                   # artifact 3
python scripts/run_eval.py --version v2 --split check                   # artifact 4
```
Each run writes `runs/<version>_<split>.json` and `.md`. Add `--db` to also persist a run to PostgreSQL.

- **Timeout:** each provider request has a **90 s** timeout (`--timeout`). Requests are throttled to one per 6.5 s (`--min-interval`); HTTP 429 is retried up to 3 times.
- **Cost and quota:** about 2 requests per answer, about 80 per development run. A daily-quota hit marks the run `failed` and keeps the partial evidence.
- **Resume, don't restart:** progress is saved after every answer to `runs/<name>.partial.json`. If a run stops, re-run the same command plus `--resume`.
- **Determinism:** the model's default temperature is used (Google advises against lowering it for Gemini 3), so reruns can differ slightly. `--temperature 0` is available.

## Tests

```powershell
pytest -q -rs                                   # DB tests are skipped without a database
```
Recorded result: **77 passed, 3 skipped, 1 warning** (`runs/test_output.txt`). The 3 skipped tests are the PostgreSQL
persistence tests in `tests/test_api_db.py`; they were **not run against a real PostgreSQL** for the recorded evidence
(`TEST_DATABASE_URL` was not set). Everything else, including the fake-provider, validation, scorer and API-validation
tests, ran. Fake-provider tests do not replace the live runs.

To run the PostgreSQL tests against a throwaway database:
```powershell
$env:TEST_DATABASE_URL="postgresql://user:password@localhost:5432/claims_test"
pytest -q -rs
```
```bash
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/claims_test pytest -q -rs
```
The tests create and clear tables, so use a database you can discard.

## API and database

Create a database, set `DATABASE_URL`, apply the schema once and start the service:
```powershell
$env:DATABASE_URL="postgresql://user:password@localhost:5432/claims"
python -c "from claims import db; c = db.connect(); db.init_schema(c); c.close()"
uvicorn claims.api:app
```
`python scripts/run_eval.py ... --db` also creates the schema automatically.

| Endpoint | Behavior |
|---|---|
| `POST /classify` | Input `answer_id`, `brand_id`, `question`, `ai_answer`, `agent_version` (v1/v2). 200 with validated claims; 422 invalid input or gold/claim-list fields; 404 unknown brand; 502 provider or invalid output; 504 timeout. |
| `POST /evaluation-runs` | Input `agent_version`, `split`. Runs the fixed CSV split; 201 with run id, status, counts and metrics (null for `check`). |
| `GET /evaluation-runs/{id}` | Joins run metadata, answer outcomes and predicted claims in stable order; 404 missing, 422 invalid UUID. |

Storage uses parameterized SQL only, foreign keys, and unique constraints on `(run_id, answer_id)` and
`(run_id, answer_id, start_char, end_char)`.

## Design notes

- **Tool contract:** the model must call `get_brand_facts(brand_id)` through real tool calling. The executor validates the tool name and the brand argument; an illegal tool or unknown brand is an answer-level error. Text in the answer is never executed.
- **Spans:** offsets are computed by Python (never by the model) as zero-based code-point positions in the exact `ai_answer`. The validator checks bounds, quote equality, duplicate IDs, overlaps, labels and fact IDs.
- **Errors are preserved:** an invalid response, unknown tool, provider failure or turn-limit hit becomes an answer-level error with no accepted predictions; it is never converted to `unknown`.
- **Scoring:** a prediction matches a gold claim only on identical `answer_id`, `start_char` and `end_char`. Joint F1 is the main metric; error answers keep all their gold claims as missed. Gold labels are used only in the harness, after predictions are saved, and never reach the model or the tool.
- **Check runs:** no gold is read; all quality metrics stay null.

## Limitations

See `docs/EXPLANATION.md` for the full list. In short: one run per version at the default temperature (no variance
measurement), v2 is a regression and was not iterated on, and the PostgreSQL persistence tests were not run against a
real PostgreSQL for the recorded evidence. Langfuse, concurrency and the React front end were not built (all optional).