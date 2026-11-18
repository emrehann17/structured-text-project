"""Rebuild metrics, chart and report together from current raw outputs and manual gold."""
import argparse
import html
import json
from os.path import relpath
from pathlib import Path
import re

import llm_pipeline as pipeline
from evaluate import ROOT, RUNS, compare_runs, load_gold


def report_markdown(results, directory):
    runs, progress = results["runs"], results["entity_gold"]
    finished = [r for r in runs.values() if "total_requests" in r]
    requests = sum(r["total_requests"] for r in finished)
    pending = ([] if progress["complete"] else ["manual annotation"])
    if len(finished) != 4:
        pending.append("experiments")
    status = "INCOMPLETE — pending " + " and ".join(pending) if pending else "Evaluation complete"
    environment = None
    for filename, _, _ in RUNS.values():
        meta = directory / Path(filename).with_suffix(".metadata.json")
        if meta.exists():
            environment = json.loads(meta.read_text())["environment"]
            break
    setup = "Model tag: qwen2.5:3b. Runtime version, quantization and hardware will be recorded when experiments run."
    if environment:
        setup = (f"Model tag: **{environment['model']}**; quantization **{environment['details']['quantization_level']}**; "
                 f"Ollama **{environment['ollama_version']}**; Python {environment['python']}; GPU: {environment['gpu']}. "
                 f"Model digest: {environment['model_digest']}. Per-run metadata saves the model template, system message and environment before/after execution.")
    options = ', '.join(f"{key}={json.dumps(value)}" for key, value in pipeline.OPTIONS.items())
    table = '| Mode / T | n | Raw JSON | Clean JSON | Schema | Accuracy | Entity F1 |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for name, (_, mode, temperature) in RUNS.items():
        run = runs[name]
        label = f"{mode}, {temperature:g}"
        if 'total_requests' not in run:
            table += f'| {label} | Pending | — | — | — | — | Pending |\n'
            continue
        rates = [f"{run[k + '_pct']:g}%" for k in ('raw_json_success','clean_json_success','schema_success','classification_accuracy')]
        f1 = run['entity_f1']
        rates.append(f"{f1['micro']['f1_pct']:g}%" if isinstance(f1,dict) else 'Pending')
        table += '| ' + ' | '.join([label,str(run['total_requests']),*rates]) + ' |\n'
    discussion = 'The mode comparison is pending.'
    paired = results['paired_classification']
    if paired:
        a,b = runs['prompt_only'],runs['schema_constrained']
        difference = b['classification_accuracy_pct'] - a['classification_accuracy_pct']
        discussion = (f"At T=0 schema changed end-to-end category accuracy by {difference:+g} percentage points. "
                      f"Among {paired['both_schema_valid']} outputs valid in both modes, "
                      f"{paired['different_prediction_when_both_valid']} category predictions differed. "
                      f"Only prompt was correct on {paired['only_first_correct']} texts, only schema on {paired['only_second_correct']}. "
                      "A structural recovery can improve usable-output accuracy without changing category decisions on mutually valid outputs.")
        if difference == 0:
            discussion += " Here, better formatting added no net correct category decisions. The schema restricts allowed forms and labels; it does not identify the reference category."
    temperature_discussion = []
    for name in ('prompt_only', 'schema_constrained'):
        low, high = runs[name], runs[name + '_temp1']
        if 'total_requests' in low and 'total_requests' in high:
            temperature_discussion.append(
                f"For {name.replace('_', ' ')}, T=0 to T=1 changed raw parsing "
                f"{low['raw_json_success_pct']:g}% to {high['raw_json_success_pct']:g}% and "
                f"category accuracy {low['classification_accuracy_pct']:g}% to {high['classification_accuracy_pct']:g}%.")
    entity_table = 'Entity precision, recall and F1 are pending until all 100 articles are manually annotated.'
    entity_discussion = 'The effect of schema constraints on entity correctness cannot yet be measured.'
    if progress['complete'] and all('total_requests' in runs[k] for k in ('prompt_only','schema_constrained')):
        entity_table = '| Mode / type | Precision | Recall | F1 |\n|---|---:|---:|---:|\n'
        for name in ('prompt_only','schema_constrained'):
            for kind, score in runs[name]['entity_f1'].items():
                label = ('Prompt' if name=='prompt_only' else 'Schema') + ' / ' + kind
                entity_table += f"| {label} | {score['precision_pct']:g}% | {score['recall_pct']:g}% | {score['f1_pct']:g}% |\n"
        a,b = (runs[k]['entity_f1']['micro']['f1_pct'] for k in ('prompt_only','schema_constrained'))
        entity_discussion = (f"Entity micro-F1 at T=0 is {a:g}% for prompt-only and {b:g}% for schema "
                             f"({b-a:+.2f} percentage points). Grammar constraints restrict structure and labels, "
                             "but cannot guarantee correct names, types or complete extraction. This single-seed observation does not prove general superiority.")
    reviewer = ', '.join(sorted({r['reviewer'] for r in load_gold().values() if r['status']=='completed'})) or 'No completed manual annotations yet'
    report_dir = ROOT / 'report' if directory == ROOT / 'results' else directory / 'report'
    figure = f"![Current results]({relpath(directory / 'metrics.png', report_dir)})" if finished else ''
    return f'''# Structured Turkish News: JSON Classification and Entity Extraction

**{status}.** Manual annotation: **{progress['annotated']}/{progress['selected']}**. Completed requests: **{requests}/400**.

## 1. Task and data

A local open-source Qwen model classifies Turkish news into seven categories and extracts person, organization and location names. The experiment compares prompt-only JSON instructions with Ollama JSON-schema constraints, then repeats both modes at temperatures 0 and 1. No cloud model API is used for these requests.

The fixed evaluation file contains 100 distinct TTC4900 articles: 15 dunya, 15 ekonomi, and 14 each in kultur, saglik, siyaset, spor and teknoloji. Texts, source IDs and original category labels are saved in data/news.jsonl. This balanced subset is not a random estimate of natural news prevalence. Identical texts and order are used in all four runs. Source: [savasy/ttc4900](https://huggingface.co/datasets/savasy/ttc4900).

## 2. Model and method

{setup}

Explicit options: {options}. Temperature is replaced by 1.0 for the temperature experiment; stream=false in all requests. Requests use the same prompt, schema and options except the controlled variable. Prompt-only omits format entirely; schema mode sends the JSON_SCHEMA object. Stop-list and runtime-default details are in docs/GENERATION_PARAMETERS.md. Reference: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

The prompt defines categories, entity types and a JSON object template. It asks for all named surface forms without a five-name cap. The schema requires category plus person/organization/location string arrays inside entities, and disallows additional fields. Token budget is finite, so truncation remains possible and is counted as a failure when unusable.

Raw parsing applies json.loads directly. On JSONDecodeError, cleaning removes Markdown fences or surrounding text and retries. It never adds facts, fields or missing braces. Schema checking then verifies required keys, types and allowed categories. API errors are recorded and remaining samples continue. Raw outputs are preserved; summary metrics are recomputed from them.

<!-- pagebreak -->

## 3. Evaluation results

All format and classification rates divide by every request, including API/parse/schema failures. Classification counts a correct category only when the full output is schema-valid. Entity scoring treats invalid outputs as empty predictions, so missing gold names count as false negatives. Pending entity F1 is not a zero score.

{table}

{discussion}

{' '.join(temperature_discussion)} These single-seed findings do not establish a universal temperature effect. The live video demonstrates both temperatures on the same new texts.

{figure}

<!-- pagebreak -->

## 4. Manual annotation and entity matching

The annotation screen starts with empty fields and displays only the article and the annotator's own saved entries. The human selects or types source-text names, assigns their types and explicitly saves each article. No model suggests, completes or verifies these labels. Completed records include annotator, timestamp and source-text hash. Recorded annotator(s): **{reviewer}**.

Annotate all distinct named surface forms. Exclude titles, grammatical suffixes, products, events, nationalities and fictional characters. Use the longest explicit name at a mention; include a short form separately only when it occurs separately. A club or national team is an organization; a country used geographically is a location. Repeated identical forms count once. There is no entity-count cap and no alias-group syntax. Full policy: docs/ANNOTATION_GUIDELINES.md.

Matching is exact after NFC normalization, Turkish İ→i and I→ı replacement before lowercasing, underscores-to-spaces and whitespace collapsing. Entity type is preserved. Compare sets of (type, normalized surface form) within each article. A wrong type contributes FP and FN; no partial or fuzzy match is used. P=TP/(TP+FP), R=TP/(TP+FN), F1=2PR/(P+R), with zero denominators giving zero. Micro-F1 sums counts across all articles and types.

{entity_table}

{entity_discussion}

Every annotation save rebuilds metrics, plot and this report from current gold. New or changed gold changes the evaluation input; no F1 value is hard-coded. Annotation fingerprint: {results['gold_sha256']}.

## 5. Limitations and reproduction

One annotator, one seed and a small balanced subset limit generalization. No blinded annotation or inter-annotator agreement is claimed. Exact surface matching penalizes spelling differences; finite output/context budgets can omit names. JSON validity is not semantic correctness. Runtime/hardware changes can affect reproducibility even with a fixed seed; pretraining overlap is unknown.

Run python src/build_report.py to regenerate all derived outputs without model calls. Run python src/evaluate.py --run-all --directory results/new_run for new inference. Code/report, the English video (maximum 30 minutes) and Unlisted link must be submitted according to the course instructions. Manual labels, live tests and the student's own defense cannot be replaced by generated artifacts.
'''.strip() + "\n"


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
            image_path=(Path(destination).parent/match[2]).resolve()
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


def rebuild(directory=None):
    directory = Path(directory or ROOT / "results").resolve()
    report_dir = ROOT / "report" if directory == ROOT / "results" else directory / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    # Remove derived artifacts first: a failed refresh must not leave stale scores.
    for path in (directory/'metrics.json', directory/'metrics.png',
                 report_dir/'technical_report.md', report_dir/'technical_report.pdf'):
        path.unlink(missing_ok=True)
    results = compare_runs(directory)
    markdown = report_markdown(results, directory)
    (report_dir/'technical_report.md').write_text(markdown, encoding='utf-8')
    render_pdf(markdown, report_dir/'technical_report.pdf')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args()
    results = rebuild(args.directory)
    print('Manual annotation:', results['entity_gold'])


if __name__ == '__main__':
    main()
