"""İlk 140 kaydı koruyarak 65 yeni TTC4900 haberi ekler; model çalıştırmaz.

Kullanım: python src/step1_prepare_dataset.py [--source-arrow önbellek.arrow]
Eski filtre 150–3000 karakterdir. Sabit tohum 42, hedef değerlendirme
dağılımı alfabetik ilk dört sınıfta 29, son üç sınıfta 28 haberdir.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from datasets import Dataset, load_dataset

ROOT = Path(__file__).resolve().parents[1]
SEED = 42


def main():
    """Kaynağı doğrula, eksik sınıf kotalarını doldur ve yeni dosyayı yaz.

    Parametreler: --source-arrow, mevcut Hugging Face önbelleğini salt okunur
    açmak için isteğe bağlı yoldur. Yoksa load_dataset kullanılır.
    Dönüş: None; data/test_samples.jsonl ve seçim manifesti yazılır.
    Eski 140 satırın metni/etiketi kaynak indeksleriyle uyuşmazsa durur.
    Yetersiz aday veya önceden var olan farklı çıktı sessizce geçilmez.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-arrow", type=Path)
    args = parser.parse_args()
    # Arrow, datasets kütüphanesinin disk üzerindeki tablo biçimidir. Bu yol
    # ağa veya korumalı önbellek dizinine yazmadan aynı kaynak veriyi açar.
    if args.source_arrow:
        dataset = Dataset.from_file(str(args.source_arrow))
    else:
        dataset = load_dataset("savasy/ttc4900", split="train")
    labels = dataset.features["category"].names
    assert len(dataset) == 4900 and len(labels) == 7
    # Eski seçim algoritmasını da yeniden oynatırız; böylece kaynak satır
    # sırasının tarihsel ID anlamını koruduğuna dair ek kanıt sağlanır.
    rng = random.Random(SEED)
    indices = list(range(len(dataset)))
    rng.shuffle(indices)
    replay, counts = [], Counter()
    for i in indices:
        row = dataset[i]
        category, article = labels[row["category"]], row["text"].strip()
        if not 150 <= len(article) <= 3000 or counts[category] >= 20:
            continue
        replay.append({"id": i, "text": article, "true_category": category})
        counts[category] += 1
    rng.shuffle(replay)
    old = replay
    assert len(old) == 140 and len({r["id"] for r in old}) == 140
    original_bytes = "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in old).encode("utf-8")

    # 200 = 4*29 + 3*28. Kota geliştirme dahil toplamda değil, yalnızca
    # old[5:] değerlendirme diliminde hesaplanır. İlk 140 yer değiştirmez.
    targets = {c: 29 if j < 4 else 28 for j, c in enumerate(sorted(labels))}
    counts = Counter(s["true_category"] for s in old[5:])
    seen = {s["id"] for s in old}
    seen_texts = {s["text"] for s in old}
    added = []
    for i in indices:
        if i in seen:
            continue
        row = dataset[i]
        category, article = labels[row["category"]], row["text"].strip()
        if not 150 <= len(article) <= 3000:
            continue
        # Tarihsel metin tekrarı korunur; yeni eklerde aynı haber yeniden seçilmez.
        if article in seen_texts:
            continue
        if counts[category] >= targets[category]:
            continue
        added.append({"id": i, "text": article, "true_category": category})
        seen.add(i)
        seen_texts.add(article)
        counts[category] += 1
    assert len(added) == 65 and dict(counts) == targets
    assert len(seen) == 205
    assert len(seen_texts) == len({s["text"] for s in old}) + 65
    assert original_bytes.endswith(b"\n"), "Özgün satır sonu bekleniyor."
    expanded = original_bytes + "".join(
        json.dumps(s, ensure_ascii=False) + "\n" for s in added
    ).encode("utf-8")
    output = ROOT / "data/test_samples.jsonl"
    manifest_path = ROOT / "data/test_samples_manifest.json"
    if manifest_path.exists():
        saved = json.loads(manifest_path.read_text())
        assert hashlib.sha256(expanded).hexdigest() == saved["expanded_sha256"], "Veri üyeliği veya sırası değiştirilemez."
    if output.exists():
        assert output.read_bytes() == expanded, "Farklı mevcut çıktı üzerine yazılmadı."
    else:
        output.write_bytes(expanded)
    manifest = {
        "source": "savasy/ttc4900", "split": "train", "seed": SEED,
        "dataset_fingerprint": dataset._fingerprint,
        "source_arrow_sha256": hashlib.sha256(args.source_arrow.read_bytes()).hexdigest()
        if args.source_arrow else None,
        "original_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "expanded_sha256": hashlib.sha256(expanded).hexdigest(),
        "filter": "150 <= len(text.strip()) <= 3000",
        "selection": "random.Random(42).shuffle(indices); exclude old IDs and already selected texts for additions; fill evaluation quotas; append without reshuffling",
        "unique_texts": len(seen_texts),
        "historical_duplicate_text_ids": [[s["id"] for s in old if s["text"] == text]
            for text, count in Counter(s["text"] for s in old).items() if count > 1],
        "original_selection_replayed": True, "first_140_byte_identical": True,
        "total": 205, "development_ids": [s["id"] for s in old[:5]],
        "evaluation_ids": [s["id"] for s in (old + added)[5:]],
        "new_ids": [s["id"] for s in added], "evaluation_category_counts": targets,
    }
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": 205, "added": 65, "evaluation": dict(counts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
