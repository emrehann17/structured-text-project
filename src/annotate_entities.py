"""Manual annotation from article text; no model calls or proposed entities.

python src/annotate_entities.py --web
python src/annotate_entities.py --status
"""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path

from evaluate import ROOT, GOLD_PATH, load_samples, load_gold, gold_status, normalize_entity, validate_gold_record
from llm_pipeline import ENTITY_TYPES, fingerprint


def annotation_state():
    samples, gold = load_samples(), load_gold()
    return {"progress": gold_status([s["id"] for s in samples], gold),
            "samples": [{"id": s["id"], "text": s["text"].replace("_", " "),
                         "annotation": gold[s["id"]]} for s in samples]}


def save_annotation(sample, payload, path=GOLD_PATH):
    """Save only human-entered names supported by this article; regenerate all derived artifacts."""
    reviewer = payload.get("reviewer", "").strip()
    if not reviewer or payload.get("confirmed") is not True:
        raise ValueError("Enter your name and explicitly save the completed annotation")
    record = {"id": sample["id"], "status": "completed", "annotation_method": "manual_from_text",
              "reviewer": reviewer, "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "text_sha256": fingerprint(sample["text"])}
    for kind in sorted(ENTITY_TYPES):
        names = payload.get(kind)
        if not isinstance(names, list) or any(not isinstance(n, str) for n in names):
            raise ValueError("Each entity field must be a list of names")
        record[kind] = [n.strip() for n in names]
    validate_gold_record(record)
    text = normalize_entity(sample["text"])
    for kind in ENTITY_TYPES:
        for name in record[kind]:
            if normalize_entity(name) not in text:
                raise ValueError(f"The selected name is not in this article: {name}")
    records = load_gold(path)
    if sample["id"] not in records:
        raise ValueError("Unknown article ID")
    records[sample["id"]] = record
    temporary = Path(path).with_suffix(".tmp")
    temporary.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records.values()), encoding="utf-8")
    temporary.replace(path)
    return record


def serve(port):
    samples = {s["id"]: s for s in load_samples()}

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, payload, content_type="application/json"):
            body = payload.encode() if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.reply(200, (ROOT / "src/annotation.html").read_text(), "text/html")
            elif self.path == "/api/state":
                self.reply(200, annotation_state())
            else:
                self.reply(404, {"error": "Not found"})

        def do_POST(self):
            if self.path != "/api/save":
                self.reply(404, {"error": "Not found"})
                return
            if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
                self.reply(403, {"error": "Use the local annotation page"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 100000:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(length))
                sample = samples[payload["id"]]
                save_annotation(sample, payload)
            except (ValueError, KeyError, TypeError) as error:
                self.reply(400, {"error": str(error)})
                return
            # Every saved edit rebuilds scores, figure and report from current gold.
            try:
                from build_report import rebuild
                rebuild()
                self.reply(200, annotation_state())
            except Exception as error:
                self.reply(500, {"error": f"Annotation saved; report refresh failed: {error}. Run python src/build_report.py."})

        def log_message(self, *args):
            pass

    print(f"Manual annotation: http://127.0.0.1:{port}", flush=True)
    print("No suggestions are generated. Save each article after selecting its entities.", flush=True)
    with HTTPServer(("127.0.0.1", port), Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.web:
        serve(args.port)
    else:
        print(json.dumps(annotation_state()["progress"], indent=2))


if __name__ == "__main__":
    main()
