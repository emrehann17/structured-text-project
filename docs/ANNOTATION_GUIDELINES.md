# Manual entity annotation

Start from empty fields. Select names directly from each article, or type a name
in the appropriate person/organization/location field and press Enter or Ekle.
Typed names must also occur in the article; they follow the same rules as selected
names. Added names are highlighted in the article: people in blue, organizations
in green and locations in yellow. Highlights update when names are added or removed,
and are restored from your saved lists when revisiting an article. Only your own
saved selections are displayed when revisiting an article. Read the whole article,
check omissions and explicitly save it. Do not generate labels with an AI tool.
An empty list is a valid annotation only after you have checked the text.

## What to select

- **Person:** a named real person. Exclude titles, roles and fictional characters.
- **Organization:** companies, institutions, parties, universities, agencies,
  sports clubs and national teams. Products and events are excluded.
- **Location:** geographic places, countries, cities, regions and physical venues.
  A country standing for its national team is an organization; a geographic country
  is a location. Nationality adjectives are not place names.
- A venue acting as an institution is an organization; a venue used as a place is
  a location. Choose the contextual type.
- Select the longest explicit name at a mention, without its title or grammatical
  suffix. Do not infer a full name or expand abbreviations from outside knowledge.
- Include a short name separately if it occurs separately in the text. For example,
  if both a full institution name and its abbreviation occur independently, select
  both. This task measures named surface forms, not real-world identity linking.
- Do not extract an internal city/person name from a longer organization name
  unless it also occurs independently. Add each distinct form once per type.
- Annotate **all** qualifying forms; there is no limit of five and no alias syntax.
  The interface allows selecting just the name within an inflected word.

The displayed article replaces dataset underscores with spaces for readability.
The original text is retained; scoring applies the same space normalization.

## Saving and scoring

Enter your real name and use the completion button for each article. The program
stores `annotation_method="manual_from_text"`, `status="completed"`, reviewer,
time and a source-text hash. Until then the record is `draft`, even if its lists are
empty. These fields document your action; software cannot establish whether you
read the article carefully.

Every saved correction rebuilds scores, the plot and the report. No numeric entity
F1 is released until all 100 annotations are complete. For edits made directly to
the JSONL file, run `python src/build_report.py` before using any result.

Matching: NFC Unicode normalization, replace `İ` with `i` and `I` with `ı`, then
lowercase; replace underscores with spaces and collapse whitespace. Preserve other
punctuation and entity type. Compare exact sets of normalized forms per article.
Wrong types produce FP and FN. Unsupported names are FP; missed names are FN.
Unusable model responses have no predicted entities. Micro precision/recall/F1
sum TP/FP/FN over all articles/types; zero denominators give zero.

This is a single-annotator study. Do not claim blinded annotation or agreement
between independent annotators. Do not change a label just to agree with a model.
