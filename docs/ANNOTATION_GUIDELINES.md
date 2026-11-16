# Human entity review

`data/entity_gold.jsonl` has one record for each selected ID. The initial lists are
**unverified historical Qwen predictions**, not manually annotated gold. They may
contain wrong types, omissions and invented names. `candidate_source` and the
original results hash retain this provenance. Never accept a list just because
it was suggested; read the complete source article and check every type.

## Workflow

```bash
python src/annotate_entities.py --status
python src/annotate_entities.py --reviewer "Your real name"
python src/annotate_entities.py --reviewer "Your real name" --id 4000
python src/evaluate.py --compare
```

The terminal shows the full original text (including its underscores). Enter
keeps a list; `-` empties it; `name; another name` replaces it. `full name | alias`
groups aliases of ONE entity. Only an explicit human `y` verifies a record.
Ctrl-C stops with previously verified records saved; an unfinished record is not
saved. Use `--id` to revisit a record. Reviewer, UTC time and source text SHA-256
are stored. Do not pipe automated `y` answers into this tool.

F1 is **PENDING HUMAN REVIEW** until every ID in the analyzed run is verified.
No partial score is presented as a final score. The helper can enforce metadata,
but only the reviewer can establish that the labels were actually read carefully.

## Consistent labeling policy

- Person: a named real individual, not a title, role or fictional character.
- Organization: named companies, institutions, parties, clubs, national sports
  teams, universities and agencies. Products and events are not organizations.
- Location: named geographic places, countries, cities, regions and physical
  venues. A country remains a location when acting politically. Nationality
  adjectives are not locations.
- A venue acting as an institution is an organization; a venue used as a place is
  a location. Choose its contextual role consistently. A club is an organization,
  not an additional mention of the city in its name.
- Do not infer names absent from the text. A source agency such as `aa` is an
  organization if explicitly present. Do not expand abbreviations using outside
  knowledge; accept expanded names only when they occur in the text.
- Keep the most complete surface form actually present, stripping grammatical
  case suffixes. No fuzzy matching, automatic suffix stripping or translation is
  performed by the scorer. Preserve meaningful punctuation in names.
- Group repeated mentions and explicit aliases into a single entry using `|`.
  No alias may belong to two different entries within a type. For ambiguous
  shared surnames, retain unambiguous forms only. Nested organizations are not
  split into extra locations unless the location occurs independently.
- **Maximum five distinct entities per type**, matching the model's output cap.
  When there are more, retain the first five distinct entities in order of first
  mention. Later aliases can enrich those entries. Record a note about capping.
  This fixed convention avoids selecting gold after seeing new predictions.
  The prompt does not prescribe which five to choose, so alternative legitimate
  choices can lower measured recall; discuss this limitation.

## Matching and denominators

NFC Unicode normalization; `İ→i`, `I→ı`, then lowercase; underscores become spaces;
whitespace collapses. Punctuation is retained to avoid merging different names.
Matching is exact after normalization and within the same type. Identical
normalized predictions are deduplicated; each gold entity matches at most one
prediction. Predicting two different aliases for the same entity gives one TP
and one FP. Wrong-type entities give an FP in the predicted type and an FN in
the gold type. Gold aliases must be disjoint, avoiding ambiguous greedy matches.

Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2PR/(P+R).
A zero denominator gives zero. Micro scores sum TP, FP, FN over every selected
sample and all three types before division; per-type scores use the same rule
within a type. API errors and schema-invalid responses supply empty prediction
sets, so all their gold entities are FNs. Numeric results are percentages.
These are end-to-end scores, conditional on schema validation for usable output.

Reviewing model suggestions may bias the annotator. Check omissions against the
text, and if possible ask a second person to review ambiguous cases. No second
review or inter-annotator agreement has been claimed.
