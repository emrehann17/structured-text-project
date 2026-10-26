"""Çevrimdışı testler; yapay hata örnekleri test verisidir, deney sonucu değildir."""

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import evaluate
import llm_pipeline as pipeline

VALID = {"category": "spor", "entities": {"person": [], "organization": [], "location": []}}
RAW = json.dumps(VALID)
SAMPLE = {"id": 1, "text": "Bir spor haberi.", "true_category": "spor"}


class ParsingTests(unittest.TestCase):
    def test_direct_json(self):
        self.assertEqual(pipeline.parse_json_response(RAW), (VALID, True, True))
        self.assertEqual(pipeline.parse_json_response(" \n" + RAW), (VALID, True, True))

    def test_cleaning(self):
        for raw in [f"```json\n{RAW}\n```", f"```JSON\n{RAW}\n```",
                    f"Here is JSON: {RAW}", f"{RAW}\nEnd of answer.",
                    f" Explanation {{broken \n{RAW}\nThank you."]:
            with self.subTest(raw=raw):
                self.assertEqual(pipeline.parse_json_response(raw), (VALID, False, True))

    def test_malformed_truncated_and_empty(self):
        for raw in ['{"category":', '{"category": "spor",', "not JSON", "", "   "]:
            with self.subTest(raw=raw):
                self.assertEqual(pipeline.parse_json_response(raw), (None, False, False))

    def test_truncation_does_not_invent_missing_fields(self):
        # Original recovery can find a nested complete object in truncated text.
        flags = pipeline.evaluate_response(RAW[:-1], "spor")
        self.assertFalse(flags["raw_json_valid"])
        self.assertTrue(flags["clean_json_valid"])
        self.assertFalse(flags["schema_valid"])
        self.assertFalse(flags["category_correct"])

    def test_invalid_schema(self):
        invalid = [42, [], None, {}, {"category": "spor"}]
        for key, value in [("category", []), ("category", "unknown"), ("entities", [])]:
            obj = deepcopy(VALID); obj[key] = value; invalid.append(obj)
        for value in ["name", [42], None]:
            obj = deepcopy(VALID); obj["entities"]["person"] = value; invalid.append(obj)
        obj = deepcopy(VALID); del obj["entities"]["location"]; invalid.append(obj)
        obj = deepcopy(VALID); obj["extra"] = 1; invalid.append(obj)
        obj = deepcopy(VALID); obj["entities"]["extra"] = []; invalid.append(obj)
        for obj in invalid:
            with self.subTest(obj=obj):
                flags = pipeline.evaluate_response(json.dumps(obj), "spor")
                self.assertTrue(flags["raw_json_valid"])
                self.assertFalse(flags["schema_valid"])
                self.assertFalse(flags["category_correct"])

    def test_wrong_category_is_separate_from_structure(self):
        flags = pipeline.evaluate_response(RAW, "ekonomi")
        self.assertTrue(flags["schema_valid"])
        self.assertTrue(flags["raw_json_valid"])
        self.assertFalse(flags["category_correct"])

    def test_optional_reference(self):
        self.assertFalse(pipeline.evaluate_response(RAW)["category_correct"])


class RequestTests(unittest.TestCase):
    def test_request_contract_mocked(self):
        response = Mock()
        response.json.return_value = {"response": RAW, "done_reason": "stop", "eval_count": 40}
        with patch.object(pipeline.requests, "post", return_value=response) as post:
            result = pipeline.evaluate_sample(SAMPLE)
        post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={"model": "qwen2.5:3b", "prompt": pipeline.build_prompt(SAMPLE["text"]),
                  "stream": False, "format": pipeline.JSON_SCHEMA,
                  "options": {"temperature": 0, "seed": 42, "num_ctx": 4096,
                              "num_predict": 384, "repeat_penalty": 1.2, "repeat_last_n": 128}},
            timeout=(5, 60))
        response.raise_for_status.assert_called_once()
        self.assertTrue(result["category_correct"])
        self.assertEqual(result["raw_output"], RAW)

    def test_connection_timeout_and_http_errors(self):
        for error in [pipeline.requests.ConnectionError("offline"),
                      pipeline.requests.Timeout("timeout"), pipeline.requests.HTTPError("500")]:
            with self.subTest(error=error), patch.object(pipeline.requests, "post", side_effect=error):
                result = pipeline.evaluate_sample(SAMPLE)
                self.assertFalse(result["response_received"])
                self.assertFalse(result["category_correct"])
                self.assertIsNotNone(result["api_error"])
        response = Mock()
        response.raise_for_status.side_effect = pipeline.requests.HTTPError("500")
        with patch.object(pipeline.requests, "post", return_value=response):
            self.assertIsNotNone(pipeline.evaluate_sample(SAMPLE)["api_error"])
        response.json.assert_not_called()

    def test_invalid_api_envelope(self):
        for payload in [{}, [], {"response": None}, {"response": 42}]:
            response = Mock(); response.json.return_value = payload
            with patch.object(pipeline.requests, "post", return_value=response):
                self.assertIsNotNone(pipeline.evaluate_sample(SAMPLE)["api_error"])
        response.json.side_effect = ValueError("invalid HTTP JSON body")
        with patch.object(pipeline.requests, "post", return_value=response):
            self.assertIsNotNone(pipeline.evaluate_sample(SAMPLE)["api_error"])

    def test_bad_model_text_is_not_api_error(self):
        for raw in ["", "{", '{"category":"spor"}']:
            with patch.object(pipeline, "call_ollama", return_value={"response": raw}):
                row = pipeline.evaluate_sample(SAMPLE)
                self.assertTrue(row["response_received"])
                self.assertIsNone(row["api_error"])
                self.assertFalse(row["schema_valid"])


class EvaluationTests(unittest.TestCase):
    def test_denominator_and_cleaning_metrics(self):
        samples, rows = [], []
        outputs = [RAW, f"```json\n{RAW}\n```", "{", "{}", RAW, None]
        for index, raw in enumerate(outputs):
            sample = dict(SAMPLE, id=index, true_category="ekonomi" if index == 4 else "spor")
            samples.append(sample)
            rows.append({"id": index, "true_category": sample["true_category"],
                         "raw_output": raw, "response_received": raw is not None,
                         "api_error": "offline" if raw is None else None, "elapsed_seconds": 1})
        result = evaluate.analyze_results(samples, rows)
        self.assertEqual(result["total_requests"], 6)
        for key, count in [("raw_json_success", 3), ("clean_json_success", 4),
                           ("schema_success", 3), ("classification_accuracy", 2)]:
            self.assertEqual(result[key + "_count"], count)
            self.assertEqual(result[key + "_pct"], round(count / 6 * 100, 2))
        self.assertEqual(result["api_errors"], 1)

    def test_saved_results_and_preservation(self):
        original = evaluate.RESULT_PATH.read_bytes()
        dataset = evaluate.DATA_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         "6261136ce0ce69c3964ddea4a2548b7afa027996a79d445b046c0a0453579057")
        self.assertEqual(hashlib.sha256(dataset).hexdigest(),
                         "2a5b6818b3251c5552806ef000eaf4be723cf226e6c96f60b27b001408b128bc")
        samples = evaluate.load_jsonl(evaluate.DATA_PATH)[5:205]
        rows = evaluate.load_jsonl(evaluate.RESULT_PATH)
        self.assertEqual(len({s["id"] for s in samples}), 200)
        self.assertEqual(len({s["text"] for s in samples}), 199)
        # Reanalysis must ignore old flags, even deliberately incorrect ones.
        for row in rows:
            for flag in evaluate.METRICS.values():
                row[flag] = False
        with patch.object(pipeline.requests, "post", side_effect=AssertionError("No network")):
            result = evaluate.analyze_results(samples, rows)
        for metric in ["raw_json_success", "clean_json_success", "schema_success"]:
            self.assertEqual(result[metric + "_count"], 200)
            self.assertEqual(result[metric + "_pct"], 100.0)
        self.assertEqual(result["classification_accuracy_count"], 107)
        self.assertEqual(result["classification_accuracy_pct"], 53.5)
        self.assertEqual(result["responses_received"], 200)
        self.assertEqual(result["api_errors"], 0)
        self.assertEqual(result["total_measured_seconds"], 241.83)
        self.assertEqual(result["average_measured_seconds"], 1.21)
        self.assertEqual(evaluate.RESULT_PATH.read_bytes(), original)
        self.assertEqual(evaluate.DATA_PATH.read_bytes(), dataset)

    def test_incomplete_duplicate_foreign_or_mismatched_records_rejected(self):
        samples = evaluate.load_jsonl(evaluate.DATA_PATH)[5:205]
        rows = evaluate.load_jsonl(evaluate.RESULT_PATH)
        foreign = deepcopy(rows); foreign[0]["id"] = -1
        wrong = deepcopy(rows); wrong[0]["true_category"] = "unknown"
        for invalid in [rows[:-1], rows + [rows[0]], foreign, wrong]:
            with self.assertRaises(ValueError):
                evaluate.analyze_results(samples, invalid)

    def test_default_cli_is_offline_and_preserves_responses(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "saved.jsonl"
            path.write_bytes(evaluate.RESULT_PATH.read_bytes())
            before = path.read_bytes()
            with patch.object(sys, "argv", ["evaluate.py", "--results", str(path)]), \
                 patch.object(pipeline.requests, "post", side_effect=AssertionError("No network")) as post, \
                 patch.object(evaluate, "save_figure"), redirect_stdout(StringIO()):
                evaluate.main()
            post.assert_not_called()
            self.assertEqual(path.read_bytes(), before)
            self.assertTrue(path.with_suffix(".summary.json").exists())

    def test_run_requires_new_output(self):
        for args in [["--run"], ["--run", "--results", str(evaluate.RESULT_PATH)]]:
            with patch.object(sys, "argv", ["evaluate.py"] + args), \
                 patch.object(evaluate, "evaluate_sample") as infer, \
                 patch("sys.stderr", new=StringIO()), self.assertRaises(SystemExit):
                evaluate.main()
            infer.assert_not_called()

    def test_run_continues_after_api_failures_mocked(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fresh.jsonl"
            with patch.object(sys, "argv", ["evaluate.py", "--run", "--results", str(path)]), \
                 patch.object(pipeline.requests, "post", side_effect=pipeline.requests.ConnectionError("offline")) as post, \
                 patch.object(evaluate, "save_figure"), redirect_stdout(StringIO()):
                evaluate.main()
            self.assertEqual(post.call_count, 200)
            summary = json.loads(path.with_suffix(".summary.json").read_text())
            self.assertEqual(summary["total_requests"], 200)
            self.assertEqual(summary["api_errors"], 200)
            self.assertEqual(summary["raw_json_success_pct"], 0)


if __name__ == "__main__":
    unittest.main()
