"""Shared helpers for Kie AI (https://docs.kie.ai).

Covers the bits every Kie-backed script in this repo needs:

- Auth env var (KIE_AI_API_KEY).
- File upload (local path via multipart stream; remote URL via url-upload).
- Task lifecycle: createTask -> poll recordInfo -> download resultUrls.

Not a CLI. Imported by `kie-upload`, `kie-task`, `seedance`, ... — consumers
do `sys.path.insert(0, <this dir>)` then `from kie_api import ...`. See the
"Shared library: kie_api" section in CLAUDE.md.
"""

import json
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Iterable, Optional

API_BASE = "https://api.kie.ai"
UPLOAD_BASE = "https://kieai.redpandaai.co"
ENV_KEY = "KIE_AI_API_KEY"

TERMINAL_OK = "success"
TERMINAL_FAIL = "fail"


class KieError(RuntimeError):
    """Any error originating from Kie AI or these helpers. CLI layers catch
    this and translate to sys.exit; the library itself never calls sys.exit."""


def get_api_key() -> str:
    key = os.environ.get(ENV_KEY)
    if not key:
        raise KieError(f"{ENV_KEY} is not set in the environment.")
    return key


def is_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def _request(url: str, api_key: str, *, body=None, method: str = "GET") -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": f"Bearer {api_key}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise KieError(f"{method} {url} returned {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise KieError(f"{method} {url} failed: {e.reason}") from e


def upload_local_file(
    path: Path,
    api_key: str,
    *,
    upload_path: Optional[str] = None,
    file_name: Optional[str] = None,
) -> str:
    """Upload a local file via Kie's multipart stream endpoint. Returns fileUrl."""
    path = Path(path)
    if not path.is_file():
        raise KieError(f"file not found: {path}")
    mime, _ = mimetypes.guess_type(str(path))
    if mime is None:
        mime = "application/octet-stream"

    boundary = f"----pyboundary{os.urandom(8).hex()}"
    parts: list[bytes] = [
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode(),
        path.read_bytes(),
        b"\r\n",
    ]
    if upload_path:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="uploadPath"\r\n\r\n'
                f"{upload_path}\r\n"
            ).encode()
        )
    if file_name:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="fileName"\r\n\r\n'
                f"{file_name}\r\n"
            ).encode()
        )
    parts.append(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{UPLOAD_BASE}/api/file-stream-upload",
        data=b"".join(parts),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise KieError(f"upload of {path.name} returned {e.code}: {detail}") from e

    if not resp.get("success") or not resp.get("data", {}).get("fileUrl"):
        raise KieError(f"upload of {path.name} failed: {resp}")
    return resp["data"]["fileUrl"]


def upload_url(
    file_url: str,
    api_key: str,
    *,
    upload_path: Optional[str] = None,
    file_name: Optional[str] = None,
) -> str:
    """Have Kie fetch a remote URL and re-host it. Returns the new fileUrl."""
    body: dict = {"fileUrl": file_url}
    if upload_path:
        body["uploadPath"] = upload_path
    if file_name:
        body["fileName"] = file_name
    resp = _request(
        f"{UPLOAD_BASE}/api/file-url-upload", api_key, body=body, method="POST"
    )
    if not resp.get("success") or not resp.get("data", {}).get("fileUrl"):
        raise KieError(f"url-upload failed: {resp}")
    return resp["data"]["fileUrl"]


def resolve_to_url(ref: str, api_key: str, *, label: str = "input") -> str:
    """Accept a local path or http(s) URL; ensure Kie has a URL for it.
    URLs pass through unchanged (task bodies accept them directly); local
    paths go through a stream upload."""
    if is_url(ref):
        return ref
    path = Path(ref).expanduser()
    if not path.is_file():
        raise KieError(f"{label} not found: {path}")
    return upload_local_file(path, api_key)


def create_task(
    model: str,
    input_body: dict,
    api_key: str,
    *,
    callback_url: Optional[str] = None,
) -> str:
    """POST /api/v1/jobs/createTask. Returns the taskId."""
    body: dict = {"model": model, "input": input_body}
    if callback_url:
        body["callBackUrl"] = callback_url
    resp = _request(
        f"{API_BASE}/api/v1/jobs/createTask", api_key, body=body, method="POST"
    )
    if resp.get("code") != 200 or not resp.get("data", {}).get("taskId"):
        raise KieError(f"createTask failed: {resp}")
    return resp["data"]["taskId"]


def get_task(task_id: str, api_key: str) -> dict:
    """GET /api/v1/jobs/recordInfo?taskId=... Returns the `data` object."""
    url = (
        f"{API_BASE}/api/v1/jobs/recordInfo?"
        + urllib.parse.urlencode({"taskId": task_id})
    )
    resp = _request(url, api_key)
    if resp.get("code") != 200:
        raise KieError(f"recordInfo failed: {resp}")
    return resp.get("data") or {}


def poll_task(
    task_id: str,
    api_key: str,
    *,
    poll_interval: float = 5,
    timeout: float = 900,
    on_wait: Optional[Callable[[dict], None]] = None,
) -> dict:
    """Poll recordInfo until state is terminal. Returns the final `data` dict.

    on_wait: called with the latest `data` on each non-terminal tick, before
    sleeping. Use it to emit progress messages from the caller.

    Raises KieError on fail state or timeout.
    """
    deadline = time.time() + timeout
    while True:
        data = get_task(task_id, api_key)
        state = data.get("state")
        if state == TERMINAL_OK:
            return data
        if state == TERMINAL_FAIL:
            raise KieError(
                f"task {task_id} failed "
                f"[{data.get('failCode')}]: {data.get('failMsg')}"
            )
        if time.time() > deadline:
            raise KieError(
                f"timed out after {timeout}s; task {task_id} still in state "
                f"{state!r}. Query later with taskId={task_id}."
            )
        if on_wait is not None:
            on_wait(data)
        time.sleep(poll_interval)


def result_urls(data: dict) -> list[str]:
    """Pull resultUrls[] out of a terminal-success task's data dict."""
    raw = data.get("resultJson") or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise KieError(f"could not parse resultJson: {raw!r}") from e
    urls = parsed.get("resultUrls") or []
    if not isinstance(urls, list):
        raise KieError(f"resultJson.resultUrls is not a list: {urls!r}")
    return urls


def download(url: str, dest: Path) -> None:
    dest = Path(dest)
    with urllib.request.urlopen(url) as src, open(dest, "wb") as dst:
        while True:
            chunk = src.read(1 << 20)
            if not chunk:
                break
            dst.write(chunk)


def _ext_for_url(url: str, default: str) -> str:
    parsed = urllib.parse.urlparse(url)
    ext = Path(parsed.path).suffix.lstrip(".")
    return ext or default


def download_result_urls(
    urls: Iterable[str],
    out_dir: Path,
    stem: str,
    *,
    default_ext: str = "mp4",
) -> list[Path]:
    """Download each URL to `<out_dir>/<stem>[-N].<ext>`. Returns saved paths.

    Single URL -> `<stem>.<ext>`. Multiple URLs -> `<stem>-1.<ext>`, ... .
    Extension comes from the URL path when present; otherwise default_ext.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    urls = list(urls)
    saved: list[Path] = []
    for i, url in enumerate(urls):
        ext = _ext_for_url(url, default_ext)
        suffix = "" if len(urls) == 1 else f"-{i + 1}"
        path = out_dir / f"{stem}{suffix}.{ext}"
        download(url, path)
        saved.append(path)
    return saved
