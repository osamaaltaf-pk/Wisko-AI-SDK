"""The client. Polling only (webhooks come later), retries with backoff on
429/5xx/connection errors, an Idempotency-Key on every create so a retried
create never makes a second job."""
from __future__ import annotations

import os
import random
import time
import uuid
from contextlib import ExitStack
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

import requests

from . import errors

DEFAULT_BASE_URL = "https://app.wiskoai.com"
PathLike = Union[str, "os.PathLike[str]"]


@dataclass
class Job:
    id: str
    status: str = "queued"               # queued | running | done | failed | cancelled
    progress: int = 0
    stages: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    video_url: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def finished(self) -> bool:
        return self.status in ("done", "failed", "cancelled")

    @classmethod
    def from_api(cls, d: dict) -> "Job":
        return cls(id=d.get("id", ""), status=d.get("status", "queued"), progress=int(d.get("progress") or 0),
                   stages=dict(d.get("stages") or {}), error=d.get("error"), video_url=d.get("video_url"), raw=d)


class _Transport:
    def __init__(self, api_key: str, base_url: str, timeout: float, max_retries: int,
                 session: Optional[requests.Session] = None):
        if not api_key or not api_key.startswith(("wsk_live_", "wsk_test_")):
            raise errors.AuthenticationError("An API key (wsk_live_...) is required.")
        self.base_url = base_url.rstrip("/")
        self.timeout, self.max_retries = timeout, max_retries
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}",
                                     "User-Agent": "wisko-python/1.0.0"})

    def request(self, method: str, path: str, *, stream: bool = False, **kw) -> requests.Response:
        url = self.base_url + path
        attempt = 0
        while True:
            try:
                resp = self.session.request(method, url, timeout=self.timeout, stream=stream, **kw)
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt >= self.max_retries:
                    raise errors.ServerError(f"Could not reach Wisko: {e}") from e
                self._sleep(attempt, None)
                attempt += 1
                continue
            if resp.status_code < 400:
                return resp
            retry_after = _retry_after(resp)
            retryable = resp.status_code in (429, 502, 503, 504) or resp.status_code >= 500
            # a daily or plan limit will not clear in seconds: do not spin on it
            code = _code(resp)
            if code in ("daily_job_limit", "plan_does_not_allow", "concurrency_limit"):
                retryable = False
            if retryable and attempt < self.max_retries:
                self._sleep(attempt, retry_after)
                attempt += 1
                continue
            try:
                body = resp.json()
            except ValueError:
                body = {"error": {"message": resp.text[:300]}}
            raise errors.from_response(resp.status_code, body, retry_after)

    @staticmethod
    def _sleep(attempt: int, retry_after: Optional[float]) -> None:
        delay = retry_after if retry_after else min(30.0, (2 ** attempt) + random.random())
        time.sleep(delay)


def _retry_after(resp) -> Optional[float]:
    try:
        return float(resp.headers.get("Retry-After"))
    except (TypeError, ValueError):
        return None


def _code(resp) -> str:
    try:
        return ((resp.json() or {}).get("error") or {}).get("code") or ""
    except ValueError:
        return ""


class Jobs:
    def __init__(self, t: _Transport):
        self._t = t

    def create(self, *, images: Sequence[PathLike] = (), narration: Union[str, Iterable[str], None] = None,
               prompt: Optional[str] = None, idempotency_key: Optional[str] = None, **settings: Any) -> Job:
        """Create and start a job.

        Manual: `images` in scene order and `narration` (one line per image, a
        list or a newline-separated string). AI-planned: `prompt` (images are
        optional references). Any Agent setting may be passed as a keyword:
        style_id, tts_voice, aspect_ratio, duration, resolution, ...
        """
        if not prompt and not images:
            raise errors.InvalidRequestError("Pass images with narration, or a prompt.")
        data: Dict[str, Any] = {k: ("true" if v is True else "false" if v is False else str(v))
                                for k, v in settings.items() if v is not None}
        if prompt:
            data["prompt"] = prompt
        if narration is not None:
            data["narration"] = narration if isinstance(narration, str) else "\n".join(narration)
        headers = {"Idempotency-Key": idempotency_key or str(uuid.uuid4())}
        with ExitStack() as stack:
            files = [("images", (os.path.basename(str(p)), stack.enter_context(open(p, "rb"))))
                     for p in images]
            resp = self._t.request("POST", "/v1/jobs", data=data, files=files or None, headers=headers)
        d = resp.json()
        return Job(id=d["id"], status=d.get("status", "queued"), raw=d)

    def get(self, job_id: str) -> Job:
        return Job.from_api(self._t.request("GET", f"/v1/jobs/{job_id}").json())

    def list(self, limit: int = 20) -> List[dict]:
        return self._t.request("GET", "/v1/jobs", params={"limit": limit}).json().get("data", [])

    def wait(self, job_id: str, *, timeout: float = 3 * 3600, poll_interval: float = 5.0,
             on_progress=None) -> Job:
        """Poll until done. Raises JobFailedError on failed/cancelled, TimeoutError on timeout."""
        deadline = time.monotonic() + timeout
        last = -1
        while True:
            job = self.get(job_id)
            if on_progress and job.progress != last:
                on_progress(job)
                last = job.progress
            if job.status == "done":
                return job
            if job.status in ("failed", "cancelled"):
                raise errors.JobFailedError(job.error or f"Job {job_id} {job.status}.", code=job.status,
                                            body=job.raw)
            if time.monotonic() > deadline:
                raise TimeoutError(f"Job {job_id} still {job.status} after {timeout:.0f}s")
            time.sleep(poll_interval)

    def download(self, job_id: str, path: PathLike) -> str:
        """Save the finished MP4 to `path`; returns the path."""
        resp = self._t.request("GET", f"/v1/jobs/{job_id}/video", stream=True)
        tmp = f"{path}.part"
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(1 << 16):
                f.write(chunk)
        os.replace(tmp, path)
        return str(path)


class Wisko:
    """`Wisko(api_key=None, base_url=None)`; the key defaults to WISKO_API_KEY,
    the base URL to WISKO_BASE_URL or https://app.wiskoai.com."""

    def __init__(self, api_key: Optional[str] = None, *, base_url: Optional[str] = None,
                 timeout: float = 120.0, max_retries: int = 3, session: Optional[requests.Session] = None):
        self._t = _Transport(api_key or os.environ.get("WISKO_API_KEY", ""),
                             base_url or os.environ.get("WISKO_BASE_URL", DEFAULT_BASE_URL),
                             timeout, max_retries, session)
        self.jobs = Jobs(self._t)

    def me(self) -> dict:
        """The key's plan, screens and limits."""
        return self._t.request("GET", "/v1/me").json()
