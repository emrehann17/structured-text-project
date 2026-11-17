"""Varlık gold etiketleri için insan inceleme aracı (tarayıcı veya terminal tabanlı).

    python src/annotate_entities.py --web                    # hızlı yerel tarayıcı arayüzünü başlat
    python src/annotate_entities.py --prepare-candidates     # 100 aday kaydı iyileştirilmiş önerilerle güncelle
    python src/annotate_entities.py --status                 # ilerleme durumunu göster
    python src/annotate_entities.py --reviewer "Ad Soyad"    # terminalde sıradaki doğrulanmamış kaydı incele
    python src/annotate_entities.py --reviewer "Ad Soyad" --id 4000  # belirli kaydı incele

Hiçbir kayıt otomatik olarak 'verified' yapılmaz. Yalnızca gerçek bir insan inceleyicinin açık onayı
(Accept & Verify veya terminalde 'y') kaydı 'verified' durumuna geçirir.
Kurallar: docs/ANNOTATION_GUIDELINES.md
"""

import argparse
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import textwrap
from urllib.parse import urlparse
import webbrowser

from evaluate import (
    GOLD_PATH,
    RESULT_PATH,
    ROOT,
    RUNS,
    gold_status,
    load_gold,
    load_jsonl,
    load_samples,
    normalize_entity,
    validate_gold_record,
)
from llm_pipeline import MODEL, OLLAMA_URL, OPTIONS, evaluate_response, fingerprint
import requests
from second_pass_candidates import SECOND_PASS_CANDIDATES

TYPES = ("person", "organization", "location")
CANDIDATE_SOURCE = (
    "Second-pass audited candidate (cross-checked against 5 saved Qwen2.5:3b runs "
    "and annotation guidelines); unverified, requires explicit human review"
)


def save_gold(records, path=GOLD_PATH):
    """Her değişiklikten sonra atomik yazar (yarım kalan dosya oluşmaz)."""
    temporary = Path(path).with_suffix(".tmp")
    temporary.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def parse_entry_line(line):
    """'a; b | c' -> ['a', 'b | c'] (boş parçalar atılır)."""
    if isinstance(line, list):
        line = "; ".join(str(x) for x in line)
    entries = []
    for part in str(line).split(";"):
        aliases = [a.strip() for a in part.split("|") if a.strip()]
        if aliases:
            entries.append(" | ".join(aliases))
    return entries


def deduplicate_entries(entries):
    """Aynı normalize eş ad kümesine sahip yinelenen girdileri koruyarak teke indirir."""
    cleaned = []
    seen = set()
    for entry in entries:
        aliases = [a.strip() for a in entry.split("|") if a.strip()]
        if not aliases:
            continue
        key = frozenset(normalize_entity(a) for a in aliases if normalize_entity(a))
        if key and key not in seen:
            seen.add(key)
            cleaned.append(" | ".join(aliases))
    return cleaned


def missing_from_text(entries, text):
    """Normalize edilmiş metinde hiçbir eş adı geçmeyen girdileri döndürür (uyarı amaçlı)."""
    haystack = f" {normalize_entity(text)} "
    return [
        e for e in entries
        if not any(
            f" {normalize_entity(a)} " in haystack or f" {normalize_entity(a)}" in haystack
            for a in e.split("|") if a.strip()
        )
    ]


def collect_existing_predictions(samples, root=ROOT):
    """Kayıtlı 5 Qwen çalışmasından (tarihsel + 4 kontrollü çalışma) varlık tahminlerini toplar."""
    by_id = {s["id"]: {} for s in samples}
    hist_path = root / "results/optimized_schema_results.jsonl"
    if hist_path.exists():
        for row in load_jsonl(hist_path):
            if row["id"] in by_id and isinstance(row.get("raw_output"), str):
                flags = evaluate_response(row["raw_output"], row.get("true_category"))
                by_id[row["id"]]["historical_v1"] = flags["entities"] or {t: [] for t in TYPES}
    for run_name, (rel_path, _, _) in RUNS.items():
        run_path = root / rel_path
        if run_path.exists():
            for row in load_jsonl(run_path):
                if row["id"] in by_id:
                    ents = row.get("entities")
                    if ents is None and isinstance(row.get("raw_output"), str):
                        ents = evaluate_response(row["raw_output"], row.get("true_category"))["entities"]
                    by_id[row["id"]][run_name] = ents or {t: [] for t in TYPES}
    return by_id


def analyze_candidate_discrepancies(sample, candidate, run_predictions):
    """Model tahminleri ile önerilen aday listeyi karşılaştırır; olası hataları, tip uyuşmazlıklarını
    ve kaçırılan varlıkları tespit eder."""
    cand_alias_to_type = {}
    for kind in TYPES:
        for entry in candidate.get(kind, []):
            for alias in entry.split("|"):
                norm = normalize_entity(alias)
                if norm:
                    cand_alias_to_type[norm] = (kind, entry)

    hist = run_predictions.get("historical_v1") or {t: [] for t in TYPES}
    type_mismatches = []
    unsupported_or_removed = []
    matched_entries = set()

    for pred_type in TYPES:
        for raw_name in hist.get(pred_type, []):
            norm = normalize_entity(raw_name)
            if not norm:
                continue
            if norm in cand_alias_to_type:
                true_type, entry = cand_alias_to_type[norm]
                matched_entries.add((true_type, entry))
                if true_type != pred_type:
                    type_mismatches.append({
                        "entity": raw_name,
                        "predicted_type": pred_type,
                        "suggested_type": true_type,
                    })
            else:
                unsupported_or_removed.append({
                    "entity": raw_name,
                    "predicted_type": pred_type,
                })

    missing_in_historical = []
    for kind in TYPES:
        for entry in candidate.get(kind, []):
            if (kind, entry) not in matched_entries:
                missing_in_historical.append({"type": kind, "entity": entry})

    run_sets = []
    for preds in run_predictions.values():
        run_sets.append(tuple(
            (k, tuple(sorted({normalize_entity(x) for x in preds.get(k, []) if normalize_entity(x)})))
            for k in TYPES
        ))
    cross_run_conflict = len(set(run_sets)) > 1

    not_in_text = {}
    for kind in TYPES:
        miss = missing_from_text(candidate.get(kind, []), sample["text"])
        if miss:
            not_in_text[kind] = miss

    curated_flags = list(candidate.get("flags", []))
    has_ambiguity = any("ambiguity" in f.lower() or "capped" in f.lower() for f in curated_flags)

    return {
        "type_mismatches": type_mismatches,
        "removed_predictions": unsupported_or_removed,
        "added_missing_entities": missing_in_historical,
        "cross_run_conflict": cross_run_conflict,
        "not_in_text": not_in_text,
        "flags": curated_flags,
        "needs_closer_review": bool(type_mismatches or has_ambiguity or not_in_text),
    }


SECOND_PASS_REVIEW_PROMPT = """Türkçe haber metnini ve mevcut varlık (entity) adaylarını denetleyen ikinci geçiş (second-pass) inceleme sistemisin.
Kurallar:
- person: Gerçek kişi isimleri (unvanları çıkar).
- organization: Şirket, kurum, parti, spor kulübü, üniversite, ajans (ürün ve etkinlikler hariç).
- location: Ülke, şehir, bölge ve mekan olarak kullanılan yerler.
- Metinde geçmeyen hiçbir ismi ekleme. Her tipte metindeki ilk geçiş sırasına göre EN FAZLA 5 varlık tut.
- Aynı varlığın metindeki eş adlarını 'tam ad | kısa ad' biçiminde birleştir.
Yalnızca şu JSON yapısını döndür:
{"person": [], "organization": [], "location": [], "flags": []}
"""


def run_live_llm_second_pass(sample, existing_predictions):
    """İsteğe bağlı: Yerel Ollama sunucusu açıksa canlı ikinci geçiş LLM denetimi yapar."""
    prompt = (
        f"{SECOND_PASS_REVIEW_PROMPT}\n"
        f"MEVCUT TAHMİNLER:\n{json.dumps(existing_predictions, ensure_ascii=False)}\n\n"
        f"HABER METNİ:\n{sample['text']}\n"
    )
    schema = {
        "type": "object",
        "properties": {
            "person": {"type": "array", "items": {"type": "string"}},
            "organization": {"type": "array", "items": {"type": "string"}},
            "location": {"type": "array", "items": {"type": "string"}},
            "flags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["person", "organization", "location", "flags"],
        "additionalProperties": False,
    }
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False, "format": schema, "options": dict(OPTIONS)},
        timeout=(5, 60),
    )
    response.raise_for_status()
    parsed = json.loads(response.json()["response"])
    return {
        "person": deduplicate_entries(parse_entry_line(parsed.get("person", [])))[:5],
        "organization": deduplicate_entries(parse_entry_line(parsed.get("organization", [])))[:5],
        "location": deduplicate_entries(parse_entry_line(parsed.get("location", [])))[:5],
        "flags": [str(f) for f in parsed.get("flags", [])],
    }


def prepare_candidates(path=GOLD_PATH, live_llm=False):
    """100 seçili kayıt için iyileştirilmiş adayları ve denetim bayraklarını üretir.
    Daha önce insan tarafından 'verified' yapılmış kayıtlar varsa ASLA üzerine yazmaz."""
    samples = load_samples("selected")
    existing_gold = load_gold(path) if Path(path).exists() else {}
    run_preds = collect_existing_predictions(samples)
    results_sha = fingerprint(RESULT_PATH.read_text(encoding="utf-8")) if RESULT_PATH.exists() else None

    records = []
    for sample in samples:
        sid = sample["id"]
        current = existing_gold.get(sid)
        if current and current.get("status") == "verified":
            validate_gold_record(current)
            records.append(current)
            continue

        if live_llm:
            try:
                cand = run_live_llm_second_pass(sample, run_preds.get(sid, {}))
            except Exception:
                cand = SECOND_PASS_CANDIDATES[sid]
        else:
            cand = SECOND_PASS_CANDIDATES[sid]

        audit_info = analyze_candidate_discrepancies(sample, cand, run_preds.get(sid, {}))
        notes_list = audit_info["flags"]
        notes_str = " ".join(notes_list) if notes_list else (
            "Review all source entities, not only suggestions; retain first five distinct entities per type."
        )

        record = {
            "id": sid,
            "status": "candidate",
            "candidate_source": CANDIDATE_SOURCE,
            "candidate_results_sha256": (current or {}).get("candidate_results_sha256") or results_sha,
            "reviewer": None,
            "reviewed_at": None,
            "text_sha256": fingerprint(sample["text"]),
            "notes": notes_str,
            "location": list(cand["location"]),
            "organization": list(cand["organization"]),
            "person": list(cand["person"]),
            "review_flags": audit_info,
        }
        validate_gold_record(record)
        records.append(record)

    save_gold(records, path)
    return records


def apply_record_update(record, sample, payload):
    """Web veya API üzerinden gelen düzenleme/doğrulama işlemini tek kayda uygular."""
    action = payload.get("action", "save_draft")
    if action not in ("save_draft", "verify", "unverify"):
        raise ValueError(f"Unknown action: {action}")

    updated = dict(record)
    for kind in TYPES:
        if kind in payload:
            raw_val = payload[kind]
            entries = parse_entry_line(raw_val)
            updated[kind] = deduplicate_entries(entries)

    if "notes" in payload and payload["notes"] is not None:
        updated["notes"] = str(payload["notes"]).strip()

    if "review_flags" in updated:
        not_in_text = {}
        for kind in TYPES:
            miss = missing_from_text(updated.get(kind, []), sample["text"])
            if miss:
                not_in_text[kind] = miss
        rf = dict(updated["review_flags"])
        rf["not_in_text"] = not_in_text
        updated["review_flags"] = rf

    if action == "verify":
        reviewer = str(payload.get("reviewer") or "").strip()
        if not reviewer:
            raise ValueError("Reviewer name is required to mark a record as human-verified.")
        updated.update(
            status="verified",
            reviewer=reviewer,
            text_sha256=fingerprint(sample["text"]),
            reviewed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
    elif action == "unverify":
        updated.update(
            status="candidate",
            reviewer=None,
            reviewed_at=None,
            text_sha256=fingerprint(sample["text"]),
        )
    else:
        updated["text_sha256"] = fingerprint(sample["text"])
        if updated.get("status") != "verified":
            updated["status"] = "candidate"
            updated["reviewer"] = None
            updated["reviewed_at"] = None

    validate_gold_record(updated)
    return updated


def review(record, sample, reviewer, ask=input):
    """Bir kaydı terminalde gösterir, düzeltmeleri alır; doğrulanırsa güncellenmiş kaydı döndürür."""
    print("\n" + "=" * 100)
    print(f"ID {record['id']}  |  reference category: {sample['true_category']}  |  "
          f"status: {record['status']}  |  source: {record.get('candidate_source')}")
    print("-" * 100)
    print(textwrap.fill(sample["text"], width=100))
    print("-" * 100)
    flags = (record.get("review_flags") or {}).get("flags") or []
    if flags:
        print("Review flags:")
        for flag in flags:
            print(f"  * {flag}")
        print("-" * 100)
    updated = dict(record)
    for entity_type in TYPES:
        current = updated.get(entity_type, [])
        print(f"{entity_type:>12}: {'; '.join(current) if current else '[]'}")
        answer = ask(f"{'':>12}  Enter=keep, '-'=empty, or new list: ").strip()
        if answer == "-":
            updated[entity_type] = []
        elif answer:
            updated[entity_type] = deduplicate_entries(parse_entry_line(answer))
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


WEB_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Entity Gold Review — 100 Articles</title>
<style>
  :root {
    --bg: #f8fafc; --panel: #ffffff; --border: #e2e8f0; --text: #0f172a; --muted: #64748b;
    --person-bg: #dbeafe; --person-fg: #1e40af; --person-bd: #93c5fd;
    --org-bg: #fef3c7; --org-fg: #92400e; --org-bd: #fcd34d;
    --loc-bg: #dcfce7; --loc-fg: #166534; --loc-bd: #86efac;
    --accent: #2563eb; --ok: #16a34a; --warn: #d97706; --danger: #dc2626;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); }
  header {
    background: var(--panel); border-bottom: 1px solid var(--border); padding: 10px 18px;
    display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap;
    position: sticky; top: 0; z-index: 20;
  }
  .brand { font-weight: 700; font-size: 16px; display: flex; align-items: center; gap: 10px; }
  .progress-pill {
    padding: 4px 10px; border-radius: 999px; font-weight: 600; font-size: 13px;
    background: #eff6ff; color: var(--accent); border: 1px solid #bfdbfe;
  }
  .progress-pill.done { background: #dcfce7; color: var(--ok); border-color: #86efac; }
  .controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  input[type="text"], select, textarea {
    padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;
    font-family: inherit; background: #fff; color: var(--text);
  }
  button {
    padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border); background: #fff;
    cursor: pointer; font-size: 13px; font-weight: 600; color: var(--text); transition: 0.12s;
  }
  button:hover { background: #f1f5f9; }
  button.primary { background: var(--ok); color: #fff; border-color: var(--ok); }
  button.primary:hover { background: #15803d; }
  button.accent { background: var(--accent); color: #fff; border-color: var(--accent); }
  button.accent:hover { background: #1d4ed8; }
  button.danger { color: var(--danger); border-color: #fecaca; }
  .layout {
    display: grid; grid-template-columns: 1.15fr 1fr; gap: 16px; padding: 16px; max-width: 1560px; margin: 0 auto;
  }
  @media (max-width: 1024px) { .layout { grid-template-columns: 1fr; } }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }
  .meta-bar {
    display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap;
    padding-bottom: 10px; margin-bottom: 12px; border-bottom: 1px solid var(--border);
  }
  .badge {
    display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;
  }
  .badge.candidate { background: #fef3c7; color: #92400e; }
  .badge.verified { background: #dcfce7; color: #166534; }
  .badge.flagged { background: #fee2e2; color: #991b1b; }
  .badge.cat { background: #f1f5f9; color: #334155; }
  .article-text {
    line-height: 1.78; font-size: 15.5px; white-space: pre-wrap; word-break: break-word;
    padding: 12px; background: #fcfcfd; border: 1px solid var(--border); border-radius: 8px;
    max-height: 62vh; overflow-y: auto;
  }
  mark.hl-person { background: var(--person-bg); color: var(--person-fg); padding: 1px 4px; border-radius: 4px; border-bottom: 2px solid var(--person-bd); }
  mark.hl-organization { background: var(--org-bg); color: var(--org-fg); padding: 1px 4px; border-radius: 4px; border-bottom: 2px solid var(--org-bd); }
  mark.hl-location { background: var(--loc-bg); color: var(--loc-fg); padding: 1px 4px; border-radius: 4px; border-bottom: 2px solid var(--loc-bd); }
  .legend { display: flex; gap: 12px; font-size: 12px; margin-bottom: 8px; color: var(--muted); align-items: center; }
  .flag-box {
    margin-top: 12px; padding: 10px 12px; border-radius: 8px; background: #fffbeb;
    border: 1px solid #fde68a; font-size: 13px;
  }
  .flag-box h4 { margin: 0 0 6px 0; font-size: 13px; color: #92400e; }
  .flag-box ul { margin: 0; padding-left: 18px; }
  .flag-box li { margin-bottom: 3px; }
  .type-section {
    border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; margin-bottom: 10px;
  }
  .type-section.person { border-left: 4px solid var(--person-fg); }
  .type-section.organization { border-left: 4px solid var(--org-fg); }
  .type-section.location { border-left: 4px solid var(--loc-fg); }
  .type-header {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
    font-weight: 700; font-size: 13.5px; text-transform: uppercase; letter-spacing: 0.4px;
  }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; min-height: 28px; }
  .chip {
    display: inline-flex; align-items: center; gap: 5px; padding: 4px 8px; border-radius: 6px;
    font-size: 13px; font-weight: 500; border: 1px solid var(--border); background: #f8fafc;
  }
  .chip.person { background: var(--person-bg); color: var(--person-fg); border-color: var(--person-bd); }
  .chip.organization { background: var(--org-bg); color: var(--org-fg); border-color: var(--org-bd); }
  .chip.location { background: var(--loc-bg); color: var(--loc-fg); border-color: var(--loc-bd); }
  .chip.missing { border: 2px dashed var(--danger); }
  .chip button {
    padding: 1px 5px; font-size: 11px; border-radius: 4px; background: rgba(255,255,255,0.75);
    border: 1px solid rgba(0,0,0,0.12);
  }
  .add-row { display: flex; gap: 6px; }
  .add-row input { flex: 1; }
  .action-bar {
    display: flex; gap: 8px; flex-wrap: wrap; align-items: center; justify-content: space-between;
    margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border);
  }
  .toast {
    font-size: 13px; font-weight: 600; color: var(--ok); min-height: 20px;
  }
  .toast.err { color: var(--danger); }
  .runs-box {
    margin-top: 12px; font-size: 12px; color: var(--muted); border-top: 1px solid var(--border); padding-top: 8px;
  }
  .kbd {
    background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; padding: 1px 5px;
    font-family: monospace; font-size: 11px;
  }
</style>
</head>
<body>
<header>
  <div class="brand">
    <span>Entity Gold Annotation</span>
    <span id="progressPill" class="progress-pill">0/100 verified</span>
  </div>
  <div class="controls">
    <label style="font-size:13px;font-weight:600;">Reviewer:
      <input type="text" id="reviewerInput" placeholder="Your real name (required)" style="width:180px;">
    </label>
    <label style="font-size:13px;">Filter:
      <select id="filterSelect">
        <option value="all">All 100 articles</option>
        <option value="unverified">Unverified (candidate)</option>
        <option value="flagged">Flagged / Ambiguous</option>
        <option value="verified">Verified</option>
      </select>
    </label>
    <select id="jumpSelect" style="max-width:210px;"></select>
    <button id="prevBtn" title="Shortcut: [ or Left Arrow">&larr; Prev</button>
    <button id="nextBtn" title="Shortcut: ] or Right Arrow">Next &rarr;</button>
    <button id="nextUnverifiedBtn" title="Jump to next unverified record">Next Unverified</button>
  </div>
</header>

<div class="layout">
  <div class="card">
    <div class="meta-bar">
      <div>
        <strong id="articleTitle" style="font-size:16px;">Article #1</strong>
        <span id="catBadge" class="badge cat">category</span>
        <span id="statusBadge" class="badge candidate">candidate</span>
        <span id="flagBadge" class="badge flagged" style="display:none;">needs closer review</span>
      </div>
      <div style="font-size:12px;color:var(--muted);" id="provenanceInfo"></div>
    </div>
    <div class="legend">
      <span>Highlights:</span>
      <span><mark class="hl-person">Person</mark></span>
      <span><mark class="hl-organization">Organization</mark></span>
      <span><mark class="hl-location">Location</mark></span>
      <span style="margin-left:auto;">Select text in article + click <b>+ Sel</b> to add</span>
    </div>
    <div id="articleText" class="article-text"></div>
    <div id="flagBox" class="flag-box" style="display:none;">
      <h4>Second-Pass Audit &amp; Discrepancy Notes</h4>
      <ul id="flagList"></ul>
    </div>
    <div id="runsBox" class="runs-box"></div>
  </div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <strong>Proposed Candidate Entities (max 5 per type, first-mention order)</strong>
      <button id="resetCandidateBtn" title="Restore second-pass audited candidate for this article">Reset to Audited Candidate</button>
    </div>

    <div id="sectionsContainer"></div>

    <div style="margin-top:8px;">
      <label style="font-size:12.5px;font-weight:600;color:var(--muted);">Review Notes:</label>
      <input type="text" id="notesInput" style="width:100%;margin-top:4px;">
    </div>

    <div class="action-bar">
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button class="primary" id="verifyNextBtn" title="Shortcut: Alt+Enter">Accept &amp; Verify &rarr; Next</button>
        <button class="accent" id="verifyStayBtn">Accept &amp; Verify</button>
        <button id="saveDraftBtn">Save Draft (Keep Candidate)</button>
        <button class="danger" id="unverifyBtn" style="display:none;">Reopen (Unverify)</button>
      </div>
      <div id="toast" class="toast"></div>
    </div>
    <div style="margin-top:10px;font-size:12px;color:var(--muted);">
      Shortcuts: <span class="kbd">Alt+Enter</span> Accept &amp; Verify + Next &nbsp;|&nbsp;
      <span class="kbd">[</span> / <span class="kbd">]</span> Prev / Next article &nbsp;|&nbsp;
      Use <code>full name | alias</code> to group aliases of one entity; <code>;</code> separates multiple entities.
      No bulk-approve exists: each article requires explicit inspection and confirmation.
    </div>
  </div>
</div>

<script>
const TYPES = ["person", "organization", "location"];
const OTHER_TYPES = {
  person: [["organization", "→Org"], ["location", "→Loc"]],
  organization: [["person", "→Per"], ["location", "→Loc"]],
  location: [["person", "→Per"], ["organization", "→Org"]]
};

let state = { items: [], progress: {verified: 0, selected: 100} };
let filteredIndices = [];
let currentPos = 0;
let working = { person: [], organization: [], location: [], notes: "" };

function normalizeTr(s) {
  return (s || "").normalize("NFC")
    .replace(/İ/g, "i").replace(/I/g, "ı")
    .toLowerCase().replace(/_/g, " ")
    .trim().replace(/\s+/g, " ");
}

function aliasInText(entry, text) {
  const hay = " " + normalizeTr(text) + " ";
  return entry.split("|").some(a => {
    const na = normalizeTr(a);
    return na && (hay.includes(" " + na + " ") || hay.includes(" " + na));
  });
}

function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function highlightArticle(text, entitiesByType) {
  const phrases = [];
  for (const kind of TYPES) {
    for (const entry of (entitiesByType[kind] || [])) {
      for (const rawAlias of entry.split("|")) {
        const clean = rawAlias.trim();
        if (clean.length >= 2) {
          phrases.push({ alias: clean, norm: normalizeTr(clean), kind });
          const underscored = clean.replace(/\s+/g, "_");
          if (underscored !== clean) {
            phrases.push({ alias: underscored, norm: normalizeTr(clean), kind });
          }
        }
      }
    }
  }
  phrases.sort((a, b) => b.alias.length - a.alias.length);
  if (!phrases.length) return escapeHtml(text);

  const lowerText = text.replace(/İ/g, "i").replace(/I/g, "ı").toLowerCase();
  const intervals = [];
  for (const p of phrases) {
    const needle = p.alias.replace(/İ/g, "i").replace(/I/g, "ı").toLowerCase();
    if (!needle) continue;
    let start = 0;
    while (start < lowerText.length) {
      const idx = lowerText.indexOf(needle, start);
      if (idx === -1) break;
      const before = idx === 0 ? " " : lowerText[idx - 1];
      const afterIdx = idx + needle.length;
      const after = afterIdx >= lowerText.length ? " " : lowerText[afterIdx];
      const boundaryBefore = /[\s"'“”‘’([/_-]/.test(before);
      if (boundaryBefore) {
        const end = afterIdx;
        if (!intervals.some(iv => !(end <= iv.start || idx >= iv.end))) {
          intervals.push({ start: idx, end, kind: p.kind });
        }
      }
      start = idx + 1;
    }
  }
  intervals.sort((a, b) => a.start - b.start);
  let out = "";
  let pos = 0;
  for (const iv of intervals) {
    out += escapeHtml(text.slice(pos, iv.start));
    out += `<mark class="hl-${iv.kind}">${escapeHtml(text.slice(iv.start, iv.end))}</mark>`;
    pos = iv.end;
  }
  out += escapeHtml(text.slice(pos));
  return out;
}

async function fetchState(preserveId = null) {
  const res = await fetch("/api/state");
  state = await res.json();
  const savedRev = localStorage.getItem("entity_gold_reviewer");
  if (savedRev && !document.getElementById("reviewerInput").value) {
    document.getElementById("reviewerInput").value = savedRev;
  }
  applyFilter(preserveId);
}

function isFlagged(item) {
  const rf = item.record.review_flags || {};
  return Boolean(rf.needs_closer_review || (rf.flags && rf.flags.length));
}

function applyFilter(preserveId = null) {
  const mode = document.getElementById("filterSelect").value;
  filteredIndices = [];
  state.items.forEach((item, idx) => {
    if (mode === "unverified" && item.record.status === "verified") return;
    if (mode === "verified" && item.record.status !== "verified") return;
    if (mode === "flagged" && !isFlagged(item)) return;
    filteredIndices.push(idx);
  });
  if (!filteredIndices.length) {
    filteredIndices = state.items.map((_, i) => i);
  }
  if (preserveId !== null) {
    const foundPos = filteredIndices.findIndex(i => state.items[i].id === preserveId);
    if (foundPos !== -1) currentPos = foundPos;
  }
  if (currentPos >= filteredIndices.length) currentPos = 0;
  renderJumpSelect();
  loadCurrentRecordIntoWorking();
  renderCurrent();
}

function renderJumpSelect() {
  const sel = document.getElementById("jumpSelect");
  sel.innerHTML = "";
  filteredIndices.forEach((itemIdx, pos) => {
    const it = state.items[itemIdx];
    const mark = it.record.status === "verified" ? "✓" : (isFlagged(it) ? "⚠" : "•");
    const opt = document.createElement("option");
    opt.value = pos;
    opt.textContent = `${mark} [${itemIdx + 1}/100] ID ${it.id} (${it.true_category})`;
    if (pos === currentPos) opt.selected = true;
    sel.appendChild(opt);
  });
}

function currentItem() {
  return state.items[filteredIndices[currentPos]];
}

function loadCurrentRecordIntoWorking() {
  const item = currentItem();
  if (!item) return;
  for (const k of TYPES) {
    working[k] = [...(item.record[k] || [])];
  }
  working.notes = item.record.notes || "";
}

function renderCurrent() {
  const pill = document.getElementById("progressPill");
  pill.textContent = `${state.progress.verified}/${state.progress.selected} verified`;
  pill.className = "progress-pill" + (state.progress.complete ? " done" : "");

  const item = currentItem();
  if (!item) return;
  const globalIdx = filteredIndices[currentPos];
  document.getElementById("jumpSelect").value = currentPos;
  document.getElementById("articleTitle").textContent = `Article ${globalIdx + 1}/100 — ID ${item.id}`;
  document.getElementById("catBadge").textContent = item.true_category;

  const sb = document.getElementById("statusBadge");
  sb.textContent = item.record.status;
  sb.className = "badge " + item.record.status;

  const fb = document.getElementById("flagBadge");
  fb.style.display = isFlagged(item) ? "inline-block" : "none";

  const prov = document.getElementById("provenanceInfo");
  if (item.record.status === "verified") {
    prov.textContent = `Verified by ${item.record.reviewer} at ${item.record.reviewed_at}`;
    document.getElementById("unverifyBtn").style.display = "inline-block";
  } else {
    prov.textContent = "Status: unverified candidate";
    document.getElementById("unverifyBtn").style.display = "none";
  }

  document.getElementById("articleText").innerHTML = highlightArticle(item.text, working);
  document.getElementById("notesInput").value = working.notes;

  const rf = item.record.review_flags || {};
  const flagBox = document.getElementById("flagBox");
  const flagList = document.getElementById("flagList");
  flagList.innerHTML = "";
  const notes = [...(rf.flags || [])];
  if (rf.cross_run_conflict) {
    notes.push("Predictions differ across the 5 saved Qwen runs; verify against source text.");
  }
  if (notes.length) {
    flagBox.style.display = "block";
    notes.forEach(n => {
      const li = document.createElement("li");
      li.textContent = n;
      flagList.appendChild(li);
    });
  } else {
    flagBox.style.display = "none";
  }

  const hist = (item.run_predictions && item.run_predictions.historical_v1) || {person:[], organization:[], location:[]};
  document.getElementById("runsBox").innerHTML =
    `<b>Original historical Qwen candidate:</b> P=${JSON.stringify(hist.person)} | O=${JSON.stringify(hist.organization)} | L=${JSON.stringify(hist.location)}`;

  renderSections(item.text);
}

function renderSections(text) {
  const container = document.getElementById("sectionsContainer");
  container.innerHTML = "";
  for (const kind of TYPES) {
    const list = working[kind] || [];
    const sec = document.createElement("div");
    sec.className = `type-section ${kind}`;

    const header = document.createElement("div");
    header.className = "type-header";
    header.innerHTML = `<span>${kind} (${list.length}/5)</span>`;
    const clearBtn = document.createElement("button");
    clearBtn.textContent = "Clear";
    clearBtn.onclick = () => { working[kind] = []; renderCurrent(); };
    header.appendChild(clearBtn);
    sec.appendChild(header);

    const chips = document.createElement("div");
    chips.className = "chips";
    list.forEach((entry, idx) => {
      const inTxt = aliasInText(entry, text);
      const chip = document.createElement("span");
      chip.className = `chip ${kind}` + (inTxt ? "" : " missing");
      chip.title = inTxt ? "Click Edit to modify" : "Warning: no alias found in article text";
      const label = document.createElement("span");
      label.textContent = entry + (inTxt ? "" : " ⚠");
      chip.appendChild(label);

      const editBtn = document.createElement("button");
      editBtn.textContent = "Edit";
      editBtn.onclick = () => {
        const next = prompt(`Edit ${kind} entry (use | for aliases):`, entry);
        if (next !== null) {
          const trimmed = next.trim();
          if (trimmed) working[kind][idx] = trimmed;
          else working[kind].splice(idx, 1);
          renderCurrent();
        }
      };
      chip.appendChild(editBtn);

      for (const [targetType, btnLabel] of OTHER_TYPES[kind]) {
        const mvBtn = document.createElement("button");
        mvBtn.textContent = btnLabel;
        mvBtn.title = `Move to ${targetType}`;
        mvBtn.onclick = () => {
          if (working[targetType].length >= 5) {
            showToast(`Cannot move: ${targetType} already has 5 entities.`, true);
            return;
          }
          working[kind].splice(idx, 1);
          working[targetType].push(entry);
          renderCurrent();
        };
        chip.appendChild(mvBtn);
      }

      const delBtn = document.createElement("button");
      delBtn.textContent = "×";
      delBtn.title = "Remove entity";
      delBtn.onclick = () => { working[kind].splice(idx, 1); renderCurrent(); };
      chip.appendChild(delBtn);

      chips.appendChild(chip);
    });
    sec.appendChild(chips);

    const addRow = document.createElement("div");
    addRow.className = "add-row";
    const inp = document.createElement("input");
    inp.type = "text";
    inp.placeholder = `Add ${kind} (use ';' for multiple, '|' for aliases)...`;
    inp.onkeydown = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addEntries(kind, inp.value);
        inp.value = "";
      }
    };
    const addBtn = document.createElement("button");
    addBtn.textContent = "+ Add";
    addBtn.onclick = () => { addEntries(kind, inp.value); inp.value = ""; };

    const selBtn = document.createElement("button");
    selBtn.textContent = "+ Sel";
    selBtn.title = "Add currently selected article text";
    selBtn.onclick = () => {
      const sel = window.getSelection().toString().trim();
      if (sel) addEntries(kind, sel);
    };

    addRow.appendChild(inp);
    addRow.appendChild(addBtn);
    addRow.appendChild(selBtn);
    sec.appendChild(addRow);
    container.appendChild(sec);
  }
}

function addEntries(kind, raw) {
  if (!raw || !raw.trim()) return;
  for (const part of raw.split(";")) {
    const aliases = part.split("|").map(x => x.trim()).filter(Boolean);
    if (!aliases.length) continue;
    if (working[kind].length >= 5) {
      showToast(`Maximum 5 distinct entities allowed for ${kind}.`, true);
      break;
    }
    working[kind].push(aliases.join(" | "));
  }
  renderCurrent();
}

function showToast(msg, isErr = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast" + (isErr ? " err" : "");
}

async function submitAction(action, advanceNext = false) {
  const item = currentItem();
  if (!item) return;
  const reviewer = document.getElementById("reviewerInput").value.trim();
  if (reviewer) localStorage.setItem("entity_gold_reviewer", reviewer);
  if (action === "verify" && !reviewer) {
    showToast("Please enter your real name in the Reviewer field before verifying.", true);
    document.getElementById("reviewerInput").focus();
    return;
  }
  working.notes = document.getElementById("notesInput").value.trim();
  const res = await fetch("/api/update", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: item.id,
      action,
      reviewer,
      person: working.person,
      organization: working.organization,
      location: working.location,
      notes: working.notes
    })
  });
  const data = await res.json();
  if (!res.ok) {
    showToast(data.error || "Save failed", true);
    return;
  }
  const savedId = item.id;
  state.progress = data.progress;
  const globalIdx = state.items.findIndex(x => x.id === savedId);
  if (globalIdx !== -1) state.items[globalIdx].record = data.record;

  showToast(action === "verify" ? `Verified ID ${savedId} (${state.progress.verified}/100)` : `Saved ID ${savedId}`);
  if (advanceNext && currentPos + 1 < filteredIndices.length) {
    currentPos += 1;
  }
  renderJumpSelect();
  loadCurrentRecordIntoWorking();
  renderCurrent();
}

document.getElementById("prevBtn").onclick = () => {
  if (currentPos > 0) { currentPos -= 1; loadCurrentRecordIntoWorking(); renderCurrent(); showToast(""); }
};
document.getElementById("nextBtn").onclick = () => {
  if (currentPos + 1 < filteredIndices.length) { currentPos += 1; loadCurrentRecordIntoWorking(); renderCurrent(); showToast(""); }
};
document.getElementById("nextUnverifiedBtn").onclick = () => {
  const idx = filteredIndices.findIndex((gIdx, pos) => pos > currentPos && state.items[gIdx].record.status !== "verified");
  const fallback = filteredIndices.findIndex(gIdx => state.items[gIdx].record.status !== "verified");
  const target = idx !== -1 ? idx : fallback;
  if (target !== -1) { currentPos = target; loadCurrentRecordIntoWorking(); renderCurrent(); showToast(""); }
  else showToast("All records in current filter are verified!");
};
document.getElementById("filterSelect").onchange = () => applyFilter(currentItem() ? currentItem().id : null);
document.getElementById("jumpSelect").onchange = (e) => {
  currentPos = parseInt(e.target.value, 10) || 0;
  loadCurrentRecordIntoWorking();
  renderCurrent();
  showToast("");
};
document.getElementById("resetCandidateBtn").onclick = () => {
  const item = currentItem();
  if (!item || !item.audited_candidate) return;
  for (const k of TYPES) working[k] = [...(item.audited_candidate[k] || [])];
  renderCurrent();
  showToast("Reset to second-pass audited candidate (not yet saved).");
};
document.getElementById("verifyNextBtn").onclick = () => submitAction("verify", true);
document.getElementById("verifyStayBtn").onclick = () => submitAction("verify", false);
document.getElementById("saveDraftBtn").onclick = () => submitAction("save_draft", false);
document.getElementById("unverifyBtn").onclick = () => submitAction("unverify", false);

document.addEventListener("keydown", (e) => {
  if (e.altKey && e.key === "Enter") {
    e.preventDefault();
    submitAction("verify", true);
  } else if (e.target.tagName !== "INPUT" && e.target.tagName !== "TEXTAREA" && e.target.tagName !== "SELECT") {
    if (e.key === "[" || e.key === "ArrowLeft") {
      e.preventDefault();
      document.getElementById("prevBtn").click();
    } else if (e.key === "]" || e.key === "ArrowRight") {
      e.preventDefault();
      document.getElementById("nextBtn").click();
    }
  }
});

fetchState();
</script>
</body>
</html>
"""


class AnnotationWebApp:
    """100 makalenin durumunu yöneten ve her kayıtta atomik olarak diske yazan yerel uygulama."""

    def __init__(self, gold_path=GOLD_PATH):
        self.gold_path = Path(gold_path)
        self.samples = load_samples("selected")
        self.samples_by_id = {s["id"]: s for s in self.samples}
        self.ids = [s["id"] for s in self.samples]
        self.run_predictions = collect_existing_predictions(self.samples)
        if not self.gold_path.exists():
            prepare_candidates(self.gold_path)
        gold_map = load_gold(self.gold_path)
        self.records = []
        for sid in self.ids:
            rec = gold_map.get(sid)
            if rec is None:
                cand = SECOND_PASS_CANDIDATES[sid]
                rec = {
                    "id": sid,
                    "status": "candidate",
                    "candidate_source": CANDIDATE_SOURCE,
                    "reviewer": None,
                    "reviewed_at": None,
                    "text_sha256": fingerprint(self.samples_by_id[sid]["text"]),
                    "notes": " ".join(cand.get("flags", [])),
                    "person": list(cand["person"]),
                    "organization": list(cand["organization"]),
                    "location": list(cand["location"]),
                }
            if "review_flags" not in rec:
                rec = dict(rec)
                rec["review_flags"] = analyze_candidate_discrepancies(
                    self.samples_by_id[sid],
                    SECOND_PASS_CANDIDATES.get(sid, rec),
                    self.run_predictions.get(sid, {}),
                )
            self.records.append(rec)

    def get_state(self):
        gold_map = {r["id"]: r for r in self.records}
        items = []
        for s in self.samples:
            sid = s["id"]
            items.append({
                "id": sid,
                "true_category": s["true_category"],
                "text": s["text"],
                "record": gold_map[sid],
                "audited_candidate": SECOND_PASS_CANDIDATES.get(sid),
                "run_predictions": self.run_predictions.get(sid, {}),
            })
        return {
            "progress": gold_status(self.ids, gold_map),
            "items": items,
        }

    def update_record(self, payload):
        if not isinstance(payload, dict) or "id" not in payload:
            raise ValueError("Request payload must include 'id'.")
        sid = int(payload["id"])
        if sid not in self.samples_by_id:
            raise ValueError(f"ID {sid} is not in data/evaluation_ids.json")
        idx = self.ids.index(sid)
        updated = apply_record_update(self.records[idx], self.samples_by_id[sid], payload)
        self.records[idx] = updated
        save_gold(self.records, self.gold_path)
        gold_map = {r["id"]: r for r in self.records}
        return {
            "record": updated,
            "progress": gold_status(self.ids, gold_map),
        }


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def _send_json(self, status, data):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                body = WEB_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif parsed.path == "/api/state":
                self._send_json(HTTPStatus.OK, app.get_state())
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path != "/api/update":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                result = app.update_record(payload)
                self._send_json(HTTPStatus.OK, result)
            except ValueError as error:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    return Handler


def serve_web(host="127.0.0.1", port=8765, gold_path=GOLD_PATH, open_browser=True):
    """Yerel tarayıcı inceleme sunucusunu başlatır."""
    app = AnnotationWebApp(gold_path=gold_path)
    server = ThreadingHTTPServer((host, port), make_handler(app))
    url = f"http://{host}:{server.server_port}"
    status = gold_status(app.ids, {r["id"]: r for r in app.records})
    print(f"Entity review web interface running at: {url}")
    print(f"Progress: {status['verified']}/{status['selected']} verified "
          f"({'complete' if status['complete'] else 'PENDING HUMAN REVIEW'})")
    print("Press Ctrl-C to stop.")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", action="store_true", help="show review progress only")
    parser.add_argument("--prepare-candidates", action="store_true",
                        help="populate unverified records in entity_gold.jsonl with audited second-pass candidates")
    parser.add_argument("--live-llm", action="store_true",
                        help="when used with --prepare-candidates, query local Ollama for second-pass review")
    parser.add_argument("--web", action="store_true",
                        help="launch the fast local browser-based review interface")
    parser.add_argument("--host", default="127.0.0.1", help="bind host for --web (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="bind port for --web (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="do not auto-open browser with --web")
    parser.add_argument("--id", type=int, help="review this sample ID in terminal")
    parser.add_argument("--reviewer", help="name of the human reviewer (required for terminal review)")
    args = parser.parse_args()

    if args.prepare_candidates:
        records = prepare_candidates(GOLD_PATH, live_llm=args.live_llm)
        flagged = sum(1 for r in records if (r.get("review_flags") or {}).get("needs_closer_review"))
        print(f"Prepared {len(records)} candidate records in {GOLD_PATH} "
              f"({flagged} flagged for closer review; 0 auto-verified).")
        return

    if args.web:
        serve_web(host=args.host, port=args.port, gold_path=GOLD_PATH, open_browser=not args.no_browser)
        return

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
        parser.error("--reviewer is required to verify records (or use --web for the browser interface)")
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
