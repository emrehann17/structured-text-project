"""Video demonstrations: real model calls, or an offline evaluation-line ablation."""
import argparse
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import evaluate
import llm_pipeline as pipeline
from evaluate import ROOT, load_jsonl, normalize_entity


def defense_demo():
    """Remove one evaluation statement in a temporary copy and compare matching."""
    source = Path(evaluate.__file__)
    original = source.read_text(encoding="utf-8")
    statement = '    name = name.replace("İ", "i").replace("I", "ı").lower().replace("_", " ")'
    if original.count(statement) != 1:
        raise ValueError("Inspect normalize_entity before running the demonstration")
    with TemporaryDirectory(prefix="manual-a1-") as directory:
        changed = original.replace(statement + "\n", "", 1)
        path = Path(directory) / "without_normalization.py"
        path.write_text(changed, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("without_normalization", path)
        edited = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(edited)
        print("A1: offline evaluation experiment; no new model calls.")
        print("Removed line:", statement.strip())
        print("Temporary source:", path)
        # Explicit teaching example, not a benchmark measurement.
        for name, module in (("before", evaluate), ("after", edited)):
            print(name, "teaching example:", module.normalize_entity("İSTANBUL"),
                  module.match_entities(["İSTANBUL"], ["istanbul"]))
        gold, samples = evaluate.load_gold(), evaluate.load_samples()
        if evaluate.gold_status([s['id'] for s in samples], gold)['complete']:
            for run in ("prompt_only", "schema_constrained"):
                path = ROOT / 'results' / evaluate.RUNS[run][0]
                if not path.exists():
                    print(run, "pending model experiment")
                    continue
                rows = load_jsonl(path)
                for name, module in (("before", evaluate), ("after", edited)):
                    summary = module.analyze_results(samples, rows, gold)
                    print(run, name, "entity micro-F1:", summary['entity_f1']['micro']['f1_pct'])
        else:
            print("Dataset F1 ablation awaits 100 completed manual annotations.")
        if source.read_text(encoding='utf-8') != original:
            raise RuntimeError("Evaluator source changed during demonstration")
    print("Original evaluator unchanged. Do not replace the benchmark with ablated scores.")


def live_demo(output):
    samples = load_jsonl(ROOT / 'data/demo_samples.jsonl')
    source_texts = {normalize_entity(s['text']) for s in evaluate.load_samples()}
    new_texts = {normalize_entity(s['text']) for s in samples}
    if len(samples) < 5 or len(new_texts) != len(samples) or new_texts & source_texts:
        raise ValueError("Five distinct new demo texts are required")
    if output.exists():
        raise ValueError("Choose a new output filename")
    environment = evaluate.capture_environment()
    print('Actual environment:', json.dumps(environment, ensure_ascii=False, indent=2))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        for temperature in (0, 1.0):
            for mode in ('prompt', 'schema'):
                for sample in samples:
                    print(f"\nLIVE {sample['id']}, {mode}, T={temperature}", flush=True)
                    print(sample['text'])
                    print('Expected category:', sample['true_category'], 'Challenging:', sample['challenging'])
                    row = pipeline.evaluate_sample(sample, mode, temperature)
                    row['model_digest'] = environment['model_digest']
                    print(json.dumps(row, ensure_ascii=False, indent=2), flush=True)
                    stream.write(json.dumps(row, ensure_ascii=False) + '\n')
                    stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--defense', action='store_true', help='A1: remove a normalization line and re-evaluate')
    parser.add_argument('--output', type=Path, help='New output file for 20 live model requests')
    args = parser.parse_args()
    if args.defense:
        defense_demo()
    elif args.output:
        live_demo(args.output)
    else:
        parser.error('Choose --defense or --output NEW.jsonl')


if __name__ == '__main__':
    main()
