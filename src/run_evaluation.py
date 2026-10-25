"""Aynı 200 haberle üç ayrı deneyi başlatır; özgün çıkarım mantığını çağırır.

Kullanım: python src/run_evaluation.py
Önce Ollama erişimi ve model varlığı kontrol edilir. Böylece sunucuya hiç
erişilemeyen ortamda 600 yapay hata kaydı ile checkpoint dosyaları dolmaz.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import requests

from analyze_final import METHODS, OUT, ROOT, load_jsonl, collect_summary, main as analyze


def main():
    """Hazırlık kontrolü, ayrı süreçlerle üç deney ve son analizi yürütür.

    Parametre yok. Dönüş None; erişim yoksa açıklayıcı hata ve başarısız çıkış.
    İstekler/promptlar değiştirilmez; her özgün main --limit 200 ile çağrılır.
    Çalışma kimliği veri/kod karmalarını ve Ollama sürüm/model bilgisini saklar.
    Sürdürürken bu bilgiler değişirse karışık çalışma oluşmaması için durur.
    """
    samples = load_jsonl(ROOT / "data/test_samples.jsonl")
    assert len(samples) == 205 and len({s["id"] for s in samples}) == 205
    summary, _ = collect_summary()
    if summary["status"] == "complete":
        print("All three experiments already contain 200 verified records; no inference needed.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        version = requests.get("http://localhost:11434/api/version", timeout=5)
        version.raise_for_status()
        tags = requests.get("http://localhost:11434/api/tags", timeout=5)
        tags.raise_for_status()
        models = [m for m in tags.json()["models"] if m.get("name") == "qwen2.5:3b"]
        if not models:
            raise ValueError("Ollama içinde qwen2.5:3b bulunamadı.")
        model = models[0]
        # Modelin varsayılan parametreleri de kayıt altına alınır; yeni
        # örnekleme seçeneği eklenmez ve model değiştirilmez.
        info = requests.post("http://localhost:11434/api/show", json={"model": "qwen2.5:3b"}, timeout=10)
        info.raise_for_status()
        identity = {
            "ollama_version": version.json()["version"], "model": model["name"],
            "model_digest": model["digest"], "model_parameters": info.json().get("parameters"),
            "dataset_sha256": hashlib.sha256((ROOT / "data/test_samples.jsonl").read_bytes()).hexdigest(),
            "script_sha256": {name: hashlib.sha256((ROOT / "src" / (name + ".py")).read_bytes()).hexdigest()
                for name, _ in METHODS.values()},
            "reuse_historical_results": False,
        }
    except (requests.RequestException, KeyError, ValueError) as error:
        (OUT / "execution_environment.json").write_text(json.dumps({
            "status": "blocked_before_inference", "reason": str(error),
            "new_inference_records_written": 0,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        analyze()
        raise SystemExit(f"Çıkarım başlatılamadı: {error}")

    manifest = OUT / "run_identity.json"
    if manifest.exists():
        assert json.loads(manifest.read_text()) == identity, "Çalışma ayarları değişmiş; mevcut koşuya eklenemez."
    else:
        assert not any(load_jsonl(OUT / filename) for _, filename in METHODS.values()), "Kimlik manifesti olmayan sonuçlara ekleme yapılmaz."
        manifest.write_text(json.dumps(identity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "execution_environment.json").write_text(json.dumps({
        "status": "preflight_passed", "ollama_version": identity["ollama_version"],
        "model_digest": identity["model_digest"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Önce mevcut kayıtların benzersiz ve aynı veri kümesine ait olduğunu denetler.
    analyze()
    for name, _ in METHODS.values():
        subprocess.run([sys.executable, str(ROOT / "src" / (name + ".py")), "--limit", "200"], cwd=ROOT, check=True)
    analyze()


if __name__ == "__main__":
    main()
