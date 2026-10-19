# Claim extraction & classification agent (Kasparro FSE assessment)

Reads a long answer about speaker products, extracts each factual claim sentence, labels it
`supported | contradicted | unknown` against `brand_facts.csv` using live **tool calling** (`get_brand_facts`).

## Layout
| Path | Role |
|---|---|
| `claims/agent.py` | ≤3-turn tool loop, tool executor, Python offset location, strict validation |
| `claims/prompts.py` | v1 (free quote) and v2 (sentence index) prompts |
| `claims/provider.py` | `GeminiProvider` (free, default), `AnthropicProvider` (paid, optional), `FakeProvider` (tests) |
| `claims/scorer.py` | deterministic exact-span scorer (extraction + joint metrics) |
| `claims/runner.py` | sequential run → JSON record; gold joined only after predictions |
| `claims/api.py`, `db.py`, `schema.sql` | thin FastAPI + PostgreSQL (`runs`, `answer_results`, `claim_results`) |
| `scripts/run_eval.py`, `compare.py` | live runs and v1-vs-v2 report |
| `tests/` | controlled tests (fake provider, scorer arithmetic, API, real Postgres) |
| `docs/EXPLANATION.md` | your write-up: change, evidence, disclosure, unfinished work |

## Setup
```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env     # paste your FREE Gemini key (https://aistudio.google.com/apikey) into .env
python scripts/list_models.py   # pick a flash / flash-lite model free for your project -> GEMINI_MODEL in .env
```
- Free tier, no billing. Note Google may use free-tier inputs for model improvement (this dataset is fictional).
- Do **not** use `gemini-2.5-*` (shut down 16 Oct 2026). Keep the **same model** for all four runs.
- Provider timeout per request: **90 s** (`--timeout`). Requests are throttled to one per 6.5 s (`--min-interval`) and
  429s are retried. Budget: ~2 requests per answer => ~80 per development run, ~200 for all four runs. If your model's
  daily limit is lower (check https://aistudio.google.com/rate-limit), use a Flash-Lite model; a daily-quota hit marks
  the run `failed` with partial evidence preserved.
- Gemini runs use the model's default temperature (Google advises against lowering it for Gemini 3), so reruns can differ
  slightly; mention this when comparing v1 and v2 (`--temperature 0` is available).

## The required sequence
```bash
python scripts/run_eval.py --version v1 --split development --limit 3   # smoke test only
python scripts/run_eval.py --version v1 --split development             # artifact 1  (+ .md with error buckets)
#  inspect runs/v1_development.md -> pick ONE failure/risk -> adjust v2 (only that behaviour)
python scripts/run_eval.py --version v2 --split development             # artifact 2
python scripts/compare.py                                               # runs/comparison.md
#  freeze code (git commit + tag), then:
python scripts/run_eval.py --version v1 --split check                   # artifact 3
python scripts/run_eval.py --version v2 --split check                   # artifact 4
```
Add `--db` to also persist a run to PostgreSQL.

## If the free quota runs out (resume, don't restart)
Progress is saved after every answer to `runs/<name>.partial.json`. If a run stops (daily quota, outage, Ctrl+C, laptop sleep)
it prints `RUN STOPPED` and exits. Re-run the **same command plus `--resume`**; only unfinished answers (and answers that
failed with a transient provider error) are re-requested. After 5 consecutive provider failures the run stops by itself
instead of burning quota. Free-tier limits are per Google *project*: a key from a NEW project in AI Studio gives fresh quota
(keep the same model, and disclose the key switch in `docs/EXPLANATION.md`).

## Tests
```bash
pytest -q                                                        # DB tests skip without a DB
TEST_DATABASE_URL=postgresql://user:pw@localhost:5432/claims_test pytest -q -rs   # full suite
```
API: `uvicorn claims.api:app` with `DATABASE_URL` set. Endpoints: `POST /classify`, `POST /evaluation-runs`,
`GET /evaluation-runs/{id}`.