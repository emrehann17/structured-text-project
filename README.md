# Structured Text Classification and Information Extraction

This project compares three ways to obtain structured data from Turkish news using a local **qwen2.5:3b** model through Ollama. Each response assigns one of seven news categories and extracts person, organization and location lists. The implementation separates JSON syntax, schema compliance and classification accuracy. No model training is performed.

## Dataset: 205 = 5 + 200

[data/test_samples.jsonl](data/test_samples.jsonl) contains 205 records: `samples[:5]` are development samples; `samples[5:205]` are the 200 evaluation records shared by A, B and C. Each experiment has 200 saved responses with zero API errors.

Selection uses the TTC4900 `train` source, seed 42, a 150–3000 character filter and a deterministic quota extension. [The dataset manifest](data/test_samples_manifest.json) fixes provenance, membership, order and SHA-256. Evaluation support is 29 each for `dunya`, `ekonomi`, `kultur`, `saglik`, and 28 each for `siyaset`, `spor`, `teknoloji`.

The evaluation has **200 unique IDs but 199 unique texts**: IDs 2138 and 2296 contain identical text. Across all 205 records there are 204 unique texts. Membership and order were preserved after inference; measurements are per record.

## Pipeline architecture

News → prompt → Ollama response → JSON parsing → schema validation → category comparison → JSONL checkpoint → analysis → figures → verification.

| File in `src/` | Role |
|---|---|
| `step1_prepare_dataset.py` | Reproduce the frozen selection and verify its manifest; already prepared in this repository. |
| `step2_test_model.py` | Test local Ollama with one development sample; makes a real model request. |
| `step3_run_experiments.py` | Main entry point; validate checkpoints and run A → B → C when incomplete. |
| `step3a_evaluate_prompt.py` | Experiment A: prompt-only generation. |
| `step3b_evaluate_json.py` | Experiment B: generation with JSON Schema. |
| `step3c_evaluate_optimized.py` | Experiment C: shorter prompt and repetition controls with JSON Schema. |
| `step4_analyze_results.py` | Recompute saved metrics and confusion matrices. |
| `step5_generate_figures.py` | Refresh analysis and generate six PNG/SVG figure pairs. |
| `step6_verify_project.py` | Verify data, responses, metrics, matrices, figures and source hashes without inference. |
| `dev_evaluate_baseline.py` | Separate five-sample development baseline; excluded from A/B/C results. |

## Experiments

- **A — Prompt only:** detailed Turkish prompt without generation-time schema enforcement.
- **B — JSON Schema:** the same prompt as A, with `format=JSON_SCHEMA`.
- **C — Optimized schema:** shorter prompt, the same schema, `repeat_penalty=1.2` and `repeat_last_n=128`.

All three use `temperature=0`, `seed=42`, `num_ctx=4096`, `num_predict=384`, `stream=False` and `timeout=(5, 60)`. `top_k` and `top_p` are not explicitly configured. Recorded Ollama version: `0.40.2`. [Run identity](results/run_identity.json) records the model digest and dataset/source hashes; model parameter metadata was null.

## JSON parsing and schema validation

The HTTP response is a JSON envelope; its `response` field contains the model's output text. Raw JSON success requires that text to parse directly. If parsing fails, the existing cleaner removes Markdown fences and attempts to locate a complete JSON object; it does not repair truncated JSON.

Schema validation requires a valid category and `entities` containing `person`, `organization` and `location` arrays of strings, with no extra fields. The five-entity maximum is a prompt instruction, not a schema constraint. A schema-valid category is compared with the reference label. API, parsing and schema failures remain in the denominator and the confusion matrices' `INVALID` column.

## Experimental results

All metrics are verified against saved raw responses. Main rates use **200 requests**; conditional accuracy uses the schema-valid count.

| Metric | A: Prompt only | B: JSON Schema | C: Optimized schema |
|---|---:|---:|---:|
| Responses | 200 | 200 | 200 |
| Raw JSON | 0/200 (0.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Clean JSON | 166/200 (83.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Schema valid | 162/200 (81.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Correct category | 80/200 (40.00%) | 87/200 (43.50%) | 107/200 (53.50%) |
| Conditional accuracy | 80/162 (49.38%) | 87/158 (55.06%) | 107/200 (53.50%) |
| Total time (s) | 689.88 | 505.97 | 241.83 |
| Mean time (s) | 3.45 | 2.53 | 1.21 |

Evidence: [metrics](results/metrics_summary.json), [A responses](results/improved_prompt_results.jsonl), [B responses](results/schema_results.jsonl), [C responses](results/optimized_schema_results.jsonl). Confusion matrices for [A](results/confusion_matrix_A.csv), [B](results/confusion_matrix_B.csv) and [C](results/v3_confusion_matrix.csv) each total 200; rows are reference categories and columns are predictions.

## Six evaluation visualizations

The saved figures remain unchanged and are available in both formats:

| Visualization | PNG | SVG |
|---|---|---|
| JSON and schema success | [PNG](results/figures/json_success_comparison.png) | [SVG](results/figures/json_success_comparison.svg) |
| Classification accuracy | [PNG](results/figures/classification_accuracy.png) | [SVG](results/figures/classification_accuracy.svg) |
| Inference runtime | [PNG](results/figures/inference_performance.png) | [SVG](results/figures/inference_performance.svg) |
| Experiment C confusion matrix | [PNG](results/figures/confusion_matrix.png) | [SVG](results/figures/confusion_matrix.svg) |
| Experiment C category accuracy | [PNG](results/figures/category_accuracy.png) | [SVG](results/figures/category_accuracy.svg) |
| Experiment B failure analysis | [PNG](results/figures/schema_failure_analysis.png) | [SVG](results/figures/schema_failure_analysis.svg) |

## Run and verify

From the project root, create an environment if needed, install dependencies and activate it:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python src/step3_run_experiments.py
python src/step6_verify_project.py
python -m unittest discover -s tests -v
```

The included run is complete: the main entry point validates all 600 records and exits **without contacting Ollama**. Verification recomputes metrics in memory and checks stored artifacts. Unit tests cover incomplete analysis, invalid IDs/flags, checkpoint resume and the completed runner's absence of network/subprocess calls.

For an incomplete checkpoint, the runner checks Ollama availability and model/dataset/code identity, then invokes A/B/C sequentially with `--limit 200`. Saved IDs, including errors, are skipped; malformed JSONL fails visibly. Use one runner at a time. Step 2 and the development baseline are unnecessary for presenting the completed run and can make model requests.

Steps 4 and 5 can regenerate analysis and figures from saved responses without inference; they are unnecessary for verification. Step 1 accepts `--source-arrow /path/to/ttc4900-train.arrow` for a local source cache and refuses to overwrite different dataset membership/order.

## Limitations

A has 34 outputs unparseable after cleaning and four parsed outputs that fail the schema. C has 200 structurally valid outputs but 93 incorrect categories. Structural validity does not establish semantic entity correctness: no human-labeled entity reference is available, so no NER F1 or hallucination rate is claimed. Entity checks cover structure, repetition and list length only.

C changes both prompt and repetition settings, so their individual effects are not isolated. Duplicate text limits record independence. Results describe this saved model/runtime and sample; hardware/GPU utilization was not remeasured.

Study materials: [code guide](docs/CODE_STUDY_GUIDE_TR.md), [technical Q&A](docs/TECHNICAL_QA_TR.md), [presentation plan](docs/PRESENTATION_PREPARATION_TR.md), [verification summary](docs/VERIFICATION_SUMMARY_TR.md) and [machine-readable verification](docs/verification.json). Historical source-preservation evidence remains in [the migration manifest](docs/migration_manifest.json).
