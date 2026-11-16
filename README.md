# NLP Project I — Structured Turkish News

A small Python pipeline calls local **Qwen2.5:3b through Ollama**, classifies TTC4900
news, extracts names, preserves raw output, parses/cleans JSON and measures results.
The November upgrade compares prompt-only with schema-constrained decoding and
includes a real human entity-review workflow.

**Submission is not complete:** entity gold needs human verification; the student
must confirm the demo categories, record the English video and upload it Unlisted.
Deadline: **22 November 2026, 23:59 Türkiye time**. The English report is the primary
submission; the retained Turkish report is an older historical reference only.

## Install and model setup

Run commands from the repository root. Python 3.12 was used locally.

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Install Ollama using its [official Linux instructions](https://docs.ollama.com/linux)
or the installer for your operating system. On Linux the documented install command is:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

Keep the server running in another terminal; skip `ollama serve` if the service
is already running. On a fresh installation fetch and inspect the model:

```bash
ollama pull qwen2.5:3b
ollama list
ollama show qwen2.5:3b
ollama --version
ollama ps
python src/evaluate.py --env
```

Do not pull/update a model halfway through a controlled pair. `--env` captures the
current environment and overwrites `results/environment.json`; run sidecars retain
their own before/after evidence. The measured environment reports **Q4_K_M**, Ollama
**0.40.2**, NVIDIA GeForce RTX 3050 Ti Laptop GPU (4096 MiB), and digest
`357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
Quantization was read from the installed model, not inferred from its tag.

## Data and experiment design

The frozen [TTC4900 source](https://huggingface.co/datasets/savasy/ttc4900) selection
has 205 records: first five development, next 200 historical evaluation. The 200
contain 199 distinct texts. `data/evaluation_ids.json` fixes a balanced selection of
100 distinct texts: scan in stored order, skip exact duplicate text, fill quotas
of 15 dunya, 15 ekonomi and 14 in each remaining category. No model output is used
for selection. Both modes and temperatures use these IDs in identical order.

All new requests use Turkish prompt **v2**, temperature 0 (or explicitly 1), seed
42, num_ctx 4096, num_predict 384, repeat_penalty 1.2, repeat_last_n 128, stream false.
**top_k and top_p are not explicitly set**. v2 adds an explicit JSON output template
to the original prompt because v1 did not expose the object structure to prompt-only
mode; see [provenance](docs/UPGRADE_EVIDENCE.md). No other prompt tuning was done.

- `mode=prompt`: asks for JSON in the prompt; **omits `format` entirely**.
- `mode=schema`: adds `format=JSON_SCHEMA`; every other request field is identical.
- Temperature experiment: same mode, prompt, model and options; only temperature changes.

The required object is:

```json
{"category":"spor","entities":{"person":[],"organization":[],"location":[]}}
```

Categories: dunya, ekonomi, kultur, saglik, siyaset, spor, teknoloji. The schema
requires these fields/types, an allowed category, and no extra keys. The prompt
limits each entity list to five; the schema does not enforce semantic correctness.

Pipeline: load source → build prompt/request → genuine local HTTP request → preserve
raw response → direct `json.loads` → catch `JSONDecodeError` → clean fences/surrounding
text → retry parse → validate structure → score → append JSONL. No missing facts or
closing braces are invented. API errors are saved and later samples continue.

## Reproduce the controlled experiments

The committed `results/*.jsonl` files are evidence and cannot be overwritten.
Use a new directory for a reproduction (choose another name if it already exists):

```bash
python src/evaluate.py --run --mode prompt --temperature 0 --results results/reproduction/prompt_only.jsonl
python src/evaluate.py --run --mode schema --temperature 0 --results results/reproduction/schema_constrained.jsonl
python src/evaluate.py --run --mode prompt --temperature 1 --results results/reproduction/prompt_only_temp1.jsonl
python src/evaluate.py --run --mode schema --temperature 1 --results results/reproduction/schema_constrained_temp1.jsonl
python src/evaluate.py --compare --directory results/reproduction
```

This performs **400 genuine requests**: 100 per condition. The temperature study
uses all 100 texts because local inference is practical. No automatic retries
replace failures. If a process is interrupted, repeat its exact command with
`--resume`; it verifies the saved ID prefix, source/prompt hashes, options, digest
and environment before appending. Only metadata status `running` may resume.
Truncated/corrupt files fail loudly; preserve them and use a new directory.

To reanalyze the committed controlled results without inference:

```bash
python src/evaluate.py --compare
python src/evaluate.py --analyze --results results/prompt_only.jsonl
```

Comparison validates complete matching ID order, duplicates/missing results,
model digest, quantization, prompt/schema hashes, hardware/software fingerprint,
mode and options. Missing/incomplete runs have explicit pending status. It writes
`comparison.json`, `temperature_comparison.json`, and `figures/mode_temperature_comparison.png`
inside the compared directory. JSONL rows retain original raw text, predictions,
entities, parse/schema/correctness flags, API error, timing and provenance.

All four rates divide by **all requests**, including API and structural failures.
Post-cleaning parsing includes directly parsed responses. Classification accuracy
requires a schema-valid category equal to its reference label. Entity precision,
recall and micro/per-type F1 use normalized exact matching with type preserved;
invalid outputs have no predicted entities. An unavailable F1 is never plotted as zero.

## Measured November results

Each row uses the same 100 selected texts; there were zero API errors in all four runs.

| Mode | Temperature | Raw JSON | After cleaning | Schema | Accuracy | Entity F1 |
|---|---:|---:|---:|---:|---:|---|
| Prompt-only | 0 | 96% | 99% | 98% | 48% | PENDING HUMAN REVIEW |
| Schema | 0 | 100% | 100% | 100% | 50% | PENDING HUMAN REVIEW |
| Prompt-only | 1 | 75% | 99% | 99% | 54% | PENDING HUMAN REVIEW |
| Schema | 1 | 100% | 100% | 100% | 52% | PENDING HUMAN REVIEW |

At T=0 the 98 outputs valid in both modes have identical categories. Schema's
+2 points come from IDs 4811 (prompt category `tekno`, outside the enum) and 2379
(prompt output has invalid escape sequences). This is an end-to-end reliability
gain, not evidence of better category choices among mutually valid outputs.
Entity semantic accuracy remains unknown until human review. Raising temperature
reduced prompt-only raw parsing but improved its classification in this run;
no universal temperature effect is claimed.

## Human entity review and F1

```bash
python src/annotate_entities.py --status
python src/annotate_entities.py --reviewer "Your real name"
python src/annotate_entities.py --reviewer "Your real name" --id 4000
python src/evaluate.py --compare
python src/build_report.py
```

Read [annotation rules](docs/ANNOTATION_GUIDELINES.md) first. Initial suggestions
come from historical model predictions and are **not gold**. The helper displays
full original text; Enter keeps a list, `-` empties it, semicolons separate names,
and `|` joins aliases. Only the human's explicit `y` verifies a record. Progress
is saved per reviewed record. Review all 100 texts, correct wrong types and check
omissions. Retain the first five distinct mentions of each type. The scorer handles
Turkish İ/I casing, Unicode normalization, whitespace, aliases and duplicates.
F1 stays **PENDING HUMAN REVIEW** until every selected record is verified.

## Live video demo

Five newly authored fictional Turkish stories are separate from TTC4900; novelty
is checked against all 205 records and the other demo texts. This establishes local
novelty, not absence from a model's pretraining data. The sports-finance story is
intentionally ambiguous. Its error is not guaranteed. Read and manually confirm
or correct `true_category` for each demo record; then set `category_review_status`
to `verified` and add reviewer/time fields. Until then comparisons are draft.

```bash
python src/demo.py --check
python src/demo.py --mode both --temperatures 0 1 --output results/video_take1.jsonl
python src/demo.py --defense --output results/defense_take1.jsonl
```

The first live command sends 20 real requests: five texts × two modes × two
temperatures. Raw text, parsing, schema validity, prediction, entities and expected
categories appear on screen. No mock/replay option exists. A1 makes two real
requests before/after removing the format assignment in a temporary source copy;
repository code remains intact. Use a fresh output filename for another take.
[English video preparation](docs/VIDEO_PREPARATION.md) covers code lines, ten defense
questions, live order, recording requirements and chapters. These are speaking
notes, not a script to read aloud.

## Tests and English report

```bash
python -m unittest discover -s tests -v
python src/build_report.py
```

Tests are offline and mock HTTP only inside tests. They cover both request bodies,
temperature, parsing/cleaning, errors, schema, denominators, Turkish entities, review
enforcement, paired provenance, preservation and demo novelty/live-call routing.
The report builder recalculates metrics from saved raw responses and generates
`report/technical_report.md` and `report/technical_report.pdf` using ReportLab.
It refuses a report over four pages. Visually inspect all PDF pages, especially
after completing gold review; the current PDF is explicitly a draft while F1 is pending.

## Evidence and structure

Historical results are the frozen `optimized_schema_results.jsonl` and original
`summary.json`: 200/200 raw JSON, 200/200 schema, 107/200 classifications (53.5%),
zero API errors. **These are not new comparison results.** New measured results
are in `comparison.json` and `temperature_comparison.json`; each new run has a
metadata sidecar with before/after environment evidence. Earlier partial upgrade
outputs in `prior_upgrade/` are excluded. Never combine different configurations.

```text
data/    test_samples.jsonl, evaluation_ids.json, entity_gold.jsonl, demo_samples.jsonl
src/     llm_pipeline.py, evaluate.py, annotate_entities.py, demo.py, build_report.py
results/ historical evidence, four new runs + sidecars, comparisons, figures,
         environment.json, prior_upgrade/, dev_checks/
report/  technical_report.md, technical_report.pdf, historical Turkish reference
docs/   ANNOTATION_GUIDELINES.md, VIDEO_PREPARATION.md, UPGRADE_EVIDENCE.md
tests/   test_pipeline.py, test_upgrade.py
```

The original dataset and 200 responses are SHA-256 protected in tests.
`backup/pre-simplification` remains intact; `backup/pre-nov2026-upgrade-20261116`
protects main before this upgrade. No history rewrite or force-push is used.

Limitations: single seed, small balanced selection, exact matching and five-name
cap, model-suggested annotation bias, label-taxonomy ambiguity, possible pretraining
overlap and hardware/software nondeterminism. Human gold review, manual demo-label
confirmation, the final English screen/voice recording (face at beginning), and
Unlisted YouTube upload with actual chapter timestamps remain required.
