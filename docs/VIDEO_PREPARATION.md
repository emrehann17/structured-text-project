# English video preparation

Use these prompts to understand and explain your own work, not as a script to
read aloud. Confirm the current report has 100 completed manual annotations and
400 requests before recording. Inspect the five demo reference categories yourself.
All numerical answers must come from the current report or current live output.

## Code walkthrough — starts at 00:00

Show your face at the beginning; explain the objective and then walk through:

1. `data/news.jsonl` and `evaluate.load_samples`: 100 articles, source IDs and categories.
2. `annotate_entities.save_annotation`: your manually selected or typed names, entity types,
   completion status and the current annotation progress. No model supplies labels.
3. `llm_pipeline.build_prompt` and `build_request`: categories, all entities, JSON
   template, common options; only schema mode sends `format`.
4. `call_ollama`: actual local HTTP request. Show the recorded model tag, digest,
   quantization and version; distinguish context size from output token limit.
5. `parse_json_response`, `clean_json_output`, `validate_schema`: direct parse,
   exception, cleaning, retry and type checks. Show an actual failure/recovery
   from your saved outputs if one exists.
6. `analyze_results`, `match_entities`, `prf`: all-request denominator, category
   accuracy, Turkish normalization, exact sets, TP/FP/FN and micro-F1.
7. `build_report.rebuild`: recomputes metrics/plot/report from current gold. Changing
   gold changes the evaluation; the program does not retain old F1 values.

## Live tests — uninterrupted from execution through output

Run the following using the reported model/parameters:

```bash
ollama --version
ollama show qwen2.5:3b
ollama ps
python src/demo.py --output results/live_video.jsonl
```

Choose a new output filename if it exists. This sends 20 new local requests:
five new texts at T=0 prompt/schema, then the same five at T=1 prompt/schema.
Keep screen and voice recorded during waiting periods. Discuss actual raw JSON,
parsing/schema flags, category and entities. The sports-finance story is deliberately
challenging; explain why you expected a mistake, even if this run is correct.
Do not replay a saved file as if it were live inference.

## Ten defense answers

- **A1:** Show the normalization line in `evaluate.normalize_entity`:
  `name = name.replace("İ", "i").replace("I", "ı").lower().replace("_", " ")`.
  Run `python src/demo.py --defense` on screen. It removes exactly that evaluation
  line in a temporary file and recalculates matching. Explain the labeled teaching
  example separately from dataset results. The line combines Turkish casing,
  lowercasing and underscores-to-spaces; the experiment does not isolate just one.
  NFC and whitespace collapsing stay. The model outputs did not change.
- **A2:** Explain an actual suggestion you rejected and why. One real design choice
  in this project is replacing the assistant-proposed annotation workflow with
  your own direct selections and simplifying the code. Describe your own decision;
  do not invent a conversation or pretend you wrote every line without assistance.
- **A3:** Choose a current result that actually surprised you. Show the relevant
  metric and a concrete sample, then explain possible reasons without claiming proof.
- **A4:** Use current T=0 raw/clean/schema/accuracy/F1 and paired category counts.
  Does the format constraint change category decisions, recover unusable outputs,
  or change entity extraction? Valid JSON alone cannot establish correct facts.
- **B1:** N-grams estimate next-token probabilities from a fixed short context of
  observed sequences. Transformers use embeddings, attention and learned layers
  over available context to produce logits. Selection can be greedy or sampled.
- **C1 (experimental answer):** Use the live T=0/T=1 comparison plus the 100-text
  table. For positive T, probabilities depend on softmax(logits/T). Higher T changes
  sampling; report what happened to formatting, accuracy and F1 in your results.
  Do not assume every metric must move in the same direction or generalize one seed.
- **D1:** Show actual quantization using `ollama show` and saved run metadata.
  Explain the memory/precision tradeoff. A tag alone is not proof; Q4_K_M does not
  mean every tensor and computation uses exactly four bits.
- **E1:** Turkish suffix combinations and tokenizer vocabulary can split equivalent
  meanings into more pieces than English. This is not universal. Whole-prompt token
  counts do not show how a particular word is segmented.
- **F4:** Discuss English versus Turkish instructions as an untested hypothesis.
  A fair comparison would translate instructions while fixing data/model/options,
  and compare formatting, classification and entity F1. Do not invent a result.
- **G1:** TF-IDF + logistic regression could beat this prompted LLM with sufficient
  representative labeled training data. Fit on training data, tune on development
  data and evaluate on held-out texts. No classical baseline is claimed here;
  document classification alone is not entity extraction.

A1 is an offline code experiment. C1 supplies an experiment for the selected
parameter question using real live requests. Speak naturally in your own words.

## Recording and submission

- Maximum 30 minutes, in English. Screen and voice throughout; face visible initially.
  You may join parts, but live tests must run uncut from execution to output.
- Verify your YouTube account for videos over 15 minutes at
  [youtube.com/verify](https://www.youtube.com/verify) before recording.
- Add actual chapters after recording. The structure is:

```text
00:00 Code walkthrough
[actual time] Live tests
[actual time] Defense questions
```

- Upload **Unlisted**, not Private or Public. Keep it available until final grades.
- Share documented Python scripts and the PDF (maximum four pages) through a
  viewable GitHub repository or Drive folder with “Anyone with the link can view”.
  Check both code/report and video links while signed out.
- Submit **once** through the instructor's actual form, not by email, by
  **22 November 2026, 23:59**. Include video URL, code/report link, and live-test
  and defense start times. The supplied text does not contain the actual form URL.
- Do not modify submitted code or report after the deadline. Week 15 oral exam
  responsibility includes **all** defense questions of Projects I–III.
