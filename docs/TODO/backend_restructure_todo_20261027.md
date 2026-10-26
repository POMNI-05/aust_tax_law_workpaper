# Backend package restructure — 27 October 2026

## Scope

Replace the active backend's historical `v1/` name with `backend/`. Keep the
frontend, deterministic calculators and read-only AI adapters as separate
packages. Preserve rule contents, accountant overrides, source workbooks,
generated files, request/result formats and the Streamlit launch command.

## Task plan

1. **Map and baseline — complete.** Identify imports, dynamic rule loading,
   subprocess commands, configuration paths and retained local artifacts. Run
   the existing suite and record a scan/generate baseline using synthetic data.
2. **Migrate the package — complete.** Move the package and retained local
   artifacts together; update callers, tests and current workflow references.
   Replace misleading hard-coded input-location messages with the actual job
   location or user-facing upload guidance.
3. **Verify and document — complete.** Compare workbook contents, decision
   evidence and scan results with the baseline, check retained artifact hashes,
   run the existing suite, and document package responsibilities and commands.

## Checklist

- [x] Map all runtime and test references to the package.
- [x] Run baseline checks and retain synthetic scan/generation results.
- [x] Rename `v1/` to `backend/` and update package paths and helper names.
- [x] Keep persisted overrides and local artifacts byte-for-byte intact.
- [x] Verify scan and generation use the renamed modules.
- [x] Run the existing suite and compare deterministic outputs to the baseline.
- [x] Update README, project memory and owning workflow/debugging logs.

**Exit criterion:** the active backend is clearly named, scan and generation
work through the new package, and deterministic results and retained evidence
are unchanged.

## Stage 1 result

- Python 3.13.13: all 114 existing tests passed.
- Synthetic FY2024, FY2025 and FY2026 workbooks completed scan, source-hash
  verification and isolated generation. Before/after snapshots in temporary
  storage capture scan results, the full decision/result contract and every
  workbook ZIP member, excluding only creation/modification timestamps.
- Hashed 95 retained non-code files under the old package for preservation
  verification; financial filenames and data are not copied into this log.
- Imports, dynamic rule loading, both subprocess launchers, override readers
  and workflow documentation are in scope. Large-module decomposition remains
  separate work; this change establishes a clear package name first.

## Stage 2 result

- Renamed the package and retained directories together; no `v1/` directory
  remains. Updated imports, mock targets, dynamic-matcher expectations, both
  subprocess launchers, backend metadata and frontend override paths.
- All 95 retained non-code files match their original SHA-256 hashes. Both
  override readers resolve to the same preserved JSON file.
- Existing focused policy-year, job-runner, isolated-generation and contract
  checks passed: 25 tests. Full cross-year output comparison follows in Stage 3.
- Package-name replacements leave external API versions, Streamlit's testing
  namespace and the `scan_result.v1` schema version intact.

## Stage 3 result

- All 114 existing tests pass after migration under Python 3.13.13. All project
  Python sources compile, and `git diff --check` passes.
- FY2024, FY2025 and FY2026 synthetic scans, source hashes and full decision
  contracts match the baseline. Every generated workbook ZIP member matches,
  excluding only creation/modification timestamps; the result contract's
  backend metadata correctly identifies `backend.main`.
- All 95 original retained non-code files remain byte-for-byte unchanged.
  Sixteen backend modules have identical executable syntax after ignoring
  docstrings; only `main.py` and the matcher diagnostic in `labeller.py` differ.
- README, backend package guide, project memory and runtime workflow/debugging
  documentation describe the new paths and commands. Existing Streamlit
  launchers and request/result schemas are unchanged.
- The unrelated, pre-existing `Annual_rule_update.md` remains untouched.
