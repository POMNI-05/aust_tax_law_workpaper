# Stage 2 — Isolated job and backend contract

## Purpose

`frontend/job_runner.py` creates a UUID-scoped job directory, saves copies of
the uploads, writes `request.json`, launches `python -m backend.main`, validates
`result.json`, and publishes only the owned output.

`frontend/scan_runner.py` separately launches `python -m backend.scan_workbooks`
for the preceding scan/confirm step. The scan schema remains `scan_result.v1`.

## Inputs and outputs

- Input: validated UI options and uploaded files.
- Output: `WorkpaperRequest` JSON to the backend and `WorkpaperResult` JSON
  back to the frontend.

## Issue/debugging log

| State | Issue | Diagnosis and safe resolution |
| --- | --- | --- |
| Resolved | `STRUCTURE-001`: the live backend still carried the historical `v1/` package name. | Renamed it to `backend/`, updated both subprocess launchers, imports, metadata and override paths, and moved retained artifacts unchanged. All 114 tests pass. Synthetic FY2024–2026 scans, full decision contracts and workbook contents match the baseline; only the backend metadata name and workbook timestamps differ. All 95 retained non-code file hashes match. |
| Resolved | Environment variables and filesystem paths formed an implicit backend API. | Use the versioned request/result contract; reject malformed results and paths outside the job directory. |
| Guardrail | Backend timeouts or result files are missing. | Show a failed job, publish no output, keep no partially trusted result. |

## Debug procedure

1. Re-run with `retain_job_files=True` only in a safe local debugging session.
2. Inspect that job's `request.json`, `result.json`, and logs; never inspect a
   different job directory.
3. Run `python -m unittest tests.test_workpaper_contract tests.test_job_runner -v`.
4. Check that every output path is inside its UUID job directory before the
   frontend copies it.
