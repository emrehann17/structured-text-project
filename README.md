# Project I: Structured Text Classification & Information Extraction

A small Python pipeline classifies Turkish news into seven categories and extracts people, organizations and locations as structured JSON. It uses the local open-source **Qwen2.5:3b** model through **Ollama**. There are no cloud LLM APIs, training or fine-tuning.

The course requirements are demonstrated by schema-constrained generation, explicit JSON cleaning and `try-except` handling, evaluation of **200 real saved responses**, documented Python code, offline tests and a [brief technical report (PDF)](report/technical_report.pdf) ([Markdown](report/technical_report.md)).

## Files

```text
 data/test_samples.jsonl                 Frozen news texts and reference categories
 src/llm_pipeline.py                     Prompt, local request, parsing and validation
 src/evaluate.py                         Offline analysis or explicit fresh inference
 results/optimized_schema_results.jsonl  Original completed responses, unchanged
 results/summary.json                    Recomputed metrics
 results/figures/json_success.png        Four evaluation rates
 report/technical_report.md              Brief report source
 report/technical_report.pdf             Two-page report
 report/evidence.sha256                  Preservation hashes; not needed to run
 tests/test_pipeline.py                  Offline unit and integration tests
 README.md
 requirements.txt
 .gitignore
```

## Dataset and model

The frozen TTC4900 selection (`savasy/ttc4900`, train split) contains 205 records: five development records and **200 evaluation records at `samples[5:205]`**. IDs, texts, order and reference labels are preserved. Selection used seed 42, a 150–3000 character filter and category quotas: 29 each for `dunya`, `ekonomi`, `kultur`, `saglik`; 28 each for `siyaset`, `spor`, `teknoloji`. There are **200 distinct evaluation IDs but 199 unique texts**; IDs 2138 and 2296 contain the same text. The prepared dataset is included, so no download or preparation script is required.

The completed run used `qwen2.5:3b`, JSON Schema in Ollama's `format` field, the Turkish prompt in `build_prompt()`, and these unchanged options:

```python
{"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 384,
 "repeat_penalty": 1.2, "repeat_last_n": 128}
```

Requests use `http://localhost:11434/api/generate`, `stream=False` and `timeout=(5, 60)`. These timeout values apply to connection and read waits. The saved environment records Ollama `0.40.2`; a new installation or model version need not produce identical outputs.

## JSON output and pipeline

Illustrative output shape (not an additional experimental result):

```json
{
  "category": "spor",
  "entities": {"person": [], "organization": [], "location": []}
}
```

News → Turkish prompt → local Ollama → raw response → `json.loads()` → cleaning if needed → schema validation → reference-category comparison → saved result.

`parse_json_response()` first calls `json.loads(raw_output)` directly. On `json.JSONDecodeError`, it calls `clean_json_output()` and retries parsing. The cleaner removes whitespace and Markdown fences, then finds the first decodable JSON object to handle surrounding explanations. It does not invent fields or complete truncated JSON. The original recovery behavior can find a complete inner object inside truncated text; that object must still pass schema validation.

`validate_schema()` rejects missing or extra fields, categories outside the seven labels, and entity fields that are not lists of strings. The prompt asks for at most five names per list and no duplicates; these are prompt instructions, not additional schema rules. `evaluate_sample()` records connection, HTTP and API-envelope errors and allows the next sample to continue. JSON syntax and classification correctness are scored separately.

## Install and analyze offline

Use Python 3.10 or later. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/evaluate.py --analyze
python -m unittest discover -s tests -v
```

Analysis and tests require no Ollama server or model. Running `python src/evaluate.py` without arguments also analyzes saved results. Analysis recomputes flags from raw text, checks IDs and reference labels, and refreshes only `results/summary.json` and the figure. Missing or duplicate result IDs are rejected. Raw response files are never rewritten.

## Fresh local inference (explicit)

Install Ollama, start its local service (`ollama serve` if it is not already running), then download the model and explicitly request a new run:

```bash
ollama pull qwen2.5:3b
python src/evaluate.py --run --results results/fresh_run.jsonl
```

This makes 200 local model requests. The output file must not already exist; the command refuses to overwrite it. Each result is saved immediately. A new summary and figure are saved beside that file, leaving the published results intact. To analyze a completed fresh run later:

```bash
python src/evaluate.py --analyze --results results/fresh_run.jsonl
```

An interrupted file is retained for inspection, but incomplete runs cannot produce final metrics. Choose another new filename to start again. Tests mock the request path; **no fresh inference was performed during simplification**.

## Measured results

These are recomputed from the existing completed run, not a newly executed experiment. The original response file retains its name and bytes.

| Metric | Count / all requests | Rate |
|---|---:|---:|
| First-attempt JSON parsing | 200 / 200 | **100%** |
| JSON parsing after cleaning | 200 / 200 | 100% |
| Schema validity | 200 / 200 | 100% |
| Classification accuracy | 107 / 200 | **53.5%** |

All 200 requests returned responses; API errors: **0**. Saved elapsed time totals **241.83 seconds**, averaging **1.21 seconds per record**. It includes request waiting and local parsing; offline reanalysis does not remeasure inference time.

Each rate is `successful_count / total_requests * 100`. API, parsing and schema failures stay in the denominator. First-attempt success means the unmodified model text parses before cleaning. The post-cleaning metric includes direct successes plus recovered responses; **zero responses needed recovery in this run**. Classification is counted correct only after schema validation and equality with the reference label.

![Evaluation rates for 200 records](results/figures/json_success.png)

## Limitations and preserved evidence

Valid JSON does not guarantee correct classification or factual entities. Entity extraction was performed, but no manually annotated entity ground truth was used, so semantic entity accuracy and hallucination detection were not evaluated. One repeated text slightly reduces evaluation diversity. Findings apply to this dataset and configuration.

The complete pre-simplification code and tracked experiments are preserved on [`backup/pre-simplification`](https://github.com/emrehann17/structured-text-project/tree/backup/pre-simplification), at commit `f970b0c9bbb622d8e5a6d3ccf5fe4aea90aca7cb`. [SHA-256 records](report/evidence.sha256) cover the unchanged dataset and every original model response file; historical response files can be checked on that branch. Hashes are preservation evidence, not an everyday execution step.
