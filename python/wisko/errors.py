"""Typed errors. Every API error body is {"error": {"code", "message"}}."""
from __future__ import annotations

from typing import Optional


class WiskoError(Exception):
    def __init__(self, message: str, *, status: Optional[int] = None, code: str = "",
                 retry_after: Optional[float] = None, body: Optional[dict] = None):
        super().__init__(message)
        self.message, self.status, self.code = message, status, code
        self.retry_after, self.body = retry_after, body or {}

    def __str__(self):
        head = f"[{self.status} {self.code}] " if self.status else ""
        return head + self.message


class AuthenticationError(WiskoError):
    """401: missing, invalid or revoked key."""


class PlanError(WiskoError):
    """402/403: the licence's plan does not allow this (or has no active plan)."""


class RateLimitError(WiskoError):
    """429: requests per minute, jobs per day, or jobs at a time. See retry_after."""


class NotFoundError(WiskoError):
    """404."""


class InvalidRequestError(WiskoError):
    """400/409/413/422."""


class JobFailedError(WiskoError):
    """wait(): the job ended failed or cancelled."""


class ServerError(WiskoError):
    """5xx after retries."""


def from_response(status: int, body: dict, retry_after: Optional[float]) -> WiskoError:
    err = (body or {}).get("error") or {}
    msg = err.get("message") or f"HTTP {status}"
    code = err.get("code") or ""
    kw = dict(status=status, code=code, retry_after=retry_after, body=body)
    if status == 401:
        return AuthenticationError(msg, **kw)
    if status in (402, 403):
        return PlanError(msg, **kw)
    if status == 429:
        return RateLimitError(msg, **kw)
    if status == 404:
        return NotFoundError(msg, **kw)
    if 400 <= status < 500:
        return InvalidRequestError(msg, **kw)
    return ServerError(msg, **kw)
