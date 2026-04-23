# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Global Python CLI utilities, installed on `$PATH` and runnable from anywhere. Most scripts here are thin wrappers around third-party AI generation APIs (Google Gemini/Veo, Replicate, xAI, Kie AI, etc.).

## Architecture: the shared CLI shape

Every script in this repo follows the same shape. When adding a new one, mirror it — do not invent a new layout.

1. **Shebang + module docstring**: `#!/usr/bin/env python3`, one-line purpose string.
2. **Model/constant tables at top**: e.g. `MODELS = {"lite": "...", "pro": "..."}`, `ASPECT_RATIOS = [...]`. User-facing choices map to vendor IDs here.
3. **`parse_args()` with `argparse.ArgumentDefaultsHelpFormatter`**:
   - Positional `prompt` (for generation scripts).
   - `-o/--output-dir` required — created if missing, never defaulted to CWD.
   - `-n/--name` optional filename stem; defaults to `datetime.now().strftime("<tool>-%Y%m%d-%H%M%S")`.
   - Model/size/aspect/duration flags with explicit `choices=` when the API enumerates them.
   - Long-running APIs expose `--poll-interval` (and `--timeout` where applicable).
4. **Env-var check first thing in `main()`**: fail fast with `sys.exit("error: <VAR> is not set in the environment.")` before any network call.
5. **Cross-flag validation next**: replicate the vendor's schema constraints locally so users get a clear error instead of a server 400 (see `veo`'s "1080p requires duration=8", `seedance`'s exclusivity between `--image` and `--ref-image`).
6. **Deferred imports**: import heavy vendor SDKs (`google.genai`, `replicate`, `xai_sdk`) *inside* `main()`, after arg parsing. Keeps `--help` instant and avoids paying import cost on misuse.
7. **Media input helpers**: for scripts that accept images/videos, support both local paths and `http(s)://` / `data:` URIs. Patterns vary by SDK:
   - Gemini (`veo`): load bytes + mime type into `types.Image(image_bytes=..., mime_type=...)`.
   - Replicate (`seedance`): pass open file handles; SDK uploads automatically.
   - xAI (`xvideo`): base64-encode local files into `data:` URIs.
8. **Output contract**: print the final file path(s) to stdout, one per line. No extra chatter on success. Progress/status goes to stderr or is gated behind poll-loop prints.
9. **Surface vendor errors explicitly**: when a response is empty (safety filter, etc.), dump whatever the server returned to stderr before `sys.exit(1)` — see `veo`'s `rai_media_filtered_*` handling. Do not let opaque `AttributeError`s through.

## Environment

- A Python virtualenv is already activated globally in the user's shell. Do **not** create a new venv or prepend activation. Just invoke `python` / `pip` directly.
- Install dependencies with `uv pip install <pkg>` — the global `~/.venv` has no `pip` module, so `pip` and `python -m pip` will fail.
- If a script grows real dependencies, add a `requirements.txt` at the repo root so the global env stays reproducible.

## Script-authoring conventions

- Self-executable, no extension: `touch ~/.scripts/<name> && chmod +x ~/.scripts/<name>`. This dir is on `$PATH`, so invoke as `<name>` from anywhere.
- Every flag needs a `help=` string. `<name> --help` is the contract.
- Resolve paths explicitly via args (`Path(...).expanduser()`); never rely on CWD — scripts run from arbitrary directories.
- Default to duplication. Don't extract a shared module on spec. When two scripts grow the same helper, flag it and get user buy-in before extracting. Exception: `kie_api.py` already exists — use it for any Kie-backed script (see below).
- Don't `git init` — the repo already exists. Use normal git workflows.

## Shared library: `kie_api.py`

`kie_api.py` is a non-executable Python module (no shebang, `.py` extension) holding the Kie AI plumbing shared by every Kie-backed script. Stdlib-only (`urllib`, `json`, `mimetypes`). Never calls `sys.exit` — raises `KieError`; CLI layers catch and translate.

Surface:

| Function | Purpose |
|---|---|
| `get_api_key()` | Read `KIE_AI_API_KEY` from env or raise. |
| `is_url(s)` | Is `s` an http(s) URL? |
| `upload_local_file(path, api_key, *, upload_path=None, file_name=None)` | Multipart stream upload. Returns `fileUrl`. |
| `upload_url(file_url, api_key, *, upload_path=None, file_name=None)` | Tell Kie to fetch a remote URL. Returns `fileUrl`. |
| `resolve_to_url(ref, api_key, *, label)` | URL → pass through; local path → stream-upload. |
| `create_task(model, input_body, api_key, *, callback_url=None)` | `POST /api/v1/jobs/createTask`. Returns `taskId`. |
| `get_task(task_id, api_key)` | `GET /api/v1/jobs/recordInfo`. Returns the `data` dict. |
| `poll_task(task_id, api_key, *, poll_interval, timeout, on_wait=None)` | Poll until terminal. Returns final `data` or raises. |
| `result_urls(data)` | Parse `resultJson.resultUrls[]` from a success `data` dict. |
| `download(url, dest)` / `download_result_urls(urls, out_dir, stem, *, default_ext)` | Stream media to disk. |

Consumers import it via a `sys.path` prelude (the scripts dir isn't on `PYTHONPATH`):

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from kie_api import KieError, create_task, poll_task, resolve_to_url, result_urls, download_result_urls, get_api_key
```

### Companion CLIs

- **`kie-upload SOURCE [--path DIR] [--name FILENAME]`** — upload a local file (stream) or http(s) URL (url-upload) and print the returned `fileUrl`.
- **`kie-task TASKID [-w/--wait] [--poll-interval N] [--timeout N] [-o/--download DIR] [-n NAME] [--ext EXT]`** — query/poll a task. Without flags, prints the `data` object as JSON. With `--download`, writes every `resultUrl` to disk and prints saved paths (implies `--wait`). Progress messages go to stderr so JSON/paths on stdout stay pipe-clean.

When adding a new Kie-backed model script, build on `kie_api` + optionally shell out to `kie-upload` / `kie-task` for one-off flows — don't re-implement HTTP.

## API keys / env vars by script

| Script | Env var | Vendor |
|---|---|---|
| `nano-banana` | `GEMINI_API_KEY` | Google Gemini (Nano Banana 2 / Pro) |
| `veo` | `GEMINI_API_KEY` | Google Veo 3.1 Lite |
| `seedance` | `KIE_AI_API_KEY` | Kie AI (ByteDance Seedance 2.0 / 2.0 Fast) |
| `kie-upload` | `KIE_AI_API_KEY` | Kie AI file store |
| `kie-task` | `KIE_AI_API_KEY` | Kie AI task polling/download |
| `xvideo` | `XAI_API_KEY` | xAI Grok Imagine |

## Kie AI integration

Kie AI is a model marketplace that fronts many vendors (Seedream, Flux, Imagen, Kling, Sora2, Runway, Suno, ElevenLabs, Veo 3.1, etc.) behind one unified task-based API. Full docs: <https://docs.kie.ai/llms.txt> — **always fetch the current docs** before writing a Kie-backed script; per-model payload schemas live there, not in your training data.

Shape of the API (common across models):

1. **Create task**: `POST /api/v1/jobs/createTask` with `{model, input, callBackUrl?}` → returns `{code, msg, data: {taskId}}`.
2. **Poll**: `GET /api/v1/jobs/recordInfo?taskId=...` until `data.state` ∈ `{success, fail}`. States: `waiting`, `queuing`, `generating`, `success`, `fail`.
3. **Download**: on `success`, `data.resultJson` is a JSON *string* containing `{resultUrls: [...]}` (plus model-specific extras like `firstFrameUrl`/`lastFrameUrl`). URLs expire (images ~14d, uploads ~3d), so always download to `--output-dir`.

**Auth:** `Authorization: Bearer $KIE_AI_API_KEY`. Envelope is `{code, msg, data}`; `code: 200` = OK, other documented codes include 400/401/404/422/429/500.

**Base URLs:**
- Main API: `https://api.kie.ai`
- File uploads: `https://kieai.redpandaai.co` (separate host — don't assume `api.kie.ai`)

When writing a Kie-backed script:

- Use `kie_api.py` (see the section above) for all HTTP/upload/poll/download plumbing. Don't reimplement it.
- `KIE_AI_API_KEY` env check → argparse with `choices=` for enum fields → build `input` dict → `create_task` → `poll_task` → `result_urls` → `download_result_urls` → print path.
- Accept local paths *or* URLs in `--image`-type flags and funnel through `resolve_to_url` — it pass-throughs URLs and stream-uploads local files.
- Don't use `callBackUrl` for CLI flows — poll instead. Webhooks need a public endpoint the CLI can't offer.
- Per-model quirks live in the Kie docs: some models return multiple artifacts (Suno = 2 tracks), some gate fields by tier (Seedance `1080p` is pro-only), some surface progress (Sora2 exposes a `progress` 0-100). Fetch the docs page for the specific model before coding.

## Related reference

- `README.md` — user-facing install and per-script usage.
- `yt-dlp.md` — notes on the globally-installed `yt-dlp` binary (not a script in this repo).
