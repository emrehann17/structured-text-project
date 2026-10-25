"""Yalnız yeni 200 analizinin payda/hata/kimlik kontrollerini sınar.

Tamamı yapay birim testi verisidir: Ollama çağrısı yapılmaz, gerçek haber
sonucu oluşturulmaz, hiçbir deney JSONL dosyasına kayıt yazılmaz.
"""

import copy
import importlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from step4_analyze_results import analyze_experiment


class AnalysisTests(unittest.TestCase):
    """Bilinen beş hata/temizlik durumu üzerinden paydaları kontrol eder."""

    def fixture(self):
        """200 yapay haber ve elle belirlenmiş beklenen başarı bayraklarını döndürür."""
        categories = ["dunya", "ekonomi", "kultur", "saglik", "siyaset", "spor", "teknoloji"]
        samples, rows = [], []
        for i in range(200):
            category = categories[i % 7]
            samples.append({"id": 10000 + i, "text": "YAPAY BİRİM TESTİ", "true_category": category})
            raw = json.dumps({"category": category, "entities": {"person": [], "organization": [], "location": []}})
            rows.append({"id": 10000 + i, "true_category": category, "raw_output": raw,
                "raw_json_valid": True, "clean_json_valid": True, "schema_valid": True,
                "category_correct": True, "response_received": True, "api_error": None, "elapsed_seconds": 0.5})
        rows[0].update(raw_output=None, raw_json_valid=False, clean_json_valid=False,
            schema_valid=False, category_correct=False, response_received=False, api_error="YAPAY TEST HATASI")
        rows[1].update(raw_output="{", raw_json_valid=False, clean_json_valid=False,
            schema_valid=False, category_correct=False)
        rows[2].update(raw_output='{"category":"kultur"}', schema_valid=False, category_correct=False)
        wrong = json.loads(rows[3]["raw_output"])
        wrong["category"] = "spor"
        rows[3].update(raw_output=json.dumps(wrong), category_correct=False)
        rows[4].update(raw_output="```json\n" + rows[4]["raw_output"] + "\n```", raw_json_valid=False)
        return samples, rows

    def test_complete_counts_include_api_and_format_errors(self):
        """200 payda, koşullu payda ve INVALID sütunu birbirinden ayrılmalı."""
        for name in ("step3a_evaluate_prompt", "step3b_evaluate_json", "step3c_evaluate_optimized"):
            with self.subTest(method=name):
                samples, rows = self.fixture()
                result, matrix = analyze_experiment(rows, samples, importlib.import_module(name))
                self.assertEqual(result["status"], "complete")
                self.assertEqual(result["responses_received"], 199)
                self.assertEqual(result["api_error_count"], 1)
                metrics = result["final_metrics"]
                self.assertEqual(metrics["raw_json_success_count"], 197)
                self.assertEqual(metrics["clean_json_success_count"], 198)
                self.assertEqual(metrics["schema_success_count"], 197)
                self.assertEqual(metrics["category_correct_count"], 196)
                self.assertEqual(metrics["end_to_end_accuracy_pct"], 98.0)
                self.assertEqual(metrics["conditional_accuracy_pct"], round(196 / 197 * 100, 2))
                self.assertEqual(metrics["mean_inference_seconds"], 0.5)
                self.assertEqual(metrics["total_inference_seconds"], 100.0)
                self.assertEqual(sum(sum(r.values()) for r in matrix.values()), 200)
                self.assertEqual(sum(matrix[c][c] for c in matrix), 196)
                self.assertEqual(sum(r["INVALID"] for r in matrix.values()), 3)
                self.assertEqual(matrix["saglik"]["spor"], 1)
                self.assertEqual(metrics["per_category"]["dunya"]["total"], 29)
                self.assertEqual(metrics["per_category"]["dunya"]["correct"], 28)

    def test_partial_run_is_pending(self):
        """199 kayıt veya boş küme nihai oran ve matris üretmemeli."""
        samples, rows = self.fixture()
        module = importlib.import_module("step3c_evaluate_optimized")
        for partial in ([], rows[:135], rows[:199]):
            result, matrix = analyze_experiment(partial, samples, module)
            self.assertEqual(result["status"], "pending")
            self.assertIsNone(result["final_metrics"])
            self.assertIsNone(matrix)

    def test_duplicate_foreign_id_and_false_flag_fail(self):
        """Tekrarlı/yabancı ID ve değiştirilmiş bayrak sessizce kabul edilmemeli."""
        samples, rows = self.fixture()
        module = importlib.import_module("step3c_evaluate_optimized")
        duplicate = rows + [rows[0]]
        foreign = copy.deepcopy(rows)
        foreign[0]["id"] = -1
        incorrect = copy.deepcopy(rows)
        incorrect[0]["schema_valid"] = True
        for bad in (duplicate, foreign, incorrect):
            with self.assertRaises(AssertionError):
                analyze_experiment(bad, samples, module)



class ResumeTests(unittest.TestCase):
    """Gerçek çıkarım yapmadan dolu/kısmi checkpoint sürdürmesini sınar."""

    def test_completed_and_partial_checkpoints(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        root = Path(__file__).resolve().parents[1]
        samples = [json.loads(line) for line in (root/'data/test_samples.jsonl').read_text().splitlines()]
        for name,filename in [('step3a_evaluate_prompt','improved_prompt_results.jsonl'),('step3b_evaluate_json','schema_results.jsonl'),('step3c_evaluate_optimized','optimized_schema_results.jsonl')]:
            module = importlib.import_module(name)
            original = (root/'results'/filename).read_bytes()
            rows = [json.loads(line) for line in original.splitlines()]
            with self.subTest(method=name), TemporaryDirectory() as tmp:
                result = Path(tmp)/filename
                result.write_bytes(original)
                with patch.object(module,'RESULT_PATH',result), patch.object(sys,'argv',[name]), patch.object(module,'evaluate_sample',side_effect=AssertionError('Completed IDs must not be inferred')) as infer, redirect_stdout(StringIO()):
                    module.main()
                    infer.assert_not_called()
                self.assertEqual(result.read_bytes(),original)
                result.write_bytes(b'\n'.join(original.splitlines()[:-1])+b'\n')
                with patch.object(module,'RESULT_PATH',result), patch.object(sys,'argv',[name]), patch.object(module,'evaluate_sample',return_value=rows[-1]) as infer, redirect_stdout(StringIO()):
                    module.main()
                    infer.assert_called_once_with(samples[-1])
                resumed = [json.loads(line) for line in result.read_text().splitlines()]
                self.assertEqual(resumed,rows)
                self.assertEqual(len({row['id'] for row in resumed}),200)

    def test_completed_runner_makes_no_network_or_subprocess_calls(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        import step3_run_experiments
        with patch.object(step3_run_experiments.requests,'get',side_effect=AssertionError('No network')) as get, patch.object(step3_run_experiments.requests,'post',side_effect=AssertionError('No network')) as post, patch.object(step3_run_experiments.subprocess,'run',side_effect=AssertionError('No subprocess')) as run, redirect_stdout(StringIO()):
            step3_run_experiments.main()
            get.assert_not_called()
            post.assert_not_called()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
