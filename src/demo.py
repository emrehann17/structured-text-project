"""Continuous live Ollama demo; --check only checks novelty, never generates responses."""
import argparse
from difflib import SequenceMatcher
import json
import importlib.util
from tempfile import TemporaryDirectory
from pathlib import Path

from evaluate import ROOT, load_jsonl, normalize_entity, capture_environment, environment_fingerprint
from llm_pipeline import evaluate_sample, fingerprint
import llm_pipeline

DEMO_PATH = ROOT / "data/demo_samples.jsonl"


def check_novelty(samples, source):
    """Reject normalized duplicates, long containment, or >=0.80 word-sequence similarity."""
    if len(samples) < 5 or len({s["id"] for s in samples}) != len(samples):
        raise ValueError("At least five distinct demo IDs required")
    references = [(s["id"], normalize_entity(s["text"]).split()) for s in source]
    evidence = []
    for sample in samples:
        words = normalize_entity(sample["text"]).split()
        if not words:
            raise ValueError("Empty demo text")
        best, closest = 0, None
        for ref_id, other in references:
            ratio = SequenceMatcher(None, words, other, autojunk=False).ratio()
            short, long = sorted((" ".join(words), " ".join(other)), key=len)
            if words == other or (len(short) >= 80 and short in long) or ratio >= .80:
                raise ValueError(f"Demo {sample['id']} duplicates or resembles {ref_id}")
            if ratio > best:
                best, closest = ratio, ref_id
        evidence.append({"id": sample["id"], "nearest_source_id": closest,
                         "max_word_similarity": round(best, 4), "text_sha256": fingerprint(sample["text"])})
        references.append((sample["id"], words))
    return evidence


def defense_demo(output_path, sample):
    """A1: remove one executable statement in a temporary copy; make two real requests."""
    original = Path(llm_pipeline.__file__).read_text(encoding="utf-8")
    statement = '        request_body["format"] = JSON_SCHEMA'
    if original.count(statement) != 1:
        raise ValueError("Expected one format assignment; inspect code before this demo")
    changed = original.replace(statement, '        pass  # format assignment removed for A1')
    environment = capture_environment(path=None)
    with TemporaryDirectory(prefix="nlp-defense-") as directory:
        path = Path(directory) / "without_format.py"
        path.write_text(changed, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("without_format", path)
        edited = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(edited)
        print("Temporary copy:", path)
        print("Removed executable statement:", statement.strip())
        print("A pass statement keeps the now-empty if block syntactically valid.")
        with output_path.open("x", encoding="utf-8") as output:
            for label, module in (("before", llm_pipeline), ("after", edited)):
                request = module.build_request(sample["text"], "schema", 0)
                print(label, "ACTUAL REQUEST KEYS:", list(request), flush=True)
                row = module.evaluate_sample(sample, "schema", 0)
                row.update(defense_variant=label, model_digest=environment["model_digest"],
                           quantization=environment["details"]["quantization_level"])
                print("RAW:", row["raw_output"], flush=True)
                print("EVALUATION:", json.dumps(row, ensure_ascii=False, indent=2), flush=True)
                output.write(json.dumps(row, ensure_ascii=False) + "\n")
        assert Path(llm_pipeline.__file__).read_text(encoding="utf-8") == original
    print("Temporary copy removed. Repository source unchanged. Output changes are not guaranteed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--defense", action="store_true", help="A1: real before/after requests using a temporary source copy")
    parser.add_argument("--mode", choices=["prompt", "schema", "both"], default="both")
    parser.add_argument("--temperatures", type=float, nargs="+", default=[0, 1.0])
    parser.add_argument("--output", type=Path, help="NEW JSONL file; required for live requests")
    args = parser.parse_args()
    samples = load_jsonl(DEMO_PATH)
    evidence = check_novelty(samples, load_jsonl(ROOT / "data/test_samples.jsonl"))
    print("Novelty check:", json.dumps(evidence, ensure_ascii=False, indent=2))
    if args.check:
        return
    if args.output is None or args.output.exists():
        parser.error("Live demo requires --output with a new filename")
    if args.defense:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        defense_demo(args.output, samples[-1])
        return
    environment = capture_environment(path=None)
    print("ACTUAL ENVIRONMENT:", json.dumps(environment, ensure_ascii=False, indent=2))
    modes = ["prompt", "schema"] if args.mode == "both" else [args.mode]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        for temperature in args.temperatures:
            for mode in modes:
                for sample in samples:
                    print(f"\n{'=' * 72}\nLIVE ID={sample['id']} mode={mode} temperature={temperature}", flush=True)
                    print(sample["text"], flush=True)
                    print("Expected category (draft until student reviews):", sample["true_category"], flush=True)
                    print("Rationale:", sample["category_rationale"], flush=True)
                    row = evaluate_sample(sample, mode, temperature)
                    row.update(model_digest=environment["model_digest"],
                               quantization=environment["details"]["quantization_level"],
                               environment_sha256=environment_fingerprint(environment),
                               expected_category_status=sample["category_review_status"])
                    print("RAW MODEL RESPONSE:\n" + (row["raw_output"] if row["raw_output"] is not None else "[NO RESPONSE]"))
                    print("CHECKS:", json.dumps({k: v for k, v in row.items() if k != "raw_output"}, ensure_ascii=False, indent=2), flush=True)
                    output.write(json.dumps(row, ensure_ascii=False) + "\n")
                    output.flush()
    print(f"Saved genuine requests to {args.output}. No mock or replay mode exists.")


if __name__ == "__main__":
    main()
