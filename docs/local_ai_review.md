# Local AI review trial

The staged generator can optionally review completed decision evidence with
Ollama and `qwen3:1.7b`. The review runs on this Mac and needs no API key. It has
the same read-only boundary as the cloud adapters: it cannot change tax rules,
labels, approved adjustments or workbook contents. This is an experimental
small-model review, and every finding needs independent accountant review.

## Use the installed trial

From the repository root, start the server in a terminal:

```bash
python tools/run_local_ai.py
```

Keep that terminal open. In another terminal, start the app as usual:

```bash
python -m streamlit run frontend/app.py
```

After **Scan files** and reviewer confirmation, select **Run local AI review
(experimental, read-only)** before generating. The result shows the review
status and an expandable audit with findings and accountant disposition.
The checkbox is off by default. An unavailable model/server or invalid response
leaves the generated workbook available and shows a review warning.

Press **Ctrl+C** in the server terminal when finished. No login item or
system-wide service is installed. The model unloads after each request even
while the idle server remains open.

## Installation and storage

This trial uses the portable Ollama 0.40.11 runtime from the
[official release](https://github.com/ollama/ollama/releases/tag/v0.40.11), with
the published archive SHA-256 verified before extraction. The runtime is under
`.local_ai/runtime/` and models are under `.local_ai/models/`; `.local_ai/` is
ignored by Git. First startup also creates Ollama's standard per-account
identity files in `~/.ollama/`. No API key or cloud sign-in is needed.

On a fresh checkout, install Ollama from its
[official download](https://ollama.com/download), then start the server with
the helper above. It can use an installed `ollama` executable or the portable
one. With the server running, download the selected model once:

```bash
ollama pull qwen3:1.7b
```

For this portable installation, the equivalent command is:

```bash
./.local_ai/runtime/ollama pull qwen3:1.7b
```

The model download is about 1.4 GB. Downloading the runtime/model needs internet;
review requests use only `http://127.0.0.1:11434/api/chat`. The helper disables
Ollama cloud support. The adapter permits only the selected local model, skips
environment proxies, rejects redirects and remote endpoints, and has no cloud
fallback. A loopback server is local to the machine, not private to one macOS
account; it should run only during the intended review session.

## Shared Mac resource controls

This Mac reports an Apple M5 and 16 GB unified memory. All accounts share the
CPU, GPU, memory and storage. A model download consumes disk/network resources;
active review consumes compute and memory even after switching accounts.

The trial applies these controls:

- One loaded model and one inference request at a time, with a short queue.
- Lower CPU scheduling priority, two CPU inference threads, an 8,192-token
  context and a 1,024-token output limit.
- `keep_alive: 0`, which unloads the model after every request.
- A fixed input-size limit per batch, up to 16 batches, a 60-second timeout per
  request and a 120-second overall review budget. Oversized/incomplete/invalid
  reviews produce no accepted partial findings.

These controls are not hard CPU, GPU or RAM quotas. GPU inference can still
briefly compete with another account's video calls, graphics or other work.
Memory pressure and swapping depend on all users' applications. Measure normal
shared workloads before deciding whether local review is suitable for routine
use; the small synthetic trial does not establish production review quality or
guarantee other users' responsiveness.

Larger evidence sets are partitioned without dropping decisions. Review items
stay with their referenced decision; global items go in the first batch.
The result explicitly notes that cross-batch issues may be missed.

## Validation and audit

The live synthetic trial on 27 October 2026 reviewed six decisions in one
request: 10.7 seconds of local inference and 11.6 seconds including workbook
generation and unload verification. Sampled model allocation was about
1.78 GiB, excluding other server/system overhead. It returned two generic
accountant-review reminders. The workbook hash was unchanged, the model
unloaded and the trial server was stopped. These measurements describe one
small fixture, not typical full-workpaper latency or specialist review quality.

```bash
python -m unittest tests.test_local_ai_review -v
python -m unittest discover -s tests -v
```

The existing local audit records provider/model, input hash, the local prompt
version (`1.0-local.1`), findings and accountant disposition. It is never read
by the tax engine. See [data handling](ai_review_data_handling.md) and the
[trial task record](TODO/local_ai_review_todo_20261027.md).

Official references: [structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[chat API and unload option](https://docs.ollama.com/api/chat),
[resource configuration](https://docs.ollama.com/faq),
[selected model](https://ollama.com/library/qwen3:1.7b).
