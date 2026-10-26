# Workpaper backend

This package owns deterministic Excel intake, account classification and
workpaper generation. It was renamed from `v1/` to `backend/`; personal scripts
should use the new module names.

## Entry points

Run from the repository root:

```bash
python -m backend.main
```

The Streamlit generation runner launches this module with
`TAX_WORKPAPER_REQUEST_PATH` and `TAX_WORKPAPER_RESULT_PATH`. The request defines
the isolated job's inputs, output and logs; the result contains decision traces,
review items and the completed or failed status.

Without a request, local configuration defaults to `backend/data/`,
`backend/output/` and `backend/logs/`. Existing environment overrides in
`config.py` still apply.

The scan runner launches `python -m backend.scan_workbooks` with `TAX_SCAN_ID`,
`TAX_DATA_DIR`, `TAX_JOB_WORK_DIR`, `TAX_SCAN_RESULT_PATH` and
`TAX_SCAN_SOURCE_HASHES`. Scanning discovers evidence and review questions
without labelling accounts, calculating tax or writing a workbook.

## Module responsibilities

| Modules | Responsibility |
| --- | --- |
| `main.py`, `scan_workbooks.py` | Subprocess entry points for generation and scan. |
| `config.py`, `job_config.py`, `utils.py` | Runtime configuration, reviewed job options, directories and logging. |
| `cleaner.py` | Report discovery, period selection and strict amount parsing. |
| `itr_rules*.py`, `itr_metadata.py`, `ato_policy.py` | Supported-year classification rules and return metadata. |
| `labeller.py`, `label_overrides.py`, `decision_trace.py` | Apply labels and approved overrides, preserving decision evidence. |
| `workpaper_builder.py`, `reconciler.py` | Reconciliation and workpaper data blocks. |
| `write_workbook.py` | Preserve source sheets and render the generated workbook. |
| `user_itr_overrides.json` | Persisted accountant-approved label overrides, shared with the frontend override editor. |

Regulated arithmetic remains in the separate `tax_calculators/` package.
Optional AI providers remain in `ai_review/` and receive only downstream
review evidence; they cannot change classifications, rules or workbooks.

## Validation

```bash
python -m unittest discover -s tests -v
```

See [the runtime workflow](../docs/project_workflow.md) and
[the restructure record](../docs/TODO/backend_restructure_todo_20261027.md).
