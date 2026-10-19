# v2 / development  (run 2deda42f-98e2-4739-b216-0c51f526bcf0)
- status: **completed**  provider: gemini / gemini-3.5-flash-lite  duration: 535.73s
- prompt: v2-sentence-index  dataset: long-brand-answers-50-v4  facts: speaker-catalogue-v4  evaluator: sentence-spans-and-labels-v4  revision: 0c78877d5a72ebcbfdb465a3aab6ea99f77e035a
- settings: `{'temperature': 'model default', 'max_output_tokens': 8192, 'min_interval_s': 6.5, 'retries_on_429': 3, 'provider_timeout_s': 90.0, 'max_turns': 3, 'limit': None}`
- answers: scheduled 40, ok 40, errors 0, empty 0; accepted predictions 334
- G=376 P=334 M=333 C=311
- **Joint F1 0.876** (P 0.931, R 0.827)
- Extraction F1 0.938 (P 0.997, R 0.886)
- gold coverage C/G 0.827; missed 43; unmatched predictions 1; matched wrong-label 22; answer errors 0 []

## Error buckets

Missed gold claims by tag: missing_fact=9, inference=9, price_vs_shipping=6, feature_conflation=6, policy_scope=5, negative_missing_fact=3, negation=3, requirement_vs_availability=2, cross_brand_comparison=2, condition_scope=1, outdated_fact=1, model_scope=1, qualification=1, missing_condition=1

Wrong-label (matched) by tag: arithmetic=9, comparison=7, unit_conversion=6, condition_scope=3, date_scope=2, historical_scope=2, policy_scope=1, requirement_vs_availability=1

Label confusion (expected -> predicted): contradicted->supported=11, supported->contradicted=7, unknown->contradicted=4

Unmatched predictions (extras / bad boundaries): A18:2173:2236
