"""Kanonik veri/yanıt/metrik/matris ve kaynak karmalarını ağsız doğrular."""
import ast
import csv
import hashlib
import json
from pathlib import Path
from step4_analyze_results import ROOT, OUT, METHODS, collect_summary, load_jsonl

FIGURES = ('json_success_comparison', 'classification_accuracy', 'inference_performance',
           'confusion_matrix', 'category_accuracy', 'schema_failure_analysis')

# The migration manifest records names at migration time; preserve that history.
HISTORICAL_MODULE_NAMES = {
    'step3a_evaluate_prompt': 'evaluate_v2',
    'step3b_evaluate_json': 'evaluate_schema',
    'step3c_evaluate_optimized': 'evaluate_v3',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    summary, matrices = collect_summary()
    assert summary['status'] == 'complete'
    assert summary == json.loads((OUT / 'metrics_summary.json').read_text()), 'Saved metrics differ from raw responses.'
    manifest = json.loads((ROOT / 'docs/migration_manifest.json').read_text())
    identity = json.loads((OUT / 'run_identity.json').read_text())
    assert digest(ROOT/'data/test_samples.jsonl') == manifest['promoted_data_sha256'] == identity['dataset_sha256']
    syntax = []
    for directory in ('src','tests'):
        for path in sorted((ROOT/directory).glob('*.py')):
            compile(path.read_text(), str(path), 'exec')
            syntax.append(str(path.relative_to(ROOT)))
    matrices_verified = []
    experiments = {}
    for key,(name,filename) in METHODS.items():
        rows = load_jsonl(OUT/filename)
        assert len(rows) == len({r['id'] for r in rows}) == 200
        assert [r['id'] for r in rows] == summary['evaluation_ids']
        assert all(r['response_received'] and r['api_error'] is None for r in rows)
        assert digest(OUT/filename) == manifest['promoted_results_sha256'][filename]
        assert digest(ROOT/'src'/f'{name}.py') == identity['script_sha256'][name]
        evidence = manifest['inference_preservation'][HISTORICAL_MODULE_NAMES[name]]
        assert identity['script_sha256'][name] == evidence['canonical_source_sha256']
        assert evidence['ast_equal_after_path_and_module_docstring_normalization']
        matrix = matrices[key]
        categories = sorted(matrix)
        columns = categories + ['INVALID']
        path = OUT/('v3_confusion_matrix.csv' if key=='C' else f'confusion_matrix_{key}.csv')
        with path.open(newline='') as stream:
            reader = csv.reader(stream)
            assert next(reader) == ['Actual / Predicted']+columns
            assert list(reader) == [[c]+[str(matrix[c][p]) for p in columns] for c in categories]
        matrices_verified.append(str(path.relative_to(ROOT)))
        experiments[key] = {'records':len(rows),'same_ordered_ids':True,'raw_flags_recomputed':True,
                            'source_result_bytes_preserved':True, 'no_api_errors':True}
    assert summary['dataset']['duplicate_evaluation_text_ids'] == [[2138,2296]]
    dev = load_jsonl(OUT/'baseline_results.jsonl')
    assert len(dev) == 5 and {r['id'] for r in dev} == set(summary['dataset']['development_ids'])
    figures = []
    for name in FIGURES:
        for suffix in ('png','svg'):
            path = OUT/'figures'/f'{name}.{suffix}'
            assert path.stat().st_size > 1000
            if suffix == 'png':
                assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
            else:
                assert '<svg' in path.read_text()
            figures.append(str(path.relative_to(ROOT)))
    assert (ROOT/'report.pdf').read_bytes().startswith(b'%PDF-')
    active = [p for p in ROOT.rglob('*') if p.is_file() and not any(part in {'venv','.git','.codex','.agents','.aws','__pycache__'} for part in p.relative_to(ROOT).parts)]
    assert not [str(p.relative_to(ROOT)) for p in active if '_200' in p.name or '_205' in p.name or '-200-' in p.name]
    # Historical filenames may occur only in the migration change inventory as archive provenance.
    import re
    for p in active:
        if p.suffix not in {'.py','.md'} or p.name in {'MIGRATION_CHANGES.md','step7_verify_project.py'}:
            continue
        assert not re.search(r'\b[\w/.-]+_(?:200|205)(?:\.[\w]+|/|\b)',p.read_text()), str(p)
    report = {'status':'passed','dataset':summary['dataset'],'experiments':experiments,
              'syntax_checked':syntax,'metrics_equal_raw_recomputation':True,
              'matrices_verified':matrices_verified,'figures_verified':figures,
              'inference_source_hashes_verified':True,'active_version_suffixes_absent':True,
              'development_baseline_separate':True,'pdf_header_valid':True,
              'backup_directory':manifest['backup_directory']}
    (ROOT/'docs/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'passed','dataset':205,'development':5,'evaluation':200,'unique_evaluation_texts':199,'experiments':experiments},ensure_ascii=False))


if __name__ == '__main__':
    main()
