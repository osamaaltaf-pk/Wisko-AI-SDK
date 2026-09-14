"""Wisko Python SDK: whiteboard explainer videos through the Wisko Developer API.

    from wisko import Wisko

    client = Wisko(api_key="wsk_live_...")
    job = client.jobs.create(images=["01.png", "02.png"],
                             narration=["First scene.", "Second scene."],
                             style_id="doodle_notes")
    job = client.jobs.wait(job.id)
    client.jobs.download(job.id, "video.mp4")
"""
from .client import Wisko, Job
from .errors import (WiskoError, AuthenticationError, PlanError, RateLimitError,
                     NotFoundError, InvalidRequestError, JobFailedError, ServerError)

__all__ = ["Wisko", "Job", "WiskoError", "AuthenticationError", "PlanError", "RateLimitError",
           "NotFoundError", "InvalidRequestError", "JobFailedError", "ServerError"]
__version__ = "1.0.0"
