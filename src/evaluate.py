"""Run the local study or recompute every metric from current manual labels.

python src/evaluate.py                 # offline analysis and plot
python src/evaluate.py --run-all       # four runs, 100 texts per run
"""
import argparse
import json
import platform
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
import llm_pipeline as pipeline
from llm_pipeline import evaluate_response, evaluate_sample

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/news.jsonl"
GOLD_PATH = ROOT / "data/entity_gold.jsonl"
RUNS = {
    "prompt_only": ("prompt_only.jsonl", "prompt", 0),
    "schema_constrained": ("schema_constrained.jsonl", "schema", 0),
    "prompt_only_temp1": ("prompt_only_temp1.jsonl", "prompt", 1.0),
    "schema_constrained_temp1": ("schema_constrained_temp1.jsonl", "schema", 1.0),
}
METRICS = {"raw_json_success": "raw_json_valid", "clean_json_success": "clean_json_valid",
           "schema_success": "schema_valid", "classification_accuracy": "category_correct"}
PENDING_REVIEW = "PENDING MANUAL ANNOTATION"

def load_jsonl(path):
    """Bozuk veya eksik kayıtları gizlemeden JSONL dosyasını okur."""
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def normalize_entity(name):
    """NFC, Turkish casing, underscores as spaces, collapsed whitespace; punctuation retained."""
    name = unicodedata.normalize("NFC", name)
    name = name.replace("İ", "i").replace("I", "ı").lower().replace("_", " ")
    return " ".join(name.split())


def prf(tp, fp, fn):
    """Kesinlik, duyarlılık, F1 (yüzde). Pay/payda sıfırsa 0."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision_pct": round(precision * 100, 2),
            "recall_pct": round(recall * 100, 2), "f1_pct": round(f1 * 100, 2)}


def load_samples():
    samples = load_jsonl(DATA_PATH)
    if len(samples) != 100 or len({s["id"] for s in samples}) != 100:
        raise ValueError("Exactly 100 distinct sample IDs are required")
    if len({s["text"] for s in samples}) != 100:
        raise ValueError("Evaluation texts must be distinct")
    return samples


def match_entities(predicted, gold):
    """Exact sets of normalized surface forms within one entity type."""
    predicted = {normalize_entity(name) for name in predicted}
    expected = {normalize_entity(name) for name in gold}
    return len(predicted & expected), len(predicted - expected), len(expected - predicted)


def validate_gold_record(record):
    if record.get("annotation_method") != "manual_from_text":
        raise ValueError("Gold must be manually annotated from the source text")
    if record.get("status") not in ("draft", "completed"):
        raise ValueError("Unknown annotation status")
    for kind in sorted(pipeline.ENTITY_TYPES):
        names = record.get(kind)
        if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() or "|" in n for n in names):
            raise ValueError("Each entity must be a nonempty source-text name; no alias expressions")
        if len({normalize_entity(n) for n in names}) != len(names):
            raise ValueError("Duplicate normalized entity")
    if record["status"] == "completed" and not all(record.get(k) for k in ("reviewer", "reviewed_at", "text_sha256")):
        raise ValueError("Completed annotation needs annotator, time and source hash")


def load_gold(path=None):
    records = load_jsonl(path or GOLD_PATH)
    gold = {r["id"]: r for r in records}
    if len(gold) != len(records):
        raise ValueError("Duplicate annotation IDs")
    for record in records:
        validate_gold_record(record)
    return gold


def gold_status(ids, gold):
    count = sum(gold.get(i, {}).get("status") == "completed" for i in ids)
    return {"selected": len(ids), "annotated": count, "complete": bool(ids) and count == len(ids)}


def entity_scores(predictions, gold):
    totals = {kind: [0, 0, 0] for kind in sorted(pipeline.ENTITY_TYPES)}
    for sample_id, entities in predictions.items():
        record = gold[sample_id]
        validate_gold_record(record)
        if record["status"] != "completed":
            raise ValueError("Finish manual annotation before reporting entity F1")
        for kind in totals:
            counts = match_entities((entities or {}).get(kind, []), record[kind])
            totals[kind] = [a + b for a, b in zip(totals[kind], counts)]
    result = {kind: prf(*counts) for kind, counts in totals.items()}
    result["micro"] = prf(*[sum(c[i] for c in totals.values()) for i in range(3)])
    return result


def analyze_results(samples, rows, gold=None):
    """Her bayrağı ham metinden yeniden hesaplar; tüm istekler paydada kalır."""
    expected = {sample["id"]: sample for sample in samples}
    ids = [row["id"] for row in rows]
    if not samples or len(expected) != len(samples):
        raise ValueError("Expected nonempty samples with distinct IDs")
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError("Results must contain exactly one record for every evaluation ID")
    for key in ("mode", "temperature", "options", "model", "prompt_version", "model_digest",
                "quantization", "environment_sha256", "prompt_sha256", "schema_sha256"):
        if len({json.dumps(row.get(key), sort_keys=True) for row in rows}) != 1:
            raise ValueError(f"Mixed '{key}' values inside one result file")
    counts = dict.fromkeys(METRICS, 0)
    received = api_errors = 0
    predictions = {}
    for row in rows:
        sample = expected[row["id"]]
        if row["true_category"] != sample["true_category"]:
            raise ValueError(f"Reference category mismatch for ID {row['id']}")
        if "text_sha256" in row and row["text_sha256"] != pipeline.fingerprint(sample["text"]):
            raise ValueError("Result source text changed")
        api_errors += row["api_error"] is not None
        received += bool(row["response_received"])
        predictions[row["id"]] = None
        if row["response_received"] and row["api_error"] is None:
            if not isinstance(row["raw_output"], str):
                raise ValueError(f"Non-text response for ID {row['id']}")
            flags = evaluate_response(row["raw_output"], sample["true_category"])
            for metric, flag in METRICS.items():
                counts[metric] += flags[flag]
            predictions[row["id"]] = flags["entities"]
    total = len(rows)
    first = rows[0]
    summary = {"total_requests": total, "responses_received": received, "api_errors": api_errors,
               "mode": first.get("mode", "unknown"),
               "temperature": first.get("temperature", 0),
               "options": first.get("options", pipeline.OPTIONS),
               "prompt_version": first.get("prompt_version", pipeline.PROMPT_VERSION),
               "denominator": "all requests (API, parsing and schema failures included)"}
    for metric, count in counts.items():
        summary[metric + "_count"] = count
        summary[metric + "_pct"] = round(count / total * 100, 2)
    elapsed = sum(row["elapsed_seconds"] for row in rows)
    summary["total_measured_seconds"] = round(elapsed, 2)
    summary["average_measured_seconds"] = round(elapsed / total, 2)
    if gold is not None:
        for sample_id, sample in expected.items():
            record = gold.get(sample_id, {})
            if record.get("status") == "completed":
                validate_gold_record(record)
                if record["text_sha256"] != pipeline.fingerprint(sample["text"]):
                    raise ValueError("Manual gold refers to different source text")
        summary["gold_sha256"] = pipeline.fingerprint(gold)
        status = gold_status(list(expected), gold)
        summary["entity_gold"] = status
        summary["entity_f1"] = (entity_scores(predictions, gold) if status["complete"]
                                else PENDING_REVIEW)
    return summary


def category_agreement(rows_a, rows_b):
    """Aynı örneklerde iki ayarın doğruluk farkını örnek bazında sayar (eşleştirilmiş analiz)."""
    b_by_id = {r["id"]: r for r in rows_b}
    table = {"both_correct": 0, "only_first_correct": 0, "only_second_correct": 0,
             "both_wrong": 0, "same_prediction": 0, "both_schema_valid": 0,
             "different_prediction_when_both_valid": 0}
    for row in rows_a:
        a = evaluate_response(row["raw_output"] if row["response_received"] and not row["api_error"] else "", row["true_category"])
        other = b_by_id[row["id"]]
        b = evaluate_response(other["raw_output"] if other["response_received"] and not other["api_error"] else "", other["true_category"])
        key = {(True, True): "both_correct", (True, False): "only_first_correct",
               (False, True): "only_second_correct", (False, False): "both_wrong"}
        table[key[(a["category_correct"], b["category_correct"])]] += 1
        table["same_prediction"] += a["predicted_category"] == b["predicted_category"]
        if a["schema_valid"] and b["schema_valid"]:
            table["both_schema_valid"] += 1
            table["different_prediction_when_both_valid"] += a["predicted_category"] != b["predicted_category"]
    return table


def compare_runs(directory=None):
    """Recompute from raw responses; old summary flags and old F1 are never reused."""
    directory = Path(directory or ROOT / "results")
    samples, gold = load_samples(), load_gold()
    ids = [s["id"] for s in samples]
    if set(gold) != set(ids):
        raise ValueError("Annotation IDs must match the evaluation set")
    for sample in samples:
        if gold[sample["id"]]["text_sha256"] != pipeline.fingerprint(sample["text"]):
            raise ValueError("Annotation source text changed")
    summaries, loaded = {}, {}
    environments = []
    for name, (filename, mode, temperature) in RUNS.items():
        path = directory / filename
        if not path.exists():
            summaries[name] = {"status": "PENDING EXPERIMENT"}
            continue
        metadata = json.loads(path.with_suffix(".metadata.json").read_text())
        if metadata["status"] == "running":
            summaries[name] = {"status": "PENDING EXPERIMENT: running or interrupted"}
            continue
        rows = load_jsonl(path)
        if [r["id"] for r in rows] != ids:
            raise ValueError(f"{filename}: incomplete, duplicated or reordered samples")
        if metadata["status"] != "complete" or metadata["sample_ids"] != ids:
            raise ValueError("Experiment metadata is incomplete")
        for row in rows:
            expected = {"mode": mode, "temperature": temperature,
                        "options": pipeline.build_options(temperature), "format_sent": mode == "schema",
                        "model": pipeline.MODEL, "prompt_version": pipeline.PROMPT_VERSION,
                        "prompt_sha256": pipeline.fingerprint(pipeline.build_prompt("")),
                        "schema_sha256": pipeline.fingerprint(pipeline.JSON_SCHEMA)}
            if any(row.get(k) != v for k, v in expected.items()):
                raise ValueError(f"{filename}: outputs belong to a different request configuration")
        for key in ("environment", "environment_after"):
            env = metadata[key]
            if environment_fingerprint(env) != rows[0]["environment_sha256"]:
                raise ValueError("Experiment environment changed")
            if env["model_digest"] != rows[0]["model_digest"] or env["details"]["quantization_level"] != rows[0]["quantization"]:
                raise ValueError("Model metadata mismatch")
        environments.append(rows[0]["environment_sha256"])
        loaded[name] = rows
        summaries[name] = analyze_results(samples, rows, gold)
    if len(set(environments)) > 1:
        raise ValueError("All four experiments must use the same model and environment")
    result = {"gold_sha256": pipeline.fingerprint(gold), "entity_gold": gold_status(ids, gold),
              "runs": summaries, "paired_classification": None}
    if "prompt_only" in loaded and "schema_constrained" in loaded:
        result["paired_classification"] = category_agreement(loaded["prompt_only"], loaded["schema_constrained"])
    write_json(directory / "metrics.json", result)
    save_comparison_figure({k: v for k, v in summaries.items() if "total_requests" in v}, directory)
    return result


def capture_environment(path=None):
    """Ollama sürümü, model özeti, kuantizasyon ve donanım bilgisini yerel sunucudan okur."""
    base = pipeline.OLLAMA_URL.rsplit("/api/", 1)[0]
    def read_api(endpoint, body=None):
        response = (requests.get(base + endpoint, timeout=5) if body is None
                    else requests.post(base + endpoint, json=body, timeout=10))
        response.raise_for_status()
        return response.json()
    version = read_api("/api/version")["version"]
    show = read_api("/api/show", {"model": pipeline.MODEL})
    tags = read_api("/api/tags")["models"]
    running = read_api("/api/ps").get("models", [])
    digest = next((m["digest"] for m in tags if m["name"] == pipeline.MODEL), None)
    try:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=10, check=True).stdout.strip() or "not available"
    except (OSError, subprocess.SubprocessError):
        gpu = "not available"
    info = show.get("model_info", {})
    environment = {
        "ollama_version": version, "model": pipeline.MODEL, "model_digest": digest,
        "details": show.get("details"),
        "parameter_count": info.get("general.parameter_count"),
        "base_model": info.get("general.base_model.0.repo_url"),
        "loaded_models": [{"name": m["name"], "size": m.get("size"), "size_vram": m.get("size_vram"),
                           "context_length": m.get("context_length")} for m in running],
        "generation_options": pipeline.OPTIONS,
        "sampling_options": pipeline.OPTIONS,
        "platform": platform.platform(), "python": platform.python_version(), "gpu": gpu,
        "model_parameters": show.get("parameters"),
        "model_template": show.get("template"),
        "model_system": show.get("system"),
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    if not digest or not (show.get("details") or {}).get("quantization_level"):
        raise ValueError("Installed model digest/quantization unavailable")
    if path is not None:
        write_json(path, environment)
    return environment


def environment_fingerprint(environment):
    keys = ("ollama_version", "model", "model_digest", "details", "platform", "python", "gpu",
            "model_parameters", "model_template", "model_system")
    return pipeline.fingerprint({k: environment[k] for k in keys})


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_comparison_figure(summaries, figure_dir):
    """Tamamlanan çalışmalar için gruplanmış çubuk grafik (varlık F1 yalnızca doğrulanmışsa)."""
    if not summaries:
        (figure_dir / "metrics.png").unlink(missing_ok=True)
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["Raw JSON\nparsing", "Parsing after\ncleaning", "Schema\nvalidity",
              "Classification\naccuracy", "Entity\nmicro-F1"]
    names = {"prompt_only": "Prompt-only, T=0", "schema_constrained": "Schema, T=0",
             "prompt_only_temp1": "Prompt-only, T=1.0", "schema_constrained_temp1": "Schema, T=1.0"}
    colors = {"prompt_only": "#c17b30", "schema_constrained": "#267c91",
              "prompt_only_temp1": "#ecc08d", "schema_constrained_temp1": "#8ec5d3"}
    width = 0.8 / len(summaries)
    fig, ax = plt.subplots(figsize=(9, 4.2), layout="constrained")
    for index, (name, summary) in enumerate(summaries.items()):
        f1 = summary.get("entity_f1")
        values = [summary[key + "_pct"] for key in METRICS]
        values.append(f1["micro"]["f1_pct"] if isinstance(f1, dict) else float("nan"))
        xs = [i + (index - (len(summaries) - 1) / 2) * width for i in range(len(labels))]
        bars = ax.bar(xs, values, width, label=names[name], color=colors[name])
        text = [f"{v:.0f}" for v in values[:4]] + [f"{values[4]:.0f}" if isinstance(f1, dict) else ""]
        ax.bar_label(bars, labels=text, padding=2, fontsize=7)
    ax.set_xticks(range(len(labels)), labels)
    ax.set(ylim=(0, 112), ylabel="Percent of all requests (n=100 per run)",
           title="qwen2.5:3b: prompt-only vs schema-constrained, T=0 and T=1.0")
    if any(not isinstance(s.get("entity_f1"), dict) for s in summaries.values()):
        ax.text(4, 12, "PENDING\nANNOTATION", ha="center", fontsize=8)
    ax.set_yticks(range(0, 101, 20))
    ax.legend(fontsize=8, ncols=2, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_dir / "metrics.png", dpi=180)
    plt.close(fig)


def run_experiment(path, samples, mode, temperature):
    """One local request per sample, saved immediately; never overwrite responses."""
    if path.exists() or path.with_suffix(".metadata.json").exists():
        raise ValueError(f"Use a new output directory: {path} already exists")
    environment = capture_environment()
    signature = environment_fingerprint(environment)
    metadata = {"status": "running", "environment": environment,
                "sample_ids": [s["id"] for s in samples], "options": pipeline.build_options(temperature)}
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path.with_suffix(".metadata.json"), metadata)
    with path.open("x", encoding="utf-8") as output:
        for index, sample in enumerate(samples, 1):
            row = evaluate_sample(sample, mode, temperature)
            row.update(model_digest=environment["model_digest"],
                       quantization=environment["details"]["quantization_level"],
                       environment_sha256=signature)
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            output.flush()
            print(f"{mode} T={temperature} {index}/{len(samples)}: "
                  f"raw={row['raw_json_valid']} schema={row['schema_valid']} category={row['predicted_category']}", flush=True)
    after = capture_environment()
    if environment_fingerprint(after) != signature:
        raise ValueError("Environment changed during experiment; do not compare this run")
    metadata.update(status="complete", environment_after=after)
    write_json(path.with_suffix(".metadata.json"), metadata)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--run-all", action="store_true")
    action.add_argument("--env", action="store_true")
    parser.add_argument("--directory", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    try:
        if args.env:
            print(json.dumps(capture_environment(), ensure_ascii=False, indent=2))
            return
        if args.run_all:
            if any((args.directory / filename).exists() or (args.directory / filename).with_suffix(".metadata.json").exists() for filename, _, _ in RUNS.values()):
                raise ValueError("Use a new directory; saved experiments are never overwritten")
            for filename, mode, temperature in RUNS.values():
                run_experiment(args.directory / filename, load_samples(), mode, temperature)
        # One entry point updates metrics, plot, Markdown and PDF together.
        from build_report import rebuild
        result = rebuild(args.directory)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, requests.RequestException) as error:
        parser.exit(1, f"Evaluation failed: {error}\n")


if __name__ == "__main__":
    main()
