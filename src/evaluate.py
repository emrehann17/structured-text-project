"""Analyze the 200 saved responses offline, or explicitly run fresh local inference."""

import argparse
import json
from pathlib import Path

from llm_pipeline import evaluate_response, evaluate_sample

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/test_samples.jsonl"
RESULT_PATH = ROOT / "results/optimized_schema_results.jsonl"
METRICS = {
    "raw_json_success": "raw_json_valid",
    "clean_json_success": "clean_json_valid",
    "schema_success": "schema_valid",
    "classification_accuracy": "category_correct",
}


def load_jsonl(path):
    """Read JSONL without hiding corrupt or incomplete saved records."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def analyze_results(samples, rows):
    """Recompute every flag from raw text; all requests remain in the denominator."""
    expected = {sample["id"]: sample for sample in samples}
    ids = [row["id"] for row in rows]
    if not samples or len(expected) != len(samples):
        raise ValueError("Expected nonempty samples with distinct IDs")
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError("Results must contain exactly one record for every evaluation ID")
    counts = dict.fromkeys(METRICS, 0)
    received = api_errors = 0
    for row in rows:
        sample = expected[row["id"]]
        if row["true_category"] != sample["true_category"]:
            raise ValueError(f"Reference category mismatch for ID {row['id']}")
        api_errors += row["api_error"] is not None
        received += bool(row["response_received"])
        if row["response_received"] and row["api_error"] is None:
            if not isinstance(row["raw_output"], str):
                raise ValueError(f"Non-text response for ID {row['id']}")
            flags = evaluate_response(row["raw_output"], sample["true_category"])
            for metric, flag in METRICS.items():
                counts[metric] += flags[flag]
    total = len(rows)
    summary = {"total_requests": total, "responses_received": received,
               "api_errors": api_errors}
    for metric, count in counts.items():
        summary[metric + "_count"] = count
        summary[metric + "_pct"] = round(count / total * 100, 2)
    elapsed = sum(row["elapsed_seconds"] for row in rows)
    summary["total_measured_seconds"] = round(elapsed, 2)
    summary["average_measured_seconds"] = round(elapsed / total, 2)
    return summary


def save_figure(summary, path):
    """Plot the four rates on the same all-request denominator."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["First-attempt\nJSON parsing", "JSON parsing\nafter cleaning",
              "Schema\nvalidity", "Classification\naccuracy"]
    values = [summary[key + "_pct"] for key in METRICS]
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    bars = ax.bar(labels, values, color=["#267c91"] * 3 + ["#c17b30"], width=0.6)
    ax.bar_label(bars, labels=[f"{value:g}%" for value in values], padding=4)
    ax.set(ylim=(0, 112), ylabel="Percent of all requests",
           title=f"Local Qwen2.5:3b — {summary['total_requests']} evaluation records")
    ax.set_yticks(range(0, 101, 20))
    ax.spines[["top", "right"]].set_visible(False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    """Default to offline analysis. Fresh runs require a new results filename."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--analyze", action="store_true", help="reanalyze saved responses (default)")
    mode.add_argument("--run", action="store_true", help="make 200 local Ollama requests")
    parser.add_argument("--results", type=Path, help="saved input, or NEW output with --run")
    args = parser.parse_args()
    if args.run and args.results is None:
        parser.error("--run requires --results with a new filename")
    path = args.results.resolve() if args.results else RESULT_PATH
    if path.suffix != ".jsonl":
        parser.error("--results must be a .jsonl file")
    try:
        all_samples = load_jsonl(DATA_PATH)
        if len(all_samples) != 205:
            raise ValueError("The frozen dataset must contain 205 records")
        samples = all_samples[5:205]
        if args.run:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation refuses to overwrite any existing evidence.
            with path.open("x", encoding="utf-8") as output:
                for index, sample in enumerate(samples, 1):
                    row = evaluate_sample(sample)
                    output.write(json.dumps(row, ensure_ascii=False) + "\n")
                    output.flush()
                    print(f"[{index}/200] ID={row['id']} JSON={row['raw_json_valid']}", flush=True)
        summary = analyze_results(samples, load_jsonl(path))
        summary["source_results"] = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        summary["analysis"] = "Recomputed from saved raw responses; timing comes from saved measurements"
        # Custom runs never replace the published summary or figure.
        summary_path = ROOT / "results/summary.json" if path == RESULT_PATH else path.with_suffix(".summary.json")
        figure_path = ROOT / "results/figures/json_success.png" if path == RESULT_PATH else path.with_suffix(".png")
        if summary_path.exists() and summary_path.samefile(path):
            raise ValueError("Summary path must differ from the response file")
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        save_figure(summary, figure_path)
        print(json.dumps(summary, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Evaluation failed: {error}\n")


if __name__ == "__main__":
    main()
