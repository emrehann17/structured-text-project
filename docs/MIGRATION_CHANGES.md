# Migration file inventory

Comparison against the checksum-verified snapshot taken before migration. Historical paths below are archive entries, not active links or commands. Every removed file remains in the external backup. Runtime bytecode caches were cleared and are excluded from this inventory and the submission.

Backup: `/tmp/structured-text-project-backup-20261025T130833Z`. Full archive: `project-before-migration.tar.gz`; original file inventory: `sha256.json`.

Modified: 32; added: 15; removed from active project: 44; unchanged inventoried files: 6.

## Modified / regenerated

- `README.md`
- `data/test_samples.jsonl`
- `docs/CODE_STUDY_GUIDE_TR.md`
- `docs/PRESENTATION_PREPARATION_TR.md`
- `docs/TECHNICAL_QA_TR.md`
- `docs/VERIFICATION_SUMMARY_TR.md`
- `report.pdf`
- `results/figures/category_accuracy.png`
- `results/figures/category_accuracy.svg`
- `results/figures/classification_accuracy.png`
- `results/figures/classification_accuracy.svg`
- `results/figures/confusion_matrix.png`
- `results/figures/confusion_matrix.svg`
- `results/figures/inference_performance.png`
- `results/figures/inference_performance.svg`
- `results/figures/json_success_comparison.png`
- `results/figures/json_success_comparison.svg`
- `results/figures/schema_failure_analysis.png`
- `results/figures/schema_failure_analysis.svg`
- `results/improved_prompt_results.jsonl`
- `results/metrics_summary.json`
- `results/optimized_schema_results.jsonl`
- `results/schema_results.jsonl`
- `results/v3_confusion_matrix.csv`
- `src/analyze_final.py`
- `src/build_report_pdf.py`
- `src/evaluate_schema.py`
- `src/evaluate_v2.py`
- `src/evaluate_v3.py`
- `src/generate_report_assets.py`
- `src/prepare_dataset.py`
- `structured-text-project-submission.zip`

## Added canonical files and validation evidence

- `data/test_samples_manifest.json`
- `docs/MIGRATION_CHANGES.md`
- `docs/migration_manifest.json`
- `docs/pdf_validation.json`
- `docs/validation_results.json`
- `docs/verification.json`
- `results/STATUS_TR.md`
- `results/confusion_matrix_A.csv`
- `results/confusion_matrix_B.csv`
- `results/execution_environment.json`
- `results/run_identity.json`
- `src/package_submission.py`
- `src/run_evaluation.py`
- `src/verify_project.py`
- `tests/test_evaluation.py`

## Removed redundant or historical files (retained in backup)

- `README_200.md`
- `data/test_samples_205.jsonl`
- `data/test_samples_205_manifest.json`
- `docs/CHANGELOG_200_TR.md`
- `docs/audit_200/historical_metrics_recomputed.json`
- `docs/audit_200/offline_validation.json`
- `docs/audit_200/original_sha256.json`
- `docs/audit_200/original_source/analyze_final.py`
- `docs/audit_200/original_source/build_report_pdf.py`
- `docs/audit_200/original_source/evaluate.py`
- `docs/audit_200/original_source/evaluate_schema.py`
- `docs/audit_200/original_source/evaluate_v2.py`
- `docs/audit_200/original_source/evaluate_v3.py`
- `docs/audit_200/original_source/generate_report_assets.py`
- `docs/audit_200/original_source/prepare_dataset.py`
- `docs/audit_200/original_source/test_model.py`
- `docs/audit_200/source_comments_only.diff`
- `docs/audit_200/unit_tests.txt`
- `docs/audit_200/variants_allowed_changes.diff`
- `docs/audit_200/verification.json`
- `report_200_pending.pdf`
- `results/evaluation_200/STATUS_TR.md`
- `results/evaluation_200/confusion_matrix_A.csv`
- `results/evaluation_200/confusion_matrix_A.png`
- `results/evaluation_200/confusion_matrix_B.csv`
- `results/evaluation_200/confusion_matrix_B.png`
- `results/evaluation_200/confusion_matrix_C.csv`
- `results/evaluation_200/confusion_matrix_C.png`
- `results/evaluation_200/execution_environment.json`
- `results/evaluation_200/improved_prompt_results.jsonl`
- `results/evaluation_200/metrics_summary_200.json`
- `results/evaluation_200/optimized_schema_results.jsonl`
- `results/evaluation_200/run_identity.json`
- `results/evaluation_200/schema_results.jsonl`
- `src/analyze_200.py`
- `src/build_report_200.py`
- `src/evaluate_schema_200.py`
- `src/evaluate_v2_200.py`
- `src/evaluate_v3_200.py`
- `src/prepare_dataset_205.py`
- `src/run_evaluation_200.py`
- `src/verify_200.py`
- `structured-text-project-200-pending.zip`
- `tests/test_evaluation_200.py`

## Unchanged inventoried project files

- `.env`
- `.gitignore`
- `requirements.txt`
- `results/baseline_results.jsonl`
- `src/evaluate.py`
- `src/test_model.py`

## What changed and why

The completed dataset and three result files were promoted byte for byte. Inference modules preserve their executable AST after path normalization and module docstring removal. The runner now exits without inference when all 600 records are present. Dataset preparation replays the existing selection algorithm and verifies the frozen manifest hash. Analysis recomputes saved flags, checks IDs and produces canonical metrics/matrices. Figures, report, README and Turkish guides now use the completed evaluation. Verification and packaging scripts validate the current project. No model inference was performed during migration.

The run identity now uses canonical script names and hashes. Original executed-source hashes and the AST equality evidence are recorded in `migration_manifest.json`; the untouched original identity is archived. The five baseline development responses were retained separately.

Validation: 205 dataset records, 5 development records, 200 evaluation records, identical ordered 200-ID coverage in A/B/C, 199 distinct evaluation texts, all 600 flags recomputed, all stored final metrics identical to the completed source summary, all three matrices total 200, six regenerated PNG/SVG figures, six PDF pages rendered and visually reviewed, syntax checks passed, five tests passed, and dataset reconstruction reproduced the exact hash.

IDs 2138 and 2296 are the same text; no membership was changed after inference. No historical source result was lost: the archive contains three previous 135-record results, three completed 200-record results and the five development records. The current submission excludes archived versions, environments and caches.
