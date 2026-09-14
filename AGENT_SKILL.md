---
name: wisko-video
description: Build products that make narrated, hand-drawn whiteboard videos with the Wisko AI Developer API. Use when a user wants to generate explainer, course, marketing or social videos from images and a script or from a prompt, or wants to add Wisko video generation to an app, backend, automation or agent.
---

# Wisko video generation

Wisko turns images plus narration, or a prompt, into a narrated whiteboard video (MP4). You call a REST API with an API key; Wisko renders on its workers; you poll and download.

Full reference (read it when you need a setting, endpoint or error you are unsure of): https://wiskoai.com/llms-full.txt

## Before you start

1. **API key.** The user creates one at https://app.wiskoai.com/settings#developers → Developers → Create API key. It looks like `wsk_live_...`. Read it from the environment variable `WISKO_API_KEY`. Never print it, log it, commit it or put it in client-side code.
2. **Provider keys.** Wisko runs model calls on the user's own AI provider keys, added in the dashboard under Settings → Providers. If a create call returns `400` naming a missing key (script & planning, image generation, vision), tell the user which key to add. Do not try to work around it.
3. **Plan.** `GET /v1/me` shows what the plan allows: `features.agent` (AI-planned jobs), `features.manual_jobs`, `limits.images_per_job`, `limits.concurrent_jobs`. Check it once before designing a flow.

## Decide the kind of job

| The user has | Use | Send |
|---|---|---|
| Images and a script | Manual job | `images` in scene order + `narration` with exactly one line per image |
| Only an idea or topic | AI-planned job | `prompt` (+ optional `duration` target in seconds, 15–1800) |

Manual job rules, checked before anything is charged:
- The number of narration lines must equal the number of images. Split the script into one line per image yourself; do not send a paragraph.
- Do not send more images than `limits.images_per_job`.
- Images must be png, jpg, webp or bmp.

## Make a video

Python SDK (preferred):

```bash
pip install "git+https://github.com/osamaaltaf-pk/Wisko-AI-SDK.git#subdirectory=python"
```

```python
from wisko import Wisko, RateLimitError, JobFailedError

client = Wisko()  # WISKO_API_KEY
job = client.jobs.create(
    images=["01.png", "02.png"],
    narration=["First scene line.", "Second scene line."],
    style_id="doodle_notes",
)
job = client.jobs.wait(job.id)            # polls; raises JobFailedError on failure
client.jobs.download(job.id, "video.mp4")
```

REST, any language:

```
POST https://app.wiskoai.com/v1/jobs          multipart/form-data
  Authorization: Bearer $WISKO_API_KEY
  Idempotency-Key: <uuid>                      always send one
  images=@01.png  images=@02.png  narration="line 1\nline 2"  style_id=doodle_notes
→ 202 {"id": "...", "status": "queued"}

GET https://app.wiskoai.com/v1/jobs/{id}      poll every 5 s
→ {"status": "queued|running|done|failed|cancelled", "progress": 0-100, "stages": {...}, "error": null}

GET https://app.wiskoai.com/v1/jobs/{id}/video   when status is done → MP4
```

A render takes minutes, not seconds. In a web app, create the job in a request, then poll from a background worker or a status endpoint of your own; never hold the user's HTTP request open until the video is done.

## Choose settings from live catalogues

Never invent ids. Fetch these public lists (no key) and pick from them:

| Need | Endpoint | Setting |
|---|---|---|
| Visual style | `GET https://app.wiskoai.com/api/packs` → keys of `data` | `style_id` |
| Voice | `GET https://app.wiskoai.com/api/tts/voices` → `voices[].id` | `tts_voice` |
| Music | `GET https://app.wiskoai.com/api/music` → `tracks[].id` | `music_track` |
| Scene transition | `GET https://app.wiskoai.com/api/transitions` → `transitions[].value` | `transition_type` |
| Drawing hand | `GET https://app.wiskoai.com/api/hand-styles` → `groups[].assets[].id` | `hand_style` |
| Output formats | `GET https://app.wiskoai.com/auto/api/video_formats` | `aspect_ratio`, `resolution` |

Common settings: `aspect_ratio` (`16:9`, `9:16`, `1:1`...), `resolution` (`720p`, `1080p`, `1440p`), `draw_hand` (`true`/`false`), `sfx_density` (`light`, `standard`, `rich`), `music_gain` (`subtle`, `normal`), `visual_effects` (`auto`, `off`), `tts_enabled` (`false` for a silent video). Everything else: Settings Reference in https://wiskoai.com/llms-full.txt. Omitted settings use the style's defaults; only send what the user asked to change.

## Handle errors

Error body: `{"error": {"code": "...", "message": "..."}}`.

| Status | Do |
|---|---|
| 400 `invalid_request` | Read the message: fix narration/image count, image limit, or ask the user to add the named provider key. Do not retry unchanged. |
| 401 | The API key is missing, wrong or revoked. Ask the user for a valid key. |
| 402 / 403 | The plan does not allow this job or credits ran out. Tell the user; link https://wiskoai.com/pricing. |
| 404 | Not a job of this key. |
| 409 `not_ready` | Keep polling. |
| 429 | Wait `Retry-After` seconds, then retry. Do not loop faster. |
| 5xx | Retry with exponential backoff (the SDK does this). |

Reuse the same `Idempotency-Key` when retrying a create, so a retry never makes two videos.

## Costs to tell users about

Cloud videos spend credits (1 credit = $1, packs of $20/$100/$500): 1 credit for a video up to 15 minutes, 2 up to 25, 3 up to 50; half a credit on BYO GCP; a tenth of a credit per Short. The narration's real length decides the price; failed jobs are refunded. Estimate before bulk runs and confirm with the user.

## Not available through the API yet

Cancel, webhooks, batches, Shorts, per-scene settings and Timeline editing (overlays, per-scene voice/effects/camera, re-render one scene), and uploading a plan, sound direction, narration audio or music with a job. These exist in the Wisko web app. If the user needs them, say so plainly instead of approximating with unsupported fields.
