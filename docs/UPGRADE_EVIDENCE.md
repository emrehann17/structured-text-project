# Upgrade provenance — 16 November 2026

The supplied assignment requirements are the implementation checklist. Fetching
https://uorhan.github.io/files/NLP-Project-1 and its `.html` variant failed in the
web tool. No additional course rules were inferred.

## Before changes

- Branch: `main`, HEAD `a896e34` (markdown update).
- Working tree was already dirty: pipeline, evaluator and tests were modified;
  selection, annotation helper, guidelines, environment evidence, development
  checks and partial experimental outputs were untracked.
- Preserved `backup/pre-simplification` and the existing
  `backup/pre-nov2026-upgrade-branch`.
- Created `backup/pre-nov2026-upgrade-20261116` at the original main HEAD.
- A working-directory snapshot, including pre-existing uncommitted work, was
  saved to `/tmp/structured-text-pre-upgrade-20261116.tar.gz` (temporary local
  recovery copy; not a permanent submission artifact).
- Existing 100 prompt / 55 schema responses and environment were moved intact
  into `results/prior_upgrade/`. They lack per-response digest evidence and are
  excluded from the final controlled comparison. Development logs remain in
  `results/dev_checks/`; their outputs are not new measurements from this turn.

Frozen SHA-256 values (also enforced by tests):

```text
2a5b6818b3251c5552806ef000eaf4be723cf226e6c96f60b27b001408b128bc  data/test_samples.jsonl
6261136ce0ce69c3964ddea4a2548b7afa027996a79d445b046c0a0453579057  results/optimized_schema_results.jsonl
```

The historical `results/summary.json` is also retained. Historical accuracy is
107/200 = 53.5%, with all 200 raw and schema-valid outputs and zero API errors.
It is not an arm of the November comparison.

## Essential prompt correction

The original prompt says to follow a schema but never supplies the JSON object's
key structure in the text. In prompt-only mode the model cannot see the schema
through the API. The pre-existing development file
`original_prompt_no_format_dev5.jsonl` contains five original-prompt outputs,
none schema-valid; it supports making the structure explicit. Version v2 appends:

```text
ÇIKTI BİÇİMİ (yalnızca bu yapıda tek bir JSON nesnesi döndür):
{"category": "<kategori>", "entities": {"person": [], "organization": [], "location": []}}
```

This correction was already present in the dirty working tree and is retained.
`build_prompt(text, "v1")` preserves the original prompt. Both new arms use v2;
the only primary request difference is the presence of `format=JSON_SCHEMA`.
Do not attribute differences from the historical 200-record run solely to format:
its prompt and evaluation selection differ. No post-evaluation prompt tuning was
performed during this upgrade.

## New evidence

Each fresh result records mode, temperature, options, prompt/schema/text hashes,
model digest, quantization, environment fingerprint and UTC recording time.
Each `.metadata.json` captures environment before and after inference. Missing
or changed provenance blocks comparison. Model tag alone is insufficient.

The first fresh prompt-only run was interrupted by an application server restart
after 35 saved responses. It resumed at record 36 only after checking the exact
ID prefix, environment, options and content fingerprints. The metadata records
resumption; no completed response was replaced and no failures were retried.
The run's elapsed times exclude the interruption. A seed and temperature zero do
not guarantee bit-identical responses across sessions or hardware.

Annotation suggestions are from the frozen historical model output and remain
`candidate` until an actual human reviews them. No AI output is designated as
verified gold. Demo stories are explicitly fictional, newly authored examples;
their proposed categories also require student review before the final video.

## Actual rehearsal (not the student's recorded video)

`results/demo_rehearsal.jsonl` contains 20 real Ollama responses: the five new
stories in both modes at T=0 and T=1. All parsed and validated, with zero API
errors. The first four matched their proposed categories. The sports-finance
story was predicted `spor` in all four settings, against the still-unverified
proposed `ekonomi` reference. This is not yet human-verified demo accuracy.
`results/defense_rehearsal.jsonl` contains two real requests from the A1 temporary
copy experiment: `format_sent` changed true→false, while both predictions stayed
`spor`. The student must make fresh requests on screen for the final recording.

## Final validation before commit

- 37 offline unit tests passed (`python -m unittest discover -s tests -v`).
- Four complete matched runs: 100 prompt T=0, 100 schema T=0, 100 prompt T=1,
  100 schema T=1; zero API errors. Model/configuration comparison checks passed.
- The v1 prompt, original schema and generation options were compared directly
  with the pre-upgrade Git version and match exactly.
- Frozen dataset, historical 200 responses and historical summary were compared
  byte-for-byte with the backup branch and remain unchanged.
- English PDF generated from saved outputs: **3 pages**, all visually inspected
  for readable text/tables, intact margins and chart clipping. It is a draft
  because entity gold remains **0/100 verified**.
- The five demo texts passed exact/near-duplicate checks; maximum observed
  word-sequence similarity to source/prior demo texts was 0.0674 (threshold 0.80).
- No student video, voice/face recording, YouTube upload or course submission has
  been made. Those actions and genuine human annotation remain pending.
