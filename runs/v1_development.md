# v1 / development  (run 83002309-bb08-4fed-a0c5-a798cf02ce68)
- status: **completed**  provider: gemini / gemini-3.5-flash-lite  duration: 543.25s
- prompt: v1-free-quote  dataset: long-brand-answers-50-v4  facts: speaker-catalogue-v4  evaluator: sentence-spans-and-labels-v4  revision: 2d4e8cdaf9d8c7054a2a73ccdef643be1042deef
- settings: `{'temperature': 'model default', 'max_output_tokens': 8192, 'min_interval_s': 6.5, 'retries_on_429': 3, 'provider_timeout_s': 90.0, 'max_turns': 3, 'limit': None}`
- answers: scheduled 40, ok 39, errors 1, empty 0; accepted predictions 344
- G=376 P=344 M=344 C=336
- **Joint F1 0.933** (P 0.977, R 0.894)
- Extraction F1 0.956 (P 1.000, R 0.915)
- gold coverage C/G 0.894; missed 32; unmatched predictions 0; matched wrong-label 8; answer errors 1 ['A19']
  - A19: invalid_output: final response is not valid JSON

## Error buckets

Missed gold claims by tag: policy_scope=6, price_vs_shipping=4, inference=4, negation=3, model_scope=2, explicit_false=2, variant_transfer=2, negative_missing_fact=2, unit_conversion=2, feature_conflation=2, comparison=1, arithmetic=1, capability_vs_connector=1, policy_vs_capability=1, future_scope=1, box_scope=1, qualification=1, cross_brand_comparison=1, missing_condition=1, missing_fact=1

Wrong-label (matched) by tag: unit_conversion=5, comparison=3, arithmetic=3

Label confusion (expected -> predicted): contradicted->supported=5, supported->contradicted=3

Unmatched predictions (extras / bad boundaries): 
