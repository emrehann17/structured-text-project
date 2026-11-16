"""Varlık gold etiketleri için insan inceleme aracı (terminal tabanlı).

    python src/annotate_entities.py --status                 # ilerleme
    python src/annotate_entities.py --reviewer "Ad Soyad"    # sıradaki doğrulanmamış kaydı incele
    python src/annotate_entities.py --reviewer "Ad Soyad" --id 296   # belirli kaydı (yeniden) incele

Her kayıt için haber metninin tamamı gösterilir. Her liste için:
    Enter          -> mevcut listeyi koru
    -              -> listeyi boşalt
    a; b | c       -> listeyi değiştir (';' varlıkları, '|' aynı varlığın eş adlarını ayırır)
Ardından 'y' ile kayıt 'verified' olarak işaretlenir. Aday (AI) öneriler asla otomatik doğrulanmaz.
Kurallar: docs/ANNOTATION_GUIDELINES.md
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import textwrap

from evaluate import GOLD_PATH, gold_status, load_gold, load_samples, normalize_entity, validate_gold_record
from llm_pipeline import fingerprint

TYPES = ("person", "organization", "location")


def save_gold(records, path=GOLD_PATH):
    """Her değişiklikten sonra atomik yazar (yarım kalan dosya oluşmaz)."""
    temporary = Path(path).with_suffix(".tmp")
    temporary.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
                         encoding="utf-8")
    os.replace(temporary, path)


def parse_entry_line(line):
    """'a; b | c' -> ['a', 'b | c'] (boş parçalar atılır)."""
    entries = []
    for part in line.split(";"):
        aliases = [a.strip() for a in part.split("|") if a.strip()]
        if aliases:
            entries.append(" | ".join(aliases))
    return entries


def missing_from_text(entries, text):
    """Normalize edilmiş metinde hiçbir eş adı geçmeyen girdileri döndürür (uyarı amaçlı)."""
    haystack = f" {normalize_entity(text)} "
    return [e for e in entries
            if not any(f" {normalize_entity(a)} " in haystack for a in e.split("|"))]


def review(record, sample, reviewer, ask=input):
    """Bir kaydı gösterir, düzeltmeleri alır; doğrulanırsa True döndürür."""
    print("\n" + "=" * 100)
    print(f"ID {record['id']}  |  reference category: {sample['true_category']}  |  "
          f"status: {record['status']}  |  source: {record.get('candidate_source')}")
    print("-" * 100)
    print(textwrap.fill(sample["text"], width=100))
    print("-" * 100)
    updated = dict(record)
    for entity_type in TYPES:
        current = updated.get(entity_type, [])
        print(f"{entity_type:>12}: {'; '.join(current) if current else '[]'}")
        answer = ask(f"{'':>12}  Enter=keep, '-'=empty, or new list: ").strip()
        if answer == "-":
            updated[entity_type] = []
        elif answer:
            updated[entity_type] = parse_entry_line(answer)
    for entity_type in TYPES:
        missing = missing_from_text(updated[entity_type], sample["text"])
        print(f"{entity_type:>12}: {updated[entity_type]}"
              + (f"   WARNING not found in text: {missing}" if missing else ""))
    note = ask("Optional note (Enter to keep): ").strip()
    if note:
        updated["notes"] = note
    if ask("Mark this record as human-verified? [y/N]: ").strip().lower() != "y":
        return None
    updated.update(status="verified", reviewer=reviewer,
                   text_sha256=fingerprint(sample["text"]),
                   reviewed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    validate_gold_record(updated)
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", action="store_true", help="show review progress only")
    parser.add_argument("--id", type=int, help="review this sample ID")
    parser.add_argument("--reviewer", help="name of the human reviewer (required to verify)")
    args = parser.parse_args()

    samples = {s["id"]: s for s in load_samples("selected")}
    ids = list(samples)
    gold = load_gold()
    records = [gold.get(i, {"id": i, "person": [], "organization": [], "location": [],
                            "status": "candidate", "candidate_source": "none (empty)",
                            "reviewer": None, "reviewed_at": None, "notes": ""}) for i in ids]
    status = gold_status(ids, {r["id"]: r for r in records})
    print(f"Verified {status['verified']}/{status['selected']} records "
          f"({'complete' if status['complete'] else 'entity F1 is PENDING HUMAN REVIEW'})")
    if args.status:
        return
    if not args.reviewer or not args.reviewer.strip():
        parser.error("--reviewer is required to verify records")
    queue = [args.id] if args.id is not None else [r["id"] for r in records
                                                    if r["status"] != "verified"]
    if args.id is not None and args.id not in samples:
        parser.error(f"ID {args.id} is not in data/evaluation_ids.json")
    for sample_id in queue:
        index = ids.index(sample_id)
        try:
            updated = review(records[index], samples[sample_id], args.reviewer)
        except (KeyboardInterrupt, EOFError):
            print("\nStopped. Progress so far is saved.")
            return
        except ValueError as error:
            print(f"Not saved: {error}. Review again with --id {sample_id}.")
            continue
        if updated is not None:
            records[index] = updated
            save_gold(records)
            done = sum(r["status"] == "verified" for r in records)
            print(f"Saved. Verified {done}/{len(records)}.")
        else:
            print("Not verified; record unchanged.")


if __name__ == "__main__":
    main()
