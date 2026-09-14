# Wisko Python SDK

Make whiteboard explainer videos with the Wisko Developer API.

```bash
pip install "git+https://github.com/osamaaltaf-pk/Wisko-AI-SDK.git#subdirectory=python"
```

## Get an API key

API keys belong to your Wisko licence and act with its plan. Create one with your licence key (shown once, store it):

```bash
curl -X POST https://app.wiskoai.com/v1/keys \
  -H "X-License-Key: wsk_..." -H "Content-Type: application/json" -d '{"label": "my app"}'
```

List keys with `GET /v1/keys` and revoke one with `DELETE /v1/keys/<key_prefix>`, both with the same header.

## Make a video

```python
from wisko import Wisko

client = Wisko(api_key="wsk_live_...")          # or set WISKO_API_KEY

job = client.jobs.create(
    images=["01.png", "02.png"],                 # one image per scene, in order
    narration=["A black bear finds a bramble.",  # one line per image
               "It picks the ripest berries."],
    style_id="doodle_notes",
    tts_voice="kokoro_af_heart",
)
job = client.jobs.wait(job.id, on_progress=lambda j: print(j.status, j.progress))
client.jobs.download(job.id, "bear.mp4")
```

AI-planned (the plan must include the AI planner):

```python
job = client.jobs.create(prompt="A 60-second explainer on why bees matter to farms.",
                         style_id="doodle_notes", duration=60)
```

## Limits and errors

A job through the API is judged by your plan exactly like one made in the app: screens, images per job, jobs at a time and credits. Each key also has requests per minute and jobs per day (`client.me()` shows them).

| Error | HTTP | When |
|---|---|---|
| `AuthenticationError` | 401 | missing, invalid or revoked key |
| `PlanError` | 402/403 | your plan does not include this |
| `RateLimitError` | 429 | requests/minute, jobs/day or jobs at a time (`retry_after`) |
| `InvalidRequestError` | 400/409 | bad input |
| `NotFoundError` | 404 | not a job of this key |
| `JobFailedError` | — | `wait()` saw the job fail |

The client retries connection errors, 5xx and short rate limits with backoff, and sends an `Idempotency-Key` on every create so a retried create never makes a second job.

## REST reference

| Method | Path | |
|---|---|---|
| POST | `/v1/keys` | create a key (`X-License-Key`) |
| GET | `/v1/keys` | list keys (`X-License-Key`) |
| DELETE | `/v1/keys/{key_prefix}` | revoke (`X-License-Key`) |
| GET | `/v1/me` | plan, screens, limits |
| POST | `/v1/jobs` | multipart: `images` (repeat) + `narration`, or `prompt`; any Agent setting; header `Idempotency-Key` |
| GET | `/v1/jobs` | this key's jobs |
| GET | `/v1/jobs/{id}` | `status` (queued, running, done, failed, cancelled), `progress`, `stages`, `error`, `video_url` |
| GET | `/v1/jobs/{id}/video` | the MP4 |

Authenticate with `Authorization: Bearer wsk_live_...`. Errors are `{"error": {"code": "...", "message": "..."}}`.
