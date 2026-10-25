"""200 örneklik çalışmayı ham yanıtlardan ölçer; eksik çalışmaya sonuç uydurmaz.

Kullanım: python src/step4_analyze_results.py
Her deneyin 200 kimliği tam değilse yalnız durum/ilerleme yazılır; nihai oranlar
null kalır ve o deneyin karışıklık matrisi üretilmez. Kanonik sonuçlar okunur.
"""

from collections import Counter
import csv
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
METHODS = {
    "A": ("step3a_evaluate_prompt", "improved_prompt_results.jsonl"),
    "B": ("step3b_evaluate_json", "schema_results.jsonl"),
    "C": ("step3c_evaluate_optimized", "optimized_schema_results.jsonl"),
}


def load_jsonl(path):
    """path dosyasındaki boş olmayan JSONL satırlarını liste döndürür.

    Eksik dosya boş liste verir (henüz başlanmamış çalışma). Bozuk satırda
    JSONDecodeError dışarı taşar; yarım kayıt gizlenmez ve payda küçültülmez.
    """
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def recompute(row, sample, module):
    """Bir ölçümün bayraklarını özgün ayrıştırıcıyla yeniden hesaplar.

    row kayıt, sample gerçek haber, module ilgili deney modülüdür.
    Dönüş (dört bayrak sözlüğü, geçerli tahmin veya 'INVALID'). Kayıt ile
    yeniden hesap uyuşmazsa AssertionError verir; kayıt değiştirilmez.
    """
    assert row["true_category"] == sample["true_category"]
    flags = dict.fromkeys(("raw_json_valid", "clean_json_valid", "schema_valid", "category_correct"), False)
    prediction = "INVALID"
    if row["response_received"]:
        raw = row["raw_output"]
        try:
            parsed = json.loads(raw)
            flags["raw_json_valid"] = flags["clean_json_valid"] = True
        except json.JSONDecodeError:
            success, parsed = module.clean_and_parse(raw)
            flags["clean_json_valid"] = success
        if flags["clean_json_valid"]:
            flags["schema_valid"] = module.validate_schema(parsed)
            if flags["schema_valid"]:
                prediction = parsed["category"]
                flags["category_correct"] = prediction == sample["true_category"]
    for key, value in flags.items():
        assert row[key] == value, f"{module.__name__} ID={row['id']} {key} uyuşmuyor"
    return flags, prediction


def analyze_experiment(rows, samples, module):
    """Aynı 200 haber için tek deneyin ölçümünü ve matrisini hazırlar.

    rows kayıt listesi, samples 200 haber, module özgün deney mantığıdır.
    Dönüş: (ölçüm sözlüğü, matris veya None). Yinelenen/fazla ID reddedilir.
    Tam çalışmada genel oranların paydası 200; koşullu doğruluk paydası
    şema geçerli sayısıdır. Sıfır koşullu payda ölçülemez: None döner.
    """
    expected = {s["id"]: s for s in samples}
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "Sonuçlarda aynı kimlik birden fazla kez var."
    assert set(ids) <= set(expected), "Sonuç dosyasında değerlendirme dışı kimlik var."
    categories = sorted(module.CATEGORIES)
    matrix = {c: {p: 0 for p in categories + ["INVALID"]} for c in categories}
    counts = Counter()
    for row in rows:
        flags, prediction = recompute(row, expected[row["id"]], module)
        counts.update({key: int(value) for key, value in flags.items()})
        matrix[row["true_category"]][prediction] += 1
    complete = len(ids) == 200 and set(ids) == set(expected)
    received = sum(bool(r["response_received"]) for r in rows)
    elapsed = round(sum(r["elapsed_seconds"] for r in rows), 2)
    result = {
        "status": "complete" if complete else "pending", "requested_samples": 200,
        "attempted_samples": len(rows), "responses_received": received,
        "api_error_count": sum(r["api_error"] is not None for r in rows),
        "missing_ids": [s["id"] for s in samples if s["id"] not in set(ids)],
        "raw_flags_recomputed": True, "final_metrics": None,
        "progress_counts": dict(counts), "progress_elapsed_seconds": elapsed,
    }
    if not complete:
        return result, None
    correct, schema = counts["category_correct"], counts["schema_valid"]
    # API/biçim/şema hataları INVALID sütununda tutulur; matrisin toplamı
    # daima 200 kalır. Böylece hata kayıtları değerlendirmeden düşmez.
    assert sum(sum(row.values()) for row in matrix.values()) == 200
    assert sum(matrix[c][c] for c in categories) == correct
    support = Counter(s["true_category"] for s in samples)
    assert all(sum(matrix[c].values()) == support[c] for c in categories)
    result["final_metrics"] = {
        "denominator_all_requests": 200,
        "raw_json_success_count": counts["raw_json_valid"],
        "raw_json_success_pct": round(100 * counts["raw_json_valid"] / 200, 2),
        "clean_json_success_count": counts["clean_json_valid"],
        "clean_json_success_pct": round(100 * counts["clean_json_valid"] / 200, 2),
        "schema_success_count": schema, "schema_success_pct": round(100 * schema / 200, 2),
        "category_correct_count": correct, "end_to_end_accuracy_pct": round(100 * correct / 200, 2),
        "conditional_accuracy_denominator": schema,
        "conditional_accuracy_pct": round(100 * correct / schema, 2) if schema else None,
        "total_inference_seconds": elapsed, "mean_inference_seconds": round(elapsed / 200, 2),
        "per_category": {c: {"total": support[c], "correct": matrix[c][c],
            "accuracy_pct": round(100 * matrix[c][c] / support[c], 2)} for c in categories},
    }
    return result, matrix


def collect_summary():
    """Ham yanıtları doğrular; dosya yazmadan güncel metrikleri ve matrisleri döndürür."""
    samples = load_jsonl(ROOT / "data/test_samples.jsonl")
    assert len(samples) == 205 and len({s["id"] for s in samples}) == 205
    selection = json.loads((ROOT / "data/test_samples_manifest.json").read_text())
    import hashlib
    assert hashlib.sha256((ROOT / "data/test_samples.jsonl").read_bytes()).hexdigest() == selection["expanded_sha256"]
    evaluation = samples[5:205]
    ids = [s["id"] for s in evaluation]
    assert ids == selection["evaluation_ids"]
    assert [s["id"] for s in samples[:5]] == selection["development_ids"]
    groups = {}
    for sample in evaluation:
        groups.setdefault(sample["text"], []).append(sample["id"])
    summary = {
        "dataset": {"total_records": len(samples), "development_records": 5,
                    "evaluation_records": len(evaluation), "evaluation_slice": "samples[5:205]",
                    "unique_record_ids": len({s["id"] for s in samples}),
                    "unique_texts": len({s["text"] for s in samples}),
                    "unique_evaluation_texts": len(groups),
                    "duplicate_evaluation_text_ids": [group for group in groups.values() if len(group) > 1],
                    "development_ids": selection["development_ids"],
                    "evaluation_category_counts": dict(sorted(Counter(s["true_category"] for s in evaluation).items()))},
        "evaluation_ids": ids, "experiments": {},
    }
    matrices = {}
    for key, (name, filename) in METHODS.items():
        module = importlib.import_module(name)
        rows = load_jsonl(OUT / filename)
        result, matrix = analyze_experiment(rows, evaluation, module)
        result["results_file"] = "results/" + filename
        if matrix is not None:
            assert [r["id"] for r in rows] == ids, "Sonuç sırası veri sırasıyla uyuşmuyor."
        result["failure_breakdown"] = {
            "unparseable_after_cleaning": sum(not r["clean_json_valid"] for r in rows),
            "parsed_but_schema_invalid": sum(r["clean_json_valid"] and not r["schema_valid"] for r in rows),
            "schema_invalid_with_length_stop": sum(not r["schema_valid"] and r.get("done_reason") == "length" for r in rows),
            "schema_invalid_other_or_unrecorded_stop": sum(not r["schema_valid"] and r.get("done_reason") != "length" for r in rows),
            "stop_reasons": dict(Counter(r.get("done_reason", "unrecorded") for r in rows)),
            "max_recorded_eval_count": max((r.get("eval_count", 0) or 0 for r in rows), default=0) or None,
        }
        summary["experiments"][key] = result
        matrices[key] = matrix
    summary["status"] = "complete" if all(r["status"] == "complete" for r in summary["experiments"].values()) else "pending"
    # Varlıkların yalnız yapısını ölçer; anlamsal NER/halüsinasyon puanı değildir.
    c_module = importlib.import_module(METHODS["C"][0])
    lists = duplicates = over_limit = responses = 0
    for row in load_jsonl(OUT / METHODS["C"][1]):
        if not row["schema_valid"]:
            continue
        success, parsed = c_module.clean_and_parse(row["raw_output"])
        assert success
        responses += 1
        for values in parsed["entities"].values():
            normalized = [v.casefold().strip() for v in values]
            lists += 1
            duplicates += len(normalized) != len(set(normalized))
            over_limit += len(values) > 5
    summary["entity_structure_C"] = {"schema_valid_responses_checked": responses,
        "entity_lists_checked": lists, "lists_with_duplicates": duplicates,
        "lists_exceeding_five": over_limit, "semantic_ner_evaluated": False}
    return summary, matrices


def main():
    """Metrikleri ve A/B/C matrislerini kanonik yollara yazar; çıkarım yapmaz."""
    summary, matrices = collect_summary()
    OUT.mkdir(parents=True, exist_ok=True)
    for key, matrix in matrices.items():
        if matrix is None:
            continue
        categories = sorted(matrix)
        columns = categories + ["INVALID"]
        filename = "v3_confusion_matrix.csv" if key == "C" else f"confusion_matrix_{key}.csv"
        with (OUT / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Actual / Predicted"] + columns)
            for category in categories:
                writer.writerow([category] + [matrix[category][p] for p in columns])
    (OUT / "metrics_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Değerlendirme durumu", "", "5 geliştirme + 200 değerlendirme kaydı. Geliştirme kayıtları ana metriklere dahil değildir.", "",
             "200 farklı değerlendirme ID'si, 199 farklı metin; 2138 ve 2296 aynı metindir.", "",
             "| Deney | Kayıt | Yanıt | API hatası | Durum |", "|---|---:|---:|---:|---|"]
    for key, result in summary["experiments"].items():
        lines.append(f"| {key} | {result['attempted_samples']} | {result['responses_received']} | {result['api_error_count']} | {result['status']} |")
    lines += ["", "Genel payda 200; koşullu doğruluk paydası şema geçerli kayıt sayısıdır.",
              "Metrikler: [metrics_summary.json](metrics_summary.json). INVALID sütunu bütün başarısız çıktıları korur."]
    (OUT / "STATUS_TR.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary["status"], {k: r["attempted_samples"] for k, r in summary["experiments"].items()})


if __name__ == "__main__":
    main()


