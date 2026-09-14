# Wisko Developer API — REST reference

Base URL: `https://app.wiskoai.com`

All responses are JSON unless noted. Errors always look like:

```json
{"error": {"code": "invalid_request", "message": "Send `images` with `narration`, or a `prompt`."}}
```

## Authentication

| Endpoints | Header |
|---|---|
| `/v1/keys` (create, list, revoke) | `X-License-Key: wsk_...` — your Wisko licence key |
| everything else | `Authorization: Bearer wsk_live_...` — an API key |

Signed in to the dashboard, the **Developers** page (`/settings#developers`) creates, lists and revokes keys without the licence key.

An API key acts with its licence's plan: the same screens, images per job, jobs at a time and credits as the app.

---

## Keys

### Create a key — `POST /v1/keys`

```bash
curl -X POST https://app.wiskoai.com/v1/keys \
  -H "X-License-Key: $WISKO_LICENSE_KEY" -H "Content-Type: application/json" \
  -d '{"label": "production server"}'
```

`201`

```json
{
  "api_key": "wsk_live_...",
  "key_prefix": "wsk_live_ab12cd34",
  "label": "production server",
  "rpm": 60,
  "jobs_per_day": 200,
  "note": "Shown once. Store it now; only its prefix is listed later."
}
```

`402 no_plan` when the licence has no active plan.

### List keys — `GET /v1/keys`

```json
{"data": [{"key_prefix": "wsk_live_ab12cd34", "label": "production server", "created_at": 1789000000.0,
           "last_used_at": 1789003600.0, "revoked_at": null, "rpm": 60, "jobs_per_day": 200}]}
```

### Revoke a key — `DELETE /v1/keys/{key_prefix}`

`200 {"revoked": "wsk_live_ab12cd34"}` · `404 not_found`

---

## Account

### `GET /v1/me`

```json
{
  "key_prefix": "wsk_live_ab12cd34",
  "plan": "cloud_payg",
  "features": {"studio": true, "batch": true, "agent": true, "auto_jobs": true, "manual_jobs": true},
  "limits": {"images_per_job": 200, "concurrent_jobs": 2},
  "rpm": 60,
  "jobs_per_day": 200
}
```

`rpm` / `jobs_per_day` of `null` mean unlimited.

---

## Jobs

### Create and start a job — `POST /v1/jobs`

`multipart/form-data`. Header `Idempotency-Key: <any unique string>` is strongly recommended.

**Manual job**

| Field | |
|---|---|
| `images` | repeat once per image, **in scene order** (png, jpg, webp, bmp) |
| `narration` | newline-separated text, **exactly one line per image** |

**AI-planned job**

| Field | |
|---|---|
| `prompt` | what the video is about |
| `images` | optional reference images |
| `duration` | target seconds (15–1800); the narration decides the final length |

**Common settings** (all optional; the app's defaults apply otherwise)

| Field | Example | |
|---|---|---|
| `style_id` | `doodle_notes` | drawing style |
| `tts_voice` | `kokoro_af_heart` | narration voice |
| `tts_language` | `en` | narration language |
| `aspect_ratio` | `16:9`, `9:16`, `1:1` | output shape |
| `resolution` | `720p`, `1080p` | output size |
| `draw_hand` | `true` / `false` | show the drawing hand |
| `end_hold_seconds` | `1.5` | hold on the last frame |

Any other setting available on the app's Agent screen may be sent by the same name.

```bash
curl -X POST https://app.wiskoai.com/v1/jobs \
  -H "Authorization: Bearer $WISKO_API_KEY" \
  -H "Idempotency-Key: $(uuidgen)" \
  -F images=@01.png -F images=@02.png \
  -F $'narration=A black bear finds a bramble.\nIt picks the ripest berries.' \
  -F style_id=doodle_notes
```

`202`

```json
{"id": "2aa93429-cfa0", "status": "queued", "status_url": "/v1/jobs/2aa93429-cfa0"}
```

Replaying the same `Idempotency-Key` returns `200` with `"idempotent_replay": true` and the original `id`.

Refusals (nothing is queued or charged):

| HTTP | code | When |
|---|---|---|
| 400 | `invalid_request` | no images and no prompt; narration rows ≠ images; more images than the plan allows; a needed provider key is missing (the message names it) |
| 400 | `unsupported_image` | not png / jpg / webp / bmp |
| 402 | `plan_does_not_allow` | the plan does not include this kind of job, or not enough credits |
| 429 | `concurrency_limit` | jobs at a time for the plan |
| 429 | `daily_job_limit` | this key's jobs per day (`Retry-After`) |
| 4xx | `job_not_started` | created but could not start (e.g. credits); the body carries `id` |

### Job status — `GET /v1/jobs/{id}`

```json
{
  "id": "2aa93429-cfa0",
  "status": "running",
  "progress": 60,
  "stages": {"plan": "done", "imagegen": "done", "tts": "done", "vlm": "running", "render": "pending"},
  "error": null,
  "video_url": null
}
```

`status`: `queued` · `running` · `done` · `failed` · `cancelled`. When `done`, `video_url` is `/v1/jobs/{id}/video`.

Poll every few seconds; the SDK's `jobs.wait()` does this for you.

### List jobs — `GET /v1/jobs?limit=20`

This key's jobs, newest first (`limit` 1–100).

### Download the video — `GET /v1/jobs/{id}/video`

The MP4 (`Content-Type: video/mp4`). `409 not_ready` until the job is done.

---

## Errors

| HTTP | code | Meaning |
|---|---|---|
| 400 | `invalid_request` | bad or missing input |
| 401 | `invalid_api_key` | missing, invalid or revoked API key |
| 401 | `licence_required` | `/v1/keys` needs `X-License-Key` |
| 402 | `no_plan` / `plan_does_not_allow` | plan or credits |
| 404 | `not_found` | not a job of this key |
| 409 | `not_ready` | video not finished |
| 429 | `rate_limited` | requests per minute for this key (`Retry-After`) |
| 429 | `daily_job_limit` / `concurrency_limit` | job limits |
| 503 | `keys_unavailable` / `auth_unavailable` | temporary; retry with backoff |

## Rate limits

- **Requests per minute** and **jobs per day** are set per API key (see `GET /v1/me`).
- **Jobs at a time** and **images per job** come from the plan.
- Over a limit the API answers `429` immediately. There is no queue.

## Billing

Cloud jobs spend **credits** from the licence's balance (packs of $20 / $100 / $500, 1 credit = $1). Credits are reserved from the narration estimate when the job starts and settled on the finished video's real length; failed jobs are refunded. Desktop-plan licences render on your own machine and are not charged per video.
