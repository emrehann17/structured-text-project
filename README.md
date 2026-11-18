# Structured Turkish News

Python + local Qwen2.5:3b through Ollama. The model classifies news and extracts
people, organizations and places as JSON. The study compares prompt-only and
JSON-schema-constrained generation on the same 100 texts at temperatures 0 and 1.

Entity labels are entered manually by selecting or typing names from the article. The
annotation screen has no model suggestions. **The project is not ready to submit
until all 100 manual annotations, the experiments and the student's video are complete.**
Current progress and measured results are in [the generated report](report/technical_report.md).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
ollama pull qwen2.5:3b
ollama serve
```

Ollama must be installed locally; if its service is already running, skip
`ollama serve`. Check `ollama --version`, `ollama show qwen2.5:3b` and `ollama ps`.
The actual version, model digest, quantization and hardware are captured in each
run's metadata. Use the reported model and parameters for the video.
[All generation settings](docs/GENERATION_PARAMETERS.md) are documented separately.

## 1. Annotate the news manually

```bash
python src/annotate_entities.py --web
```

Open **http://127.0.0.1:8765**. Enter your name. Read the news, select an entity in
its text and click **Kişi ekle**, **Kurum ekle** or **Yer ekle**. You can also type
a name in the corresponding column and press **Enter** or **Ekle**. Both methods
require the name to occur in the article and prevent duplicate entries. Added names
remain highlighted in the article by type, including when revisiting saved work;
removing a name also removes its highlight. Remove a mistaken
selection with ×. When the article is complete, save and advance. Empty lists are
valid only if the article has no entities of that type. Saved selections can be
revisited and corrected. No labels are completed automatically.

Read [the short annotation policy](docs/ANNOTATION_GUIDELINES.md) before starting.
Annotate all names: there is no five-name limit. The 100 original category labels
come from TTC4900; you are annotating entity names, not relabeling categories.

```bash
python src/annotate_entities.py --status
```

**Every save recomputes metrics, the plot and the report.** Entity F1 remains
pending until all 100 articles are completed. After that, any corrected label
triggers a fresh calculation; no score is fixed to an earlier annotation version.
The report records the current gold fingerprint. If a refresh fails, the screen
reports it and old derived artifacts are removed rather than shown as current.

## 2. Run the four experiments

With local Ollama running and an empty experiment output directory:

```bash
python src/evaluate.py --run-all
```

This makes 400 real requests: 100 texts × two modes × two temperatures. Each raw
response is saved immediately. Existing runs are not overwritten; move them outside
the project before starting a replacement study. Interrupted files are incomplete
runs, not usable final results. Keep one complete, consistent set for submission.

The prompt and schema ask for category and person/organization/location arrays.
Prompt-only requests omit `format`; schema requests send `format=JSON_SCHEMA`.
All other settings are identical at a given temperature. Parsing first applies
`json.loads` directly, then retries after cleaning if necessary. Schema and task
correctness are evaluated separately. API and parsing failures stay in denominators.

## 3. Rebuild results and report

```bash
python src/build_report.py
```

This uses the current manual gold and saved raw responses; it makes no model calls.
It updates `results/metrics.json`, `results/metrics.png`, and both report files.
Changes to entity labels affect entity precision/recall/F1 and their discussion.
Formatting and category scores are also recomputed, but entity labels do not enter
those formulas. Changing the prompt/model/settings requires new model outputs.

Raw/cleaned JSON success, schema validity, classification accuracy and entity
micro/per-type F1 are reported. Matching uses exact normalized surface forms with
Turkish casing and entity type preserved. No partial matching or alias groups are
used. The report is limited to four pages; check its PDF visually after final edits.

## 4. Record the video

```bash
python src/demo.py --output results/live_video.jsonl
python src/demo.py --defense
```

The first command runs the same five new fictional texts through both modes and
both temperatures (20 local requests). Inspect their expected categories before
recording. The sports/finance example is intentionally difficult; explain what
actually happens. The second command demonstrates A1 by removing a normalization
line in a temporary evaluator. It is explicitly offline evaluation, not new inference.
It uses a labeled teaching example and, when manual gold is complete, current dataset F1.

[Video preparation](docs/VIDEO_PREPARATION.md) covers the ten selected questions and
submission rules. Start code walkthrough at **00:00**, show live tests uncut, use
English, record screen/voice throughout and show your face initially. Maximum
length: 30 minutes. Upload Unlisted and submit once through the course form by
**22 November 2026, 23:59**. Include real chapter times and accessible code/PDF links.
Do not change submitted code or report after the deadline.

## Files and checks

```text
data/news.jsonl             100 news texts and dataset category labels
data/entity_gold.jsonl      manual entity selections and completion status
data/demo_samples.jsonl     five fictional live-demo stories
src/llm_pipeline.py         prompt, local request, JSON cleaning and schema checks
src/annotate_entities.py    manual annotation server
src/annotation.html         select names from article text
src/evaluate.py             experiments and metrics
src/build_report.py         refresh results, plot and report together
src/demo.py                 live tests and A1 experiment
results/                   four runs, metadata and current derived results
report/                    generated English Markdown and PDF
```

```bash
python -m unittest discover -s tests -v
```

Tests use clearly artificial fixtures and mocked HTTP; experiment commands use
local Ollama. The annotation interface never calls a model. Scripts are the
submission code; a notebook is optional under the assignment.
