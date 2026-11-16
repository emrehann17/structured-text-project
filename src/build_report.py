"""Generate the English Markdown/PDF from saved real results; never performs inference."""
import html
import json
from pathlib import Path
import re

from evaluate import ROOT, compare_runs, load_gold, gold_status, load_samples


def report_markdown(comparison, temperature):
    env = json.loads((ROOT / 'results/environment.json').read_text(encoding='utf-8'))
    a, b = comparison['prompt_only'], comparison['schema_constrained']
    runs = temperature['runs']
    progress = gold_status([s['id'] for s in load_samples()], load_gold())
    pending = not progress['complete'] or any('total_requests' not in r for r in runs.values())
    status = ('DRAFT — required experiments pending' if any('total_requests' not in r for r in runs.values()) else 'DRAFT — entity gold pending human review') if pending else 'Measured report — human gold verified'
    metrics = [('Raw JSON parsing','raw_json_success'), ('Parsing after cleaning','clean_json_success'),
               ('Schema validity','schema_success'), ('Classification accuracy','classification_accuracy')]
    def value(run, key):
        return (f"{run[key + '_count']}/{run['total_requests']} ({run[key + '_pct']:g}%)"
                if 'total_requests' in run else 'PENDING RUN')
    table = '| Metric | Prompt-only, T=0 | Schema, T=0 |\n|---|---:|---:|\n'
    for label, key in metrics:
        table += f'| {label} | {value(a,key)} | {value(b,key)} |\n'
    def f1(run):
        scores=run.get('entity_f1')
        return f"{scores['micro']['f1_pct']:g}%" if isinstance(scores,dict) else 'PENDING HUMAN REVIEW'
    table += f'| Entity micro-F1 | {f1(a)} | {f1(b)} |\n'
    temp_table='| Mode, temperature | n | Raw JSON | Schema | Accuracy |\n|---|---:|---:|---:|---:|\n'
    for name, run in runs.items():
        label=('Prompt' if name.startswith('prompt') else 'Schema') + (', T=1' if name.endswith('temp1') else ', T=0')
        if 'total_requests' in run:
            temp_table += f"| {label} | {run['total_requests']} | {run['raw_json_success_pct']:g}% | {run['schema_success_pct']:g}% | {run['classification_accuracy_pct']:g}% |\n"
        else:
            temp_table += f'| {label} | PENDING | PENDING | PENDING | PENDING |\n'
    discussion='The primary comparison is pending; no semantic effect can yet be inferred.'
    if 'paired_classification' in comparison:
        paired=comparison['paired_classification']
        delta=b['classification_accuracy_pct']-a['classification_accuracy_pct']
        discussion=(f"Schema decoding changed end-to-end classification accuracy by {delta:+g} percentage points "
                    f"on these 100 texts. Both modes were correct on {paired['both_correct']}, only prompt-only "
                    f"on {paired['only_first_correct']}, only schema on {paired['only_second_correct']}, and both "
                    f"wrong on {paired['both_wrong']}. Predictions agreed on {paired['same_prediction']}/100. "
                    f"Among {paired['both_schema_valid']} outputs valid in both modes, "
                    f"{paired['different_prediction_when_both_valid']} category decisions differed. "
                    "Separate usable-output gains from changed decisions; neither establishes a general semantic advantage.")
    temp_discussion=[]
    for base in ('prompt_only','schema_constrained'):
        zero, one=runs[base],runs[base+'_temp1']
        if 'total_requests' in zero and 'total_requests' in one:
            temp_discussion.append(f"For {base.replace('_',' ')}, T=0 to T=1 changed raw parsing "
                f"{zero['raw_json_success_pct']:g}% to {one['raw_json_success_pct']:g}%, schema validity "
                f"{zero['schema_success_pct']:g}% to {one['schema_success_pct']:g}%, and accuracy "
                f"{zero['classification_accuracy_pct']:g}% to {one['classification_accuracy_pct']:g}%.")
    entity_table='Entity precision, recall and per-type/overall F1: PENDING HUMAN REVIEW.'
    if all(isinstance(run.get('entity_f1'),dict) for run in (a,b)):
        entity_table='| Mode / type | Precision | Recall | F1 |\n|---|---:|---:|---:|\n'
        for name,run in [('Prompt',a),('Schema',b)]:
            for kind,score in run['entity_f1'].items():
                entity_table+=f"| {name} / {kind} | {score['precision_pct']:g}% | {score['recall_pct']:g}% | {score['f1_pct']:g}% |\n"
    return f'''# Structured Text Classification & Information Extraction

NLP Project I — November 2026 — English submission report

**{status}.** Human entity review: {progress['verified']}/{progress['selected']}. Deadline: 22 November 2026, 23:59 Türkiye time.

## 1. Introduction and objective

A local Qwen LLM converts Turkish news into a category and three named-entity lists. The objective is to separate reliable JSON formatting from correct information. The primary experiment changes only Ollama's format parameter; a supplementary experiment changes only temperature within each mode. No cloud inference, training or fine-tuning is used.

## 2. Dataset, model and setup

The frozen TTC4900 file contains 205 records: five development and 200 historical evaluation records (199 distinct texts). The November evaluation selects 100 distinct texts without looking at new model outputs: scan the 200 records in stored order, skip selected duplicate texts, and fill category quotas. Alphabetically first dunya and ekonomi receive 15 each; kultur, saglik, siyaset, spor and teknoloji receive 14 each. IDs and selection rules are saved in data/evaluation_ids.json. This balanced subset is not an estimate of natural news prevalence.

Exact model tag: **{env['model']}**; architecture qwen2; installed quantization **{env['details']['quantization_level']}**, read from Ollama /api/show and checked with ollama show. Ollama **{env['ollama_version']}**; Python **{env['python']}**; GPU: {env['gpu']}. Linux/WSL2 environment and model template/system prompt are captured in results/environment.json. Full model digest: {env['model_digest']}.

All runs use seed=42, num_ctx=4096, num_predict=384, repeat_penalty=1.2, repeat_last_n=128 and stream=false. Primary temperature=0; supplementary temperature=1.0. top_k and top_p are **not explicitly set**; runtime/model defaults apply. HTTP connection/read timeouts are 5/60 seconds. Per-run metadata captures software, model and hardware before and after execution; per-response hashes identify prompt, schema and source text.

## 3. Methodology

build_prompt() retains the Turkish task and adds a minimal explicit JSON object template (v2). This essential correction gives prompt-only mode the field names absent from v1; preserved five-record development outputs with v1 had no schema-valid response. Both new arms use identical v2 prompts and samples in the same order. Prompt-only omits the format key entirely; schema mode sends JSON_SCHEMA. The schema requires exactly category and entities, an allowed category and person/organization/location string arrays; it rejects extra fields. The prompt's five-name cap is not a schema constraint.

parse_json_response() first calls json.loads(raw_output). A JSONDecodeError triggers Markdown/explanation removal, then a second parse. No facts, missing fields or closing braces are invented. A complete nested object recovered from truncated text must still pass validate_schema(). evaluate_sample() saves the untouched raw output and records HTTP, timeout or envelope errors without stopping later samples.

<!-- pagebreak -->

## 4. Experimental results

These tables are recomputed from the fresh saved responses, not from historical success flags. All four rates divide successful records by **all 100 requests per condition**, including API, parsing and schema failures. Post-cleaning success includes direct successes and recovered responses. Correct classification requires a schema-valid output whose category equals the TTC4900 label. This is end-to-end accuracy; structural failure counts as incorrect.

{table}

{discussion}

### Controlled temperature experiment

The same 100 texts are used at both temperatures in both modes (400 requests). Seed, prompt, model and other options remain fixed within each pair.

{temp_table}

{f"At T=0 then T=1, prompt-only raw parsing was {runs['prompt_only']['raw_json_success_pct']:g}% then {runs['prompt_only_temp1']['raw_json_success_pct']:g}%, and accuracy was {runs['prompt_only']['classification_accuracy_pct']:g}% then {runs['prompt_only_temp1']['classification_accuracy_pct']:g}%. Schema accuracy was {runs['schema_constrained']['classification_accuracy_pct']:g}% then {runs['schema_constrained_temp1']['classification_accuracy_pct']:g}%. These observations do not establish a general temperature effect." if len(temp_discussion)==2 else 'Temperature runs are PENDING.'}

![Measured formatting and classification rates; pending F1 is not a zero score.](../results/figures/mode_temperature_comparison.png)

<!-- pagebreak -->

## 5. Entity evaluation, discussion and limitations

TTC4900 supplies class labels, not verified entity labels. data/entity_gold.jsonl contains historical-model suggestions explicitly marked candidate. The terminal helper displays the original text, lets a human edit every list, and saves verified status only after explicit confirmation with reviewer, timestamp and source hash. Current verification: **{progress['verified']}/100**. No entity score is released until all selected gold records are verified. Suggestions can bias review; the reviewer must also check omissions.

Match names by NFC-normalized exact equality, mapping Turkish İ to i and I to ı before lowercasing, replacing underscores with spaces and collapsing whitespace. Retain punctuation and entity type. Group explicit aliases into one gold entry; aliases must not overlap between gold entities. Deduplicate identical predictions and allow at most one prediction per gold entity. Wrong types count as FP and FN. Invalid outputs provide empty prediction sets. Per-type and micro scores use P=TP/(TP+FP), R=TP/(TP+FN), F1=2PR/(P+R); zero denominators give zero. Micro counts are summed over all texts and types before division.

Gold uses the first five distinct supported entities per type in order of first mention, keeping aliases together. This matches the output cap, but the prompt does not specify which five; alternative valid choices can lower exact-match scores. Full annotation rules cover titles, institutions, geographic names, suffixes and overlaps in docs/ANNOTATION_GUIDELINES.md.

{entity_table}

Valid JSON does not prove semantic correctness. The saved predictions include sports/economy and international-politics boundary confusions; reference labels and the prompt taxonomy need not agree perfectly. Schema constraints restrict possible outputs but do not establish entity truth. Entity accuracy effects remain unknown until review is complete. A fixed seed does not remove runtime nondeterminism; temperature findings describe one realization per condition, not a universal trend. Quantization, software, hardware and prompt changes can affect reproducibility. Model pretraining overlap with TTC4900 is unknown.

Historical evidence is separate: the preserved 200-response v1 schema run achieved 200/200 raw and schema-valid outputs, 107/200 correct categories (53.5%), and no API errors. It uses a different prompt and selection, so it is not a controlled baseline for these tables. The first fresh prompt run resumed after an application restart at 35 records; provenance was checked and no saved output was replaced. Timings exclude that interruption. Earlier uncommitted partial runs remain archived, excluded from this comparison.

### Reproduction and submission status

Run python src/evaluate.py --compare to recalculate comparisons/plots, then python src/build_report.py to regenerate this report. New inference requires --run, a mode, a temperature and a new result filename; README gives exact commands. Offline tests exercise HTTP mocks only. src/demo.py sends genuine live requests on five new fictional Turkish examples; expected categories require student confirmation. Human annotation, final PDF review after F1, English recording and Unlisted YouTube upload remain student actions. The current draft does not claim assignment completion.

Dataset source recorded by the original project: [savasy/ttc4900](https://huggingface.co/datasets/savasy/ttc4900). Interface reference: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs). Course page was unavailable to the agent; the user-supplied November requirements were followed. Evidence and backup details: docs/UPGRADE_EVIDENCE.md.
'''


def render_pdf(markdown, destination):
    """Small Markdown subset used by this report: headings, paragraphs, tables, image, page breaks."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    font_dir=Path('/usr/share/fonts/truetype/dejavu')
    if font_dir.exists():
        pdfmetrics.registerFont(TTFont('Report',str(font_dir/'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('ReportBold',str(font_dir/'DejaVuSans-Bold.ttf')))
    else:
        import reportlab
        font_dir=Path(reportlab.__file__).parent/'fonts'
        pdfmetrics.registerFont(TTFont('Report',str(font_dir/'Vera.ttf')))
        pdfmetrics.registerFont(TTFont('ReportBold',str(font_dir/'VeraBd.ttf')))
    pdfmetrics.registerFontFamily('Report',normal='Report',bold='ReportBold',italic='Report',boldItalic='ReportBold')
    styles=getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName='Report'; style.fontSize=9; style.leading=12
    for name,size in [('Title',16),('Heading2',12),('Heading3',10)]:
        styles[name].fontName='ReportBold'; styles[name].fontSize=size; styles[name].leading=size+3
    styles['BodyText'].spaceAfter=6
    def inline(text):
        text=html.escape(text)
        text=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',text)
        text=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'<link href="\2" color="#226080">\1</link>',text)
        return text
    story=[]
    blocks=markdown.strip().split('\n\n')
    for block in blocks:
        if block=='<!-- pagebreak -->': story.append(PageBreak())
        elif block.startswith('!['):
            match=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',block)
            image_path=(ROOT/'report'/match[2]).resolve()
            if image_path.exists():
                story.append(Image(str(image_path),width=500,height=233))
        elif block.startswith('|'):
            rows=[line.strip('|').split('|') for line in block.splitlines()]
            rows=[row for row in rows if not all(re.fullmatch(r'\s*:?-+:?\s*',c) for c in row)]
            table=Table([[Paragraph(inline(c.strip()),styles['BodyText']) for c in row] for row in rows],
                        colWidths=[500/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f0f3')),
                                      ('GRID',(0,0),(-1,-1),.3,colors.lightgrey),('VALIGN',(0,0),(-1,-1),'TOP'),
                                      ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,8)])
        else:
            style='BodyText'
            for prefix,name in [('### ','Heading3'),('## ','Heading2'),('# ','Title')]:
                if block.startswith(prefix): style=name; block=block[len(prefix):]; break
            story.append(Paragraph(inline(block.replace('\n',' ')),styles[style]))
    doc=SimpleDocTemplate(str(destination),pagesize=A4,leftMargin=47,rightMargin=47,topMargin=35,bottomMargin=35)
    def footer(canvas,document):
        canvas.setFont('Report',8)
        canvas.drawString(47,20,'NLP Project I | English report | see review status on page 1')
        canvas.drawRightString(A4[0]-47,20,str(document.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    if doc.page > 4:
        raise ValueError(f'Report has {doc.page} pages; shorten before submission')
    print(f'Generated {destination}: {doc.page} pages. Visually inspect before submission.')


def main():
    comparison, temperature=compare_runs()
    markdown=report_markdown(comparison,temperature)
    (ROOT/'report/technical_report.md').write_text(markdown,encoding='utf-8')
    render_pdf(markdown,ROOT/'report/technical_report.pdf')


if __name__=='__main__': main()
