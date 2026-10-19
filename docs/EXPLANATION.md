# Explanation (fill in after the live runs)

## Disclosure
- Built with help from Claude (Anthropic). I reviewed the code and ran the checks listed below.
- Splitter check: a plain `.`/`!`/`?` splitter reproduces all 376 development gold boundaries. That was observed
  on the development set before v2 was written (design informed by dev gold boundaries; no final-check labels exist to me).
- Final-check inputs are visible; I did / did not tune on them: ______ . This is not a fully blind benchmark.

## Fixed across v1 and v2
Provider Gemini (free tier) / model ______ / temperature ______ (default unless set) / max_output_tokens 8192 / timeout 90 s / min 6.5 s between requests / max 3 turns / same CSVs & scorer. Runs are not bit-for-bit deterministic; v1-v2 differences smaller than run-to-run noise should not be over-claimed.

## v1 baseline (free-quote extraction)  — results
G=___ P=___ M=___ C=___ | joint F1 ___ | extraction F1 ___ | answer errors ___

## Failure investigated (from runs/v1_development.md)
<which error bucket, N claims, example ids, why it happens>

## The one change in v2
<current candidate: Python sentence segmentation + model selects sentence indices; replace if v1 errors point elsewhere>

## Results v1 → v2 (identical inputs)
<table from runs/comparison.md; regressions & improvements; "no gain" is an acceptable result>

## Tests actually run (not just written)
- pytest: ___ passed, ___ skipped (with real PostgreSQL: yes/no)  — fake-provider tests do not replace the live runs.

## Unfinished / limitations
<list>
