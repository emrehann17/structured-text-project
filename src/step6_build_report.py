"""Doğrulanmış 200 değerlendirme kaydından akademik report.pdf üretir."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from step4_analyze_results import ROOT, OUT, collect_summary
from step5_generate_figures import main as generate_assets


def register_fonts():
    fonts = Path('/usr/share/fonts/truetype/dejavu')
    for name in ('DejaVuSans', 'DejaVuSans-Bold'):
        pdfmetrics.registerFont(TTFont(name, str(fonts / (name + '.ttf'))))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('DejaVuSans', 8)
    canvas.setFillColor(colors.HexColor('#526075'))
    canvas.drawString(20*mm, 12*mm, 'TTC4900 | 5 development + 200 evaluation records | qwen2.5:3b')
    canvas.drawRightString(190*mm, 12*mm, str(doc.page))
    canvas.restoreState()


def main():
    summary, _ = collect_summary()
    assert summary['status'] == 'complete', 'A complete run is required for the academic report.'
    # Every build refreshes the figures and stored metrics from the original responses.
    generate_assets()
    assert json.loads((OUT / 'metrics_summary.json').read_text()) == summary
    identity = json.loads((OUT / 'run_identity.json').read_text())
    register_fonts()
    body = ParagraphStyle('Body', fontName='DejaVuSans', fontSize=9, leading=13, spaceAfter=7)
    heading = ParagraphStyle('Heading', parent=body, fontName='DejaVuSans-Bold', fontSize=15, leading=20, spaceAfter=12)
    small = ParagraphStyle('Small', parent=body, fontSize=8, leading=11)
    story = []
    def para(text, title=False):
        story.append(Paragraph(escape(text), heading if title else body))
    def table(rows, widths):
        cells = [[Paragraph(escape(str(cell)), small) for cell in row] for row in rows]
        result = Table(cells, colWidths=[w*mm for w in widths], repeatRows=1, hAlign='LEFT')
        result.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5edf5')),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#abb8c5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        story.extend([result, Spacer(1, 10)])
    def figure(name, caption, height=74):
        story.append(Image(str(OUT/'figures'/f'{name}.png'), width=165*mm, height=height*mm))
        story.append(Paragraph(escape(caption), small))
        story.append(Spacer(1, 10))
    metrics = {key: exp['final_metrics'] for key, exp in summary['experiments'].items()}
    a,b,c = [metrics[key] for key in 'ABC']
    para('Structured Text Classification and Information Extraction Using a Local LLM', True)
    para('Empirical evaluation of Turkish news: 200 evaluation records', True)
    para('Abstract', True)
    para(f'This study compares prompt-only generation (A), JSON Schema constrained generation (B), and a shorter prompt with the same schema and repetition control (C), using qwen2.5:3b. Each experiment contains 200 saved responses for the same ordered article IDs. Raw JSON validity is {a["raw_json_success_pct"]:.2f}%, {b["raw_json_success_pct"]:.2f}% and {c["raw_json_success_pct"]:.2f}%; end-to-end classification accuracy is {a["end_to_end_accuracy_pct"]:.2f}%, {b["end_to_end_accuracy_pct"]:.2f}% and {c["end_to_end_accuracy_pct"]:.2f}%, respectively. The corpus has five separate development records and 200 evaluation records. Two evaluation IDs share a text, so the evaluation represents 199 unique texts. All metrics are recomputed from saved model responses; no inference is performed during report generation.')
    para('1. Research question and task', True)
    para('Can a local language model reliably emit machine-readable Turkish news classifications and entity lists? The output must contain one of seven category labels and person, organization and location arrays. JSON syntax, application schema validity and correct classification are distinct outcomes. No model training or fine-tuning is performed. Entity extraction is checked structurally; semantic NER accuracy is not measured because reference entity annotations are unavailable.')
    para('2. Dataset and split', True)
    para('The source is TTC4900 (savasy/ttc4900, train split). The canonical data/test_samples.jsonl contains 205 records in the original saved order. Development is samples[:5]; evaluation is exactly samples[5:205]. Article IDs are source row indices. Filtering retains texts with 150–3000 characters after trimming. Seed 42 and the recorded selection procedure reproduce membership; data/test_samples_manifest.json records the exact IDs and dataset hash.')
    para('The original ordered selection was extended without reshuffling. IDs 2138 and 2296 have identical text and remain included because inference was already complete. There are 205 unique record IDs and 204 unique texts overall, and 200 unique IDs but 199 unique texts in evaluation. These are record-level metrics; no post-hoc deduplication or membership change was applied.')
    para('Evaluation class support: ' + ', '.join(f'{category}: {count}' for category, count in summary['dataset']['evaluation_category_counts'].items()) + '.')

    story.append(PageBreak())
    para('3. Methods and reproducibility', True)
    table([['Configuration','A','B','C'],['Prompt','Detailed','Same as A','Shorter'],['Generation schema','Absent','JSON_SCHEMA','Same JSON_SCHEMA'],['Repetition options','Not explicit','Not explicit','Penalty 1.2; last 128'],['temperature / seed','0 / 42','0 / 42','0 / 42'],['num_ctx / num_predict','4096 / 384','4096 / 384','4096 / 384']], [51,38,38,38])
    para('Each request uses stream=False and timeout=(5, 60). top_k and top_p are not explicitly set. The schema requires category and entities, allows only the seven category labels and exactly the three entity arrays, and disallows additional properties. The five-entity limit is a prompt instruction, not a schema maxItems constraint. Existing prompt strings, schema, options, cleaning, validation and exception handling were preserved during path migration.')
    para(f'The recorded runtime is Ollama {identity["ollama_version"]}, model {identity["model"]}. Model digest: {identity["model_digest"]}. Model parameter metadata was null in the run identity, so unspecified sampling defaults are not reconstructed. GPU utilization and hardware were not measured during this migration. results/run_identity.json records the canonical source hashes; docs/migration_manifest.json preserves their relationship to the executed source hashes.')
    para('Execution appends one JSONL result per attempted article. Saved IDs, including error records, are skipped on resumption. The canonical runner validates stored responses and returns without contacting Ollama when all experiments are complete. For incomplete runs it checks the dataset, code hashes and runtime/model identity before continuing. It does not fabricate records, retry completed IDs or repair malformed checkpoint lines silently.')
    para('4. Metrics and validation', True)
    para('All primary rates use all 200 evaluation records as denominator, including API, JSON and schema failures. Raw JSON success uses json.loads on the untouched response. Clean JSON success uses the original parser after removing formatting or finding an existing JSON object; it does not repair truncated output. Schema validity checks field names, types and label membership. Classification is correct only when the schema is valid and category equals the reference label.')
    para('Conditional accuracy divides correct classifications by schema-valid outputs: A uses 162, B uses 158, C uses 200. It is not comparable to end-to-end accuracy without stating the denominator. Runtime sums the recorded client elapsed_seconds, including request waiting and parsing. Mean runtime divides this sum by 200. Confusion matrices retain failed outputs in an INVALID column; each matrix sums to 200.')
    para('All 600 result records were reparsed and their stored validity and correctness flags checked. Each experiment has exactly the same 200 IDs in dataset order, no development IDs and no API errors. The promoted JSONL files and dataset match the completed source files byte for byte. The previous project, including its earlier results and report, is retained in an external checksum-verified backup.')

    story.append(PageBreak())
    para('5. Results: output structure and classification', True)
    rows = [['Metric (count / denominator)','A','B','C']]
    for label,count,pct in [('Raw JSON','raw_json_success_count','raw_json_success_pct'),('Clean JSON','clean_json_success_count','clean_json_success_pct'),('Schema valid','schema_success_count','schema_success_pct'),('Correct category','category_correct_count','end_to_end_accuracy_pct')]:
        rows.append([label]+[f'{metrics[k][count]}/200 ({metrics[k][pct]:.2f}%)' for k in 'ABC'])
    rows.append(['Conditional accuracy']+[f'{metrics[k]["category_correct_count"]}/{metrics[k]["conditional_accuracy_denominator"]} ({metrics[k]["conditional_accuracy_pct"]:.2f}%)' for k in 'ABC'])
    table(rows,[54,37,37,37])
    figure('json_success_comparison','Figure 1. Raw parsing, cleaning and schema success; all denominators are 200.')
    figure('classification_accuracy','Figure 2. End-to-end and conditional accuracy use different denominators.')
    para(f'A has {200-a["clean_json_success_count"]} responses that remain unparseable and {a["clean_json_success_count"]-a["schema_success_count"]} parsed outputs that fail schema validation. C achieves structurally valid output for every evaluated record but misclassifies {200-c["category_correct_count"]} records. Structural reliability does not imply semantic correctness.')

    story.append(PageBreak())
    para('6. Runtime and failure analysis', True)
    table([['Recorded time','A','B','C'],['Total seconds']+[metrics[k]['total_inference_seconds'] for k in 'ABC'],['Mean seconds / record']+[metrics[k]['mean_inference_seconds'] for k in 'ABC']], [54,37,37,37])
    figure('inference_performance','Figure 3. Recorded total and mean client-side runtime.')
    figure('schema_failure_analysis','Figure 4. Experiment B outcomes, including recorded length stops.')
    fail = summary['experiments']['B']['failure_breakdown']
    para(f'B has {fail["schema_invalid_with_length_stop"]} schema-invalid responses with done_reason=length and {fail["schema_invalid_other_or_unrecorded_stop"]} schema-invalid responses with other or absent stopping metadata. This is evidence about the recorded configuration, not a controlled comparison of token limits. C is {a["total_inference_seconds"]/c["total_inference_seconds"]:.2f} times as fast as A in this run ({100*(1-c["total_inference_seconds"]/a["total_inference_seconds"]):.2f}% less total time). Hardware, scheduling and model-serving conditions can affect timing; repeated-run variability was not measured.')

    story.append(PageBreak())
    para('7. Per-category results', True)
    figure('confusion_matrix','Figure 5. C confusion matrix. Rows are reference labels, columns predictions; INVALID preserves failures.',115)
    table([['Category','Correct / support','Accuracy']]+[[k,f'{v["correct"]}/{v["total"]}',f'{v["accuracy_pct"]:.2f}%'] for k,v in c['per_category'].items()],[70,50,45])
    para('The matrix is saved as results/v3_confusion_matrix.csv. Separate matrices for A and B use the same reference classes and INVALID column. The dunya class has no correct C predictions in this run; aggregate accuracy should therefore not be interpreted as uniform performance across categories.')

    story.append(PageBreak())
    para('8. Interpretation and limitations', True)
    figure('category_accuracy','Figure 6. C per-category accuracy and overall accuracy reference.')
    entity = summary['entity_structure_C']
    para(f'The C structural entity audit covers {entity["schema_valid_responses_checked"]} responses and {entity["entity_lists_checked"]} entity arrays. {entity["lists_with_duplicates"]} arrays contain repeated entries after case-folding and trimming, and {entity["lists_exceeding_five"]} exceed five entries. These checks are not semantic precision, recall, F1 or a hallucination rate. For example, a real organization placed in person can satisfy the schema while having the wrong entity type.')
    para('C changes the prompt and repetition settings together. Their individual causal effects cannot be separated by these three experiments. No controlled top-k/top-p sweep, prompt-only ablation of the C prompt, confidence interval or repeated-run uncertainty estimate is claimed. Seed 42 and temperature 0 support reproducibility under matching conditions but do not guarantee identical output across runtime versions or hardware.')
    para('The evaluation contains a duplicated text under two IDs. Record-level results are reported exactly as inferred; the duplicate limits text-level independence. The balanced evaluation selection is not a claim about natural news frequencies. Five development examples are excluded from every main metric, and development baseline records are not pooled with evaluation results.')
    para('9. Conclusion', True)
    para(f'On these 200 evaluation records, C yields {c["raw_json_success_pct"]:.2f}% raw JSON and schema validity, {c["end_to_end_accuracy_pct"]:.2f}% end-to-end classification accuracy and {c["total_inference_seconds"]:.2f} seconds total client runtime. This supports the practical value of the combined configuration for reliable output structure while exposing remaining classification and entity-quality limitations.')
    para('10. Artifacts and references', True)
    para('Primary evidence: data/test_samples.jsonl; results/improved_prompt_results.jsonl; results/schema_results.jsonl; results/optimized_schema_results.jsonl; results/metrics_summary.json. Reproduction: python src/step6_build_report.py. Validation: python src/step7_verify_project.py and python -m unittest discover -s tests -v. The README and Turkish study, technical Q&A and presentation guides describe the same completed run.')
    para('Dataset provenance: savasy/ttc4900 (Hugging Face), recorded in data/test_samples_manifest.json. Software: Python json/requests, Ollama qwen2.5:3b, Matplotlib and ReportLab; dependencies in requirements.txt. Dataset and model identifiers describe the saved experiment, not a newly downloaded revision.')
    output = ROOT / 'report.pdf'
    SimpleDocTemplate(str(output), pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=18*mm, bottomMargin=23*mm,
        title='Turkish News: 200 Evaluation Records', author='Structured Text Project').build(story,onFirstPage=footer,onLaterPages=footer)
    print(output)


if __name__ == '__main__':
    main()
