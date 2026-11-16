"""Değerlendirme: tarihsel analiz, kontrollü deneyler, karşılaştırma ve varlık F1.

    python src/evaluate.py                     # tarihsel 200 yanıtın çevrimdışı analizi
    python src/evaluate.py --env               # Ollama/model/kuantizasyon kanıtı (yerel sunucu gerekir)
    python src/evaluate.py --run --mode prompt --temperature 0 --results results/prompt_only.jsonl
    python src/evaluate.py --compare           # comparison.json, temperature_comparison.json, grafikler
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
DATA_PATH = ROOT / "data/test_samples.jsonl"
IDS_PATH = ROOT / "data/evaluation_ids.json"
GOLD_PATH = ROOT / "data/entity_gold.jsonl"
RESULT_PATH = ROOT / "results/optimized_schema_results.jsonl"  # Tarihsel; asla yeniden yazılmaz.
FIGURE_DIR = ROOT / "results/figures"
METRICS = {
    "raw_json_success": "raw_json_valid",
    "clean_json_success": "clean_json_valid",
    "schema_success": "schema_valid",
    "classification_accuracy": "category_correct",
}
# Kontrollü deneyler: ad -> (sonuç dosyası, mod, sıcaklık). Hepsi aynı 100 kimliği kullanır.
RUNS = {
    "prompt_only": ("results/prompt_only.jsonl", "prompt", 0),
    "schema_constrained": ("results/schema_constrained.jsonl", "schema", 0),
    "prompt_only_temp1": ("results/prompt_only_temp1.jsonl", "prompt", 1.0),
    "schema_constrained_temp1": ("results/schema_constrained_temp1.jsonl", "schema", 1.0),
}
PENDING_REVIEW = "PENDING HUMAN REVIEW"


def load_jsonl(path):
    """Bozuk veya eksik kayıtları gizlemeden JSONL dosyasını okur."""
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


# ---------------------------------------------------------------- örnek seçimi

def select_evaluation_ids(eval_samples, total=100):
    """Deterministik, dengeli seçim: dosya sırasında ilerle, yinelenen metni atla,
    kategori kotası dolana kadar al. 100 = 7 x 14 + 2; alfabetik ilk iki kategori 15 alır."""
    categories = sorted({s["true_category"] for s in eval_samples})
    base, extra = divmod(total, len(categories))
    quota = {c: base + (i < extra) for i, c in enumerate(categories)}
    seen_texts, selected = set(), []
    for sample in eval_samples:
        category = sample["true_category"]
        if sample["text"] in seen_texts or quota[category] == 0:
            continue
        seen_texts.add(sample["text"])
        quota[category] -= 1
        selected.append(sample["id"])
    if len(selected) != total:
        raise ValueError("Not enough samples to fill the category quotas")
    return selected


def load_samples(which="selected"):
    """'all' = tarihsel 200 değerlendirme kaydı; 'selected' = kayıtlı 100 kimlik (aynı sırada)."""
    all_samples = load_jsonl(DATA_PATH)
    if len(all_samples) != 205:
        raise ValueError("The frozen dataset must contain 205 records")
    eval_samples = all_samples[5:205]
    if which == "all":
        return eval_samples
    ids = json.loads(IDS_PATH.read_text(encoding="utf-8"))["ids"]
    if len(ids) != 100 or len(set(ids)) != 100:
        raise ValueError("Selection must contain 100 distinct IDs")
    by_id = {s["id"]: s for s in eval_samples}
    selected = [by_id[i] for i in ids]
    if len({s["text"] for s in selected}) != len(selected):
        raise ValueError("Selected texts must be distinct")
    return selected


# ---------------------------------------------------------------- varlık eşleştirme

def normalize_entity(name):
    """NFC, Turkish casing, underscores as spaces, collapsed whitespace; punctuation retained."""
    name = unicodedata.normalize("NFC", name)
    name = name.replace("İ", "i").replace("I", "ı").lower().replace("_", " ")
    return " ".join(name.split())


def match_entities(predicted, gold):
    """Tip içi bire bir eşleşme. Gold öğesi 'ad | kısaltma' biçiminde eş adlar içerebilir.

    Tekrarlanan tahminler bir kez sayılır; bir gold varlığı en fazla bir tahminle eşleşir.
    (tp, fp, fn) döndürür."""
    preds = list(dict.fromkeys(n for n in map(normalize_entity, predicted) if n))
    golds = []
    for entry in gold:
        aliases = frozenset(n for n in map(normalize_entity, entry.split("|")) if n)
        if aliases and aliases not in golds:
            golds.append(aliases)
    # Ambiguous aliases cannot identify two different gold entities reliably.
    for index, aliases in enumerate(golds):
        if any(aliases & other for other in golds[:index]):
            raise ValueError("Overlapping gold aliases: disambiguate during review")
    matched = set()
    for pred in preds:
        for index, aliases in enumerate(golds):
            if index not in matched and pred in aliases:
                matched.add(index)
                break
    tp = len(matched)
    return tp, len(preds) - tp, len(golds) - tp


def prf(tp, fp, fn):
    """Kesinlik, duyarlılık, F1 (yüzde). Pay/payda sıfırsa 0."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision_pct": round(precision * 100, 2),
            "recall_pct": round(recall * 100, 2), "f1_pct": round(f1 * 100, 2)}


def load_gold(path=GOLD_PATH):
    """Gold kayıtlarını kimliğe göre döndürür; yinelenen kimlik hatadır."""
    if not Path(path).exists():
        return {}
    records = load_jsonl(path)
    gold = {r["id"]: r for r in records}
    if len(gold) != len(records):
        raise ValueError("Duplicate IDs in entity gold file")
    for record in records:
        validate_gold_record(record)
    return gold


def validate_gold_record(record):
    if record.get("status") not in ("candidate", "verified"):
        raise ValueError("Unknown gold review status")
    for kind in pipeline.ENTITY_TYPES:
        names = record.get(kind)
        if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() for n in names):
            raise ValueError("Gold entities must be nonempty strings in lists")
        if len(names) > 5:
            raise ValueError("Gold policy: first five distinct entities per type")
        match_entities([], names)
    if record["status"] == "verified" and not all(record.get(k) for k in ("reviewer", "reviewed_at", "text_sha256")):
        raise ValueError("Verified gold needs reviewer, time and source-text fingerprint")


def gold_status(ids, gold):
    """Yalnızca 'verified' kayıtlar sayılır; aday (AI önerisi) kayıtlar asla gold değildir."""
    verified = [i for i in ids if gold.get(i, {}).get("status") == "verified"]
    return {"selected": len(ids), "verified": len(verified),
            "complete": len(verified) == len(ids)}


def entity_scores(predictions, gold):
    """predictions: {id: entities veya None}. Geçersiz çıktı = boş tahmin (tüm gold -> FN).
    Mikro ortalama: tüm örnekler ve üç tip üzerinden toplanan tp/fp/fn."""
    totals = {t: [0, 0, 0] for t in sorted(pipeline.ENTITY_TYPES)}
    for sample_id, entities in predictions.items():
        record = gold[sample_id]
        validate_gold_record(record)
        if record.get("status") != "verified":
            raise ValueError(f"Gold entities for ID {sample_id} are not human-verified")
        for entity_type in totals:
            predicted = (entities or {}).get(entity_type, [])
            counts = match_entities(predicted, record[entity_type])
            totals[entity_type] = [a + b for a, b in zip(totals[entity_type], counts)]
    result = {t: prf(*c) for t, c in totals.items()}
    result["micro"] = prf(*[sum(c[i] for c in totals.values()) for i in range(3)])
    return result


# ---------------------------------------------------------------- sonuç analizi

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
               "mode": first.get("mode", "schema (historical)"),
               "temperature": first.get("temperature", 0),
               "options": first.get("options", pipeline.OPTIONS),
               "prompt_version": first.get("prompt_version", "v1"),
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
            if record.get("status") == "verified":
                validate_gold_record(record)
                if record["text_sha256"] != pipeline.fingerprint(sample["text"]):
                    raise ValueError("Verified gold refers to different source text")
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


def failure_breakdown(rows):
    """Şema dışı yanıtların nedenleri ve temizlemeyle kurtarılan yanıt sayısı."""
    reasons = {"api_error": 0, "not_parseable": 0, "invalid_category": 0,
               "wrong_structure": 0, "recovered_by_cleaning": 0}
    for row in rows:
        if row["api_error"] is not None:
            reasons["api_error"] += 1
            continue
        parsed, raw_ok, clean_ok = pipeline.parse_json_response(row["raw_output"])
        reasons["recovered_by_cleaning"] += clean_ok and not raw_ok
        if not clean_ok:
            reasons["not_parseable"] += 1
        elif not pipeline.validate_schema(parsed):
            category = parsed.get("category") if isinstance(parsed, dict) else None
            invalid_cat = isinstance(category, str) and category not in pipeline.CATEGORIES
            reasons["invalid_category" if invalid_cat else "wrong_structure"] += 1
    return reasons


def compare_runs(run_dir=None):
    """Dört kontrollü çalışmayı aynı 100 kimlik ve aynı sırayla karşılaştırır."""
    samples = load_samples("selected")
    run_dir = Path(run_dir) if run_dir is not None else ROOT / "results"
    order = [s["id"] for s in samples]
    gold = load_gold()
    loaded, summaries = {}, {}
    for name, (relative, mode, temperature) in RUNS.items():
        path = run_dir / Path(relative).name
        if not path.exists():
            summaries[name] = {"status": "PENDING: run not executed", "command":
                               f"python src/evaluate.py --run --mode {mode} "
                               f"--temperature {temperature} --results {path}"}
            continue
        rows = load_jsonl(path)
        if len(rows) < len(order) and [r["id"] for r in rows] == order[:len(rows)]:
            summaries[name] = {"status": "PENDING: incomplete run", "saved_records": len(rows)}
            continue
        if [r["id"] for r in rows] != order:
            raise ValueError(f"{relative}: IDs or order differ from data/evaluation_ids.json")
        if rows[0]["mode"] != mode or rows[0]["temperature"] != temperature:
            raise ValueError(f"{relative}: mode/temperature do not match {name}")
        for row in rows:
            if row.get("format_sent") != (mode == "schema"):
                raise ValueError("format flag inconsistent with experimental mode")
            if row.get("options", {}).get("temperature") != temperature:
                raise ValueError("Recorded options disagree with experiment temperature")
            for key in ("model_digest", "quantization", "environment_sha256", "prompt_sha256", "schema_sha256"):
                if not row.get(key):
                    raise ValueError(f"Missing provenance: {key}")
        metadata_path = path.with_suffix(".metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("status") != "complete" or metadata.get("environment_sha256") != rows[0]["environment_sha256"]:
            raise ValueError("Missing completed environment verification")
        if metadata.get("sample_ids") != order or metadata.get("options") != rows[0]["options"]:
            raise ValueError("Metadata differs from recorded requests")
        for snapshot in ("environment", "environment_after"):
            environment = metadata[snapshot]
            if environment_fingerprint(environment) != rows[0]["environment_sha256"]:
                raise ValueError("Environment snapshot fingerprint mismatch")
            if environment["model_digest"] != rows[0]["model_digest"] or environment["details"]["quantization_level"] != rows[0]["quantization"]:
                raise ValueError("Recorded model differs from environment evidence")
        loaded[name] = rows
        source = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        summaries[name] = dict(analyze_results(samples, rows, gold), source_results=source,
                               failures=failure_breakdown(rows))
    # Birincil karşılaştırmada tek fark format olmalı.
    if {"prompt_only", "schema_constrained"} <= set(loaded):
        a, b = loaded["prompt_only"][0], loaded["schema_constrained"][0]
        check_controlled_pair(a, b)
    comparison = {
        "samples": len(order), "evaluation_ids": "data/evaluation_ids.json",
        "controlled_difference": "presence of Ollama format=JSON_SCHEMA only",
        "prompt_only": summaries["prompt_only"],
        "schema_constrained": summaries["schema_constrained"],
    }
    if {"prompt_only", "schema_constrained"} <= set(loaded):
        comparison["paired_classification"] = dict(
            category_agreement(loaded["prompt_only"], loaded["schema_constrained"]),
            first="prompt_only", second="schema_constrained")
    temperature = {"samples": len(order),
                   "controlled_difference": "temperature 0 vs 1.0 (same mode, seed, prompt, options)",
                   "runs": {name: summaries[name] for name in RUNS}}
    for mode_name in ("prompt_only", "schema_constrained"):
        t1 = mode_name + "_temp1"
        if {mode_name, t1} <= set(loaded):
            check_controlled_pair(loaded[mode_name][0], loaded[t1][0], temperature=True)
            temperature[f"paired_{mode_name}"] = dict(
                category_agreement(loaded[mode_name], loaded[t1]), first="temperature 0",
                second="temperature 1.0")
    write_json(run_dir / "comparison.json", comparison)
    write_json(run_dir / "temperature_comparison.json", temperature)
    save_comparison_figure({k: v for k, v in summaries.items() if "total_requests" in v}, run_dir / "figures")
    return comparison, temperature


def check_controlled_pair(a, b, temperature=False):
    """Reject mixed model, prompt, schema, hardware/software or generation settings."""
    for key in ("model", "model_digest", "quantization", "environment_sha256", "prompt_version",
                "prompt_sha256", "schema_sha256"):
        if not a.get(key) or a[key] != b.get(key):
            raise ValueError(f"Uncontrolled difference: {key}")
    ao, bo = dict(a["options"]), dict(b["options"])
    if temperature:
        ao.pop("temperature"); bo.pop("temperature")
        if a["mode"] != b["mode"]:
            raise ValueError("Temperature comparison must keep mode fixed")
    if ao != bo:
        raise ValueError("Uncontrolled generation options")


# ---------------------------------------------------------------- ortam kanıtı

def capture_environment(path=ROOT / "results/environment.json"):
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
        "top_k_top_p": "not explicitly set (Ollama/model defaults)",
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


# ---------------------------------------------------------------- çıktı yardımcıları

def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_figure(summary, path):
    """Tarihsel çalışma: dört oran, tüm isteklerden oluşan ortak paydayla."""
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


def save_comparison_figure(summaries, figure_dir=FIGURE_DIR):
    """Tamamlanan çalışmalar için gruplanmış çubuk grafik (varlık F1 yalnızca doğrulanmışsa)."""
    if not summaries:
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
        ax.text(4, 12, "PENDING\nHUMAN REVIEW", ha="center", fontsize=8)
    ax.set_yticks(range(0, 101, 20))
    ax.legend(fontsize=8, ncols=2, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_dir / "mode_temperature_comparison.png", dpi=180)
    plt.close(fig)


def run_experiment(path, samples, mode, temperature, resume=False):
    """Yeni dosyaya (asla üzerine yazmadan) her yanıtı anında kaydeder."""
    if path.exists() and not resume:
        raise ValueError(f"Refusing to overwrite {path}; use a new filename")
    environment = capture_environment(path=None)
    signature = environment_fingerprint(environment)
    metadata = {"status": "running", "environment": environment, "environment_sha256": signature,
                "sample_ids": [s["id"] for s in samples], "mode": mode,
                "options": pipeline.build_options(temperature)}
    metadata_path = path.with_suffix(".metadata.json")
    completed = []
    if resume:
        previous = json.loads(metadata_path.read_text(encoding="utf-8"))
        completed = load_jsonl(path)
        if previous.get("status") != "running":
            raise ValueError("Only interrupted runs with status=running may be resumed")
        for key in ("environment_sha256", "sample_ids", "mode", "options"):
            if previous.get(key) != metadata[key]:
                raise ValueError(f"Cannot resume: {key} changed")
        if [r["id"] for r in completed] != metadata["sample_ids"][:len(completed)]:
            raise ValueError("Cannot resume: duplicate, missing or reordered IDs")
        for sample, row in zip(samples, completed):
            request = pipeline.build_request(sample["text"], mode, temperature)
            expected = {"mode": mode, "temperature": temperature, "options": request["options"],
                        "model": pipeline.MODEL, "model_digest": environment["model_digest"],
                        "environment_sha256": signature, "format_sent": mode == "schema",
                        "text_sha256": pipeline.fingerprint(sample["text"]),
                        "prompt_sha256": pipeline.fingerprint(pipeline.build_prompt("")),
                        "schema_sha256": pipeline.fingerprint(pipeline.JSON_SCHEMA)}
            if any(row.get(k) != v for k, v in expected.items()):
                raise ValueError("Cannot resume: saved request provenance differs")
        metadata = previous
        metadata.setdefault("resumed_at", []).append(environment["captured_at"])
    write_json(metadata_path, metadata)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a" if resume else "x", encoding="utf-8") as output:
        for index, sample in enumerate(samples[len(completed):], len(completed) + 1):
            row = evaluate_sample(sample, mode=mode, temperature=temperature)
            row.update(model_digest=environment["model_digest"],
                       quantization=environment["details"]["quantization_level"],
                       environment_sha256=signature,
                       recorded_at=datetime.now(timezone.utc).isoformat())
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            output.flush()
            print(f"[{index}/{len(samples)}] ID={row['id']} mode={mode} T={temperature} "
                  f"raw={row['raw_json_valid']} schema={row['schema_valid']} "
                  f"pred={row['predicted_category']} true={row['true_category']}", flush=True)
    after = capture_environment(path=None)
    if environment_fingerprint(after) != signature:
        metadata["status"] = "INVALID: environment changed during run"
        write_json(metadata_path, metadata)
        raise ValueError(metadata["status"])
    metadata.update(status="complete", environment_after=after)
    write_json(metadata_path, metadata)


def main():
    """Varsayılan: tarihsel yanıtların çevrimdışı analizi. Yeni çıkarım yeni dosya ister."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--analyze", action="store_true", help="reanalyze saved responses (default)")
    action.add_argument("--run", action="store_true", help="make new local Ollama requests")
    action.add_argument("--compare", action="store_true", help="compare the four controlled runs")
    action.add_argument("--env", action="store_true", help="record Ollama/model environment")
    parser.add_argument("--results", type=Path, help="saved input, or NEW output with --run")
    parser.add_argument("--mode", choices=pipeline.MODES, default="schema")
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--resume", action="store_true", help="resume an interrupted run after provenance checks")
    parser.add_argument("--directory", type=Path, help="directory of named run files for --compare (default: results)")
    parser.add_argument("--samples", choices=["selected", "all"],
                        help="selected = 100 IDs in data/evaluation_ids.json; all = 200 records")
    args = parser.parse_args()
    if args.resume and not args.run:
        parser.error("--resume requires --run")
    if args.directory and not args.compare:
        parser.error("--directory is only used with --compare")
    try:
        if args.env:
            print(json.dumps(capture_environment(), indent=2))
            return
        if args.compare:
            comparison, temperature = compare_runs(args.directory)
            print(json.dumps({"comparison": comparison, "temperature": temperature}, indent=2))
            return
        if args.run and args.results is None:
            parser.error("--run requires --results with a new filename")
        path = args.results.resolve() if args.results else RESULT_PATH
        if path.suffix != ".jsonl":
            parser.error("--results must be a .jsonl file")
        which = args.samples or ("all" if path == RESULT_PATH else "selected")
        samples = load_samples(which)
        if args.run:
            temperature = int(args.temperature) if args.temperature.is_integer() else args.temperature
            if path.name in {Path(r[0]).name for r in RUNS.values()}:
                expected = next(r for r in RUNS.values() if Path(r[0]).name == path.name)
                if (args.mode, temperature) != (expected[1], expected[2]):
                    parser.error(f"{path.name} is reserved for mode={expected[1]}, T={expected[2]}")
            run_experiment(path, samples, args.mode, temperature, resume=args.resume)
        rows = load_jsonl(path)
        gold = load_gold() if which == "selected" else None
        summary = analyze_results(samples, rows, gold)
        summary["source_results"] = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        summary["analysis"] = "Recomputed from saved raw responses; timing comes from saved measurements"
        # Yalnızca tarihsel dosya yayımlanmış özeti/grafiği günceller; diğerleri yanına yazılır.
        summary_path = ROOT / "results/summary.json" if path == RESULT_PATH else path.with_suffix(".summary.json")
        if summary_path.exists() and summary_path.samefile(path):
            raise ValueError("Summary path must differ from the response file")
        write_json(summary_path, summary)
        if path == RESULT_PATH:
            save_figure(summary, FIGURE_DIR / "json_success.png")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, requests.RequestException) as error:
        parser.exit(1, f"Evaluation failed: {error}\n")


if __name__ == "__main__":
    main()
