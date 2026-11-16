# English video preparation — notes, not a script

Use these prompts to understand the work and explain it in your own words. Do not
read prepared answers directly. No synthetic voice, invented experience or fake
model response is needed. Maximum video length: **30 minutes**. Keep screen and
voice recorded throughout, show your face at least at the beginning, and perform
the live model tests continuously **without cuts**. Aim for 25–28 minutes.

Before recording: complete the 100 entity reviews; confirm the five demo expected
categories; regenerate comparison and report; visually inspect the PDF; verify
microphone, terminal font and face camera. If a requirement remains pending, say so
truthfully—the draft is not a completed submission. No video or upload has been
performed by the agent.

## Part 1 — code walkthrough (about 6 minutes)

Line references below identify actual functions in this revision. Use the editor's
line numbers; if you change code, refresh them with `rg -n '^def ' src/*.py`.

| Explain in your own words | Where to show |
|---|---|
| Read each JSONL line; separate development/evaluation; fixed selected IDs | `src/evaluate.py`: [load_jsonl():44](../src/evaluate.py#L44), [select_evaluation_ids():52](../src/evaluate.py#L52), [load_samples():71](../src/evaluate.py#L71) |
| Turkish categories, extraction rules, five-name cap; v2 JSON template added identically | `src/llm_pipeline.py`: [build_prompt():58](../src/llm_pipeline.py#L58) |
| Common request options and the single format difference | `src/llm_pipeline.py`: [build_options():95](../src/llm_pipeline.py#L95), [build_request():108](../src/llm_pipeline.py#L108) |
| Actual local HTTP POST; timeout; API response string | `src/llm_pipeline.py`: [call_ollama():123](../src/llm_pipeline.py#L123) |
| Direct parsing before cleaning; catch `json.JSONDecodeError`; retry | `src/llm_pipeline.py`: [parse_json_response():160](../src/llm_pipeline.py#L160) |
| Remove Markdown and surrounding prose; never invent fields | `src/llm_pipeline.py`: [clean_json_output():134](../src/llm_pipeline.py#L134) |
| Exact fields, seven categories and three string arrays | `src/llm_pipeline.py`: [validate_schema():173](../src/llm_pipeline.py#L173) |
| Store raw text, success flags, prediction, timing and API exceptions | `src/llm_pipeline.py`: [evaluate_response():187](../src/llm_pipeline.py#L187), [evaluate_sample():204](../src/llm_pipeline.py#L204) |
| All requests remain in metric denominators; recompute saved raw text | `src/evaluate.py`: [analyze_results():186](../src/evaluate.py#L186) |
| Turkish casing, deduplication, aliases, type preservation, TP/FP/FN | `src/evaluate.py`: [normalize_entity():91](../src/evaluate.py#L91), [match_entities():98](../src/evaluate.py#L98), [prf():123](../src/evaluate.py#L123), [entity_scores():166](../src/evaluate.py#L166) |
| Human review, save after explicit confirmation, no AI auto-verification | `src/annotate_entities.py`: [review():53](../src/annotate_entities.py#L53), [save_gold():28](../src/annotate_entities.py#L28) |
| Save each response immediately; provenance checks before comparison | `src/evaluate.py`: [run_experiment():489](../src/evaluate.py#L489), [compare_runs():284](../src/evaluate.py#L284), [check_controlled_pair():360](../src/evaluate.py#L360) |
| Plot measured percentages; regenerate English PDF from results | `src/evaluate.py`: [save_comparison_figure():452](../src/evaluate.py#L452); `src/build_report.py`: [main():192](../src/build_report.py#L192) |

Explain the difference between raw parse success, post-cleaning success and schema
validity with a saved genuine failure/recovery if present. A schema-valid category
can still be wrong. Entity precision penalizes extra names; recall penalizes missed
names. Micro-F1 sums counts before division; it does not average article F1 scores.
State the exact denominator, including failed requests.

Show `data/entity_gold.jsonl` status and reviewer metadata. Do not portray initial
candidate predictions as human annotations. If review is unfinished, show
**PENDING HUMAN REVIEW**, not a numeric F1. Prefer completing review before recording.

## Part 2 — continuous live tests (about 5–7 minutes)

Activate the environment and start the recorder with your face visible. Say the
project purpose and identify the local model. Keep the screen and voice recording
running during waiting periods. Run from the repository root:

```bash
source venv/bin/activate
ollama --version
ollama list
ollama show qwen2.5:3b
ollama ps
python src/annotate_entities.py --status
python src/demo.py --check
python src/demo.py --mode both --temperatures 0 1 --output results/video_take1.jsonl
python src/demo.py --defense --output results/defense_take1.jsonl
python src/evaluate.py --compare
```

Use fresh filenames if a take already exists. Keep required live tests in one
continuous segment. The demo makes **20 new requests** in this order:
T=0 prompt (five), T=0 schema (same five), T=1 prompt (same five), T=1 schema (same five).
It prints the news, expected label and rationale, actual raw output, parse/schema
flags, categories and entities. The defense command adds two genuine requests.
No offline fixtures or saved-response playback are used by these commands.

The five stories are fictional, newly authored Turkish examples, not copied news.
Their expected categories are initially draft: spor, kultur, saglik, teknoloji,
ekonomi. Read the texts and correct/verify them manually before recording. They
were checked against all 205 dataset records and one another using normalized
identity, long-text containment and word-sequence similarity (reject >=0.80).
This is a local novelty check, not proof about the model's pretraining corpus.

The sports-finance example (`demo05`) deliberately crosses category boundaries.
Do not promise a mistake or change its reference label to match the model. If it
is correct, explain why finance dominates; if it is wrong, point to the actual
words and taxonomy. The model may also make mistakes on a different example.
Discuss actual entity names, including omissions or wrong types, without declaring
unsupported names correct. These five examples are not the main 100-text benchmark.

Then open `results/comparison.json`, `results/temperature_comparison.json`, the plot
and the English report. Distinguish the 100-text controlled experiments from the
historical 200-response v1 run. Live reruns can differ from saved outputs, even with
seed 42; state that possibility without replacing inconvenient outputs.

## Part 3 — ten defense answers (about 12–14 minutes)

### A1 — a meaningful line, and what removing it does

- Show `request_body["format"] = JSON_SCHEMA` in `build_request()`.
- This supplies the schema to Ollama's constrained generation. The prompt asks for
  JSON in both cases, but the decoding constraint exists only with this key.
- `python src/demo.py --defense --output results/defense_take1.jsonl` creates a
  temporary copy of the real module and removes this executable statement.
  A `pass` keeps the now-empty `if` block syntactically valid; no other generation
  setting changes. Show the temporary path and request-key lists on screen.
- The original and edited modules each send a genuine request on the same example.
  Compare the actual raw response and validation flags. The output need not differ:
  removing a constraint does not guarantee invalid JSON or a category change.
- The temporary directory is cleaned up and original source bytes are checked.
  `git diff -- src/llm_pipeline.py` can confirm the demonstration did not alter it.
  Do not include this diagnostic output as part of the controlled benchmark.

### A2 — an AI suggestion that was rejected

- Use the real project history: the earlier design had a much more elaborate
  multi-experiment pipeline and additional generated artifacts. It was simplified
  because it was harder to understand and defend.
- Show `backup/pre-simplification` and the preserved history if useful:
  `git log --oneline -6` and `git show --stat backup/pre-simplification`.
- Explain why the present project keeps plain functions and JSONL instead of
  restoring that framework. The newly required comparisons have a specific purpose.
- Do not invent a quotation from an assistant, a personal reaction, or a decision
  you cannot honestly explain from your own involvement.

### A3 — a surprising result

- Choose a result you actually find surprising. One defensible candidate: prompt-only
  at T=1 had worse raw JSON parsing than T=0 (75% vs 96%) while end-to-end classification
  improved (54% vs 48%) on these 100 texts. Most format errors were recoverable.
- Another: historical schema-valid JSON was 100%, but historical category accuracy
  was only 53.5%. Syntax and semantic correctness are different targets.
- Show the saved evidence and a concrete example. Do not say a personal reaction
  was experienced if it was not. Do not generalize one run to all models.

### A4 — with and without format

- Same 100 IDs/order, v2 prompt, model digest, quantization, seed and options.
  Only format key presence changed at T=0.
- Observed T=0: prompt-only raw/clean/schema/accuracy = **96/99/98/48%**;
  schema = **100/100/100/50%**. Check current comparison after any new experiment.
- Explain that the +2 percentage-point end-to-end accuracy difference is a small
  paired observation. Show `paired_classification` to see which IDs changed.
- The 98 mutually schema-valid outputs had identical categories. The +2 points came from invalid prompt-only outputs (IDs 4811 and 2379) becoming usable and correct. The schema restricts structure and allowed labels; it does not verify facts.
  Entity accuracy effects remain unknown until reviewed gold F1 is computed.
- Historical v1 results are not a third controlled arm: prompt and sample count differ.

### B1 — n-grams versus Transformers

- An n-gram estimates the next-token probability from a fixed short context of
  n−1 preceding tokens using observed counts, often smoothing/backoff for unseen cases.
- A Transformer uses learned embeddings, attention and neural layers over the
  available context to produce logits over the vocabulary. Attention is not a
  lookup table of n-gram counts; it can combine distant contextual information.
- Both produce a distribution from which a token can be selected. Greedy selection
  chooses the maximum; sampling draws according to probabilities. Neither token
  probability nor fluent text is a guarantee of factual correctness.
- In this project constrained decoding also rules out tokens inconsistent with
  the output grammar; it does not tell the model which news category is true.

### C1 — temperature, with a real experiment (required experimental answer)

- Show the uninterrupted live T=0/T=1 requests on the same five texts, then the
  larger saved 100-text temperature comparison. This supplies the real experiment
  for the chosen defense question; do not substitute a theoretical claim.
- For positive T, sampling probabilities scale logits as softmax(logits/T).
  Increasing T flattens the relative distribution; T=0 uses greedy-style selection.
  Other sampler controls and grammar constraints still matter.
- Prompt-only measured raw parsing 96% → 75%, schema validity 98% → 99%, accuracy
  48% → 54%. Cleaning recovered many fenced/prose-wrapped outputs.
- Schema-mode raw parsing and schema validity stayed at 100%; accuracy rose 50% → 52%. Show `temperature_comparison.json`.
  Discuss what changed and what stayed stable. Do not claim temperature always
  reduces accuracy or increases hallucinations. No verified entity hallucination
  rate has been measured while gold is pending.
- Seed stays 42, but temperature changes the probability distribution. One seed
  and one realization do not establish a universal effect or uncertainty bounds.

### D1 — actual quantization and verification

- Show `ollama show qwen2.5:3b`: **Q4_K_M**. Show `/api/show` details saved in
  `results/environment.json` and run metadata; the tag alone is not evidence.
- Show full digest and Ollama version **0.40.2**. Quantization uses reduced-precision
  weight representations to reduce storage/memory; the tradeoff can affect quality.
- Q4_K_M is a named mixed quantization configuration, not a promise that every
  parameter and computation uses exactly four bits. Do not invent tensor-level details.
- Model context capacity shown by `ollama show` is different from our configured
  runtime `num_ctx=4096`. Hardware/versions may change outputs even at a fixed seed.

### E1 — Turkish versus English token counts

- Tokens are tokenizer vocabulary units, not necessarily words or characters.
  Turkish's productive suffix combinations can yield many surface forms that split
  into several subwords. Vocabulary/training frequencies also affect segmentation.
- Equivalent English and Turkish texts may therefore use different token counts;
  Turkish can require more but **not always**. A short common Turkish word may be
  represented efficiently, while a rare English string may fragment.
- We did not run a paired translation/tokenizer benchmark. `prompt_eval_count`
  records actual whole-prompt counts, not proof of a language-wide ratio.

### F4 — what if the prompt were English?

- A different instruction language could change instruction following and how
  categories are interpreted because model training is multilingual and uneven.
  Keeping Turkish input/output labels while translating instructions may introduce
  subtle changes in meaning.
- This is a hypothesis; an English-prompt ablation was **not run**. Do not claim
  English or Turkish is superior from these measurements.
- A fair test would freeze texts, model, seed, options and mode, change only an
  equivalent reviewed translation, then compare formatting, category accuracy and
  verified entity F1. Keep those results separate from the primary format experiment.

### G1 — could TF-IDF + Logistic Regression beat this LLM?

- Yes, it is plausible on supervised news categories with distinctive vocabulary,
  adequate labeled training data and a representative independent test split.
  It could be faster and cheaper. This is not a measured benchmark in this repository.
- Avoid train/test overlap, near duplicates and label leakage. Fit vocabulary/IDF
  on training data only; tune on validation data; report on the same held-out texts.
- The local LLM here is prompted without task-specific supervised training. A
  supervised baseline has different data access and should be described honestly.
- Plain TF-IDF + Logistic Regression classifies documents; it does not by itself
  return person/organization/location spans. Entity extraction needs another method.

## Description chapters and final manual actions

These are **planned chapter times**, not actual timestamps. Replace them after
recording, ensuring the first chapter starts at 00:00 and chapters follow the video:

```text
00:00 Introduction, face camera and objective
01:00 Dataset, model and reproducibility
03:00 Code walkthrough
09:00 Continuous live tests: modes and temperatures
15:00 A1 temporary-copy experiment and A2–A4
20:00 B1 and experimental temperature defense C1
23:00 D1, E1, F4 and G1
27:00 Results, limitations and completion status
```

Review all ten answers and keep total duration below 30 minutes. Upload the genuine
recording to YouTube with visibility **Unlisted**, add accurate chapters and repository
link, and check playback/access in a signed-out window. Submit the English PDF and
video URL through the course's actual submission channel. Do not claim upload or
submission until you have done them. Deadline: 22 November 2026, 23:59 Türkiye time.

## Observed rehearsal evidence (not a recorded submission)

The genuine 20-request rehearsal is saved in `results/demo_rehearsal.jsonl`.
All raw JSON and schemas passed. The first four proposed labels matched; demo05
was `spor` in every mode/temperature against draft `ekonomi`. Human confirmation
of the expected labels is still required. In the A1 rehearsal, the request lost
`format` but both predictions remained `spor`; this is an honest example of a
changed mechanism without a changed prediction. Do not promise identical behavior
on the next live run, or replay these files as if they were new requests.
