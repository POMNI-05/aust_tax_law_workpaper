# Local AI review trial — 27 October 2026

## Scope and task plan

Add an optional, on-demand Ollama reviewer to the existing read-only AI boundary.
Use a small local model, bounded inputs/output and immediate model unloading.
Keep deterministic tax logic and generated workbook contents unchanged. Trial
only synthetic evidence and avoid system-wide installation or login services.

1. **Inspect and size — complete.** Read the existing review contracts and
   current TODOs, inspect hardware/runtime availability and verify current
   Ollama APIs against official documentation.
2. **Integrate and test — complete.** Add the local provider, a visible opt-in
   in the staged generator, strict response validation and audit support.
   Validate local-only transport, resource bounds and failure isolation.
3. **Run a local trial — complete.** Download a portable runtime and small model
   into ignored project storage, run synthetic review, measure duration/resource
   use where available, verify unloading, stop the trial service and document
   shared-Mac limits and restart instructions.

## Checklist

- [x] Inspect the machine and existing provider/frontend boundaries.
- [x] Verify structured output, context, concurrency and unload controls.
- [x] Add a localhost-only reviewer without API credentials or cloud fallback.
- [x] Make local review selectable and display its findings/audit in the UI.
- [x] Test strict schema/decision IDs, resource limits and failure isolation.
- [x] Install a portable runtime/model without system-wide changes.
- [x] Run synthetic end-to-end review and verify the workbook is unchanged.
- [x] Confirm the model unloads and stop the temporary service.
- [x] Update project memory, workflow notes and operator instructions.

## Stage 1 evidence

- Mac hardware reports Apple M5, 10 CPU cores, 8 GPU cores and 16 GB unified
  memory. The memory-pressure command reported 42% system-wide memory free at
  inspection; this is a transient observation, not a reserved capacity budget.
- No Ollama, llama.cpp, LM Studio or MLX runtime was found. No Ollama listener
  answered on port 11434.
- The staged generator currently hardcodes AI review off, despite existing
  Gemini/Grok adapters. Local support therefore needs both an adapter and a
  small opt-in UI change.
- Accounts share physical resources. A small model used briefly is a reasonable
  trial; other users' latency cannot be guaranteed without their workloads.
- References: [Ollama structured output](https://docs.ollama.com/capabilities/structured-outputs),
  [chat API](https://docs.ollama.com/api/chat),
  [resource controls](https://docs.ollama.com/faq),
  [Qwen3 1.7B](https://ollama.com/library/qwen3:1.7b).

## Stage 2 evidence

- Added a fixed-loopback Ollama adapter with strict schema and decision-ID
  validation, bounded evidence batches, output/context limits, a local review
  lock and `keep_alive: 0`. The transport bypasses environment proxies and
  rejects redirects and remote endpoints; there is no cloud fallback.
- The generator exposes an optional local-review checkbox and shows findings
  and the existing accountant-disposition audit. Local prompts have their own
  recorded version. AI remains disabled until selected.
- All 124 tests pass, including 10 new local-provider/transport/UI/isolation
  cases. The UI test loads the actual staged generator and toggles the option;
  the failure test proves the generated workbook hash remains unchanged.
- The portable Ollama 0.40.11 download matches the SHA-256 published with the
  official release. Models and runtime are stored under ignored `.local_ai/`.
  First startup creates Ollama's normal identity files under this account's
  `~/.ollama/`; no system-wide installation or login service is configured.

## Stage 3 evidence

- Installed the portable runtime and local Qwen3 1.7B model. The runtime takes
  about 560 MiB and model storage about 1.3 GiB. The downloaded installation
  archive was removed after checksum verification and extraction.
- A synthetic FY2026 workpaper produced six deterministic decision traces,
  completed a live local review and wrote the local-provider/prompt-version
  audit. AI inference took 10.669 seconds; generation plus review and unload
  verification took 11.562 seconds. One request processed 1,299 prompt tokens
  and 273 output tokens, ending normally.
- Ollama's sampled model allocation peaked at 1,914,102,087 bytes (about
  1.78 GiB). This is reported model allocation, not total process/system peak
  memory or a resource guarantee. System memory-free readings changed from
  45% before to 42% after; other workloads/cache make those readings unsuitable
  for attributing all memory changes to the model.
- The two schema-valid findings were generic accountant review reminders.
  This trial validates connectivity, the audit and the read-only boundary,
  not specialist tax-review quality or other accounts' responsiveness.
- The generated workbook's SHA-256 matched before/after AI review and after
  publishing the download. `/api/ps` confirmed no loaded models afterward.
  The foreground server was then stopped; a separate connection check
  confirmed nothing was listening on port 11434.
- Operator instructions: [`local_ai_review.md`](../local_ai_review.md).
  The option remains off by default and no background/login service remains.
