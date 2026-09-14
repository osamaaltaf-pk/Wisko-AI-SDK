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

## Catalogues (public)

`GET` on `https://app.wiskoai.com`, no key needed. Fill your pickers from these and send the ids as job settings. SDK: `client.catalogues.*`.

| Endpoint | Returns | Feeds the setting |
|---|---|---|
| `GET /api/packs` | `{data: {style_id: {id, name, description, preview_gif, render_mode, engine_settings, sound}}}` | `style_id` |
| `GET /api/tts/voices?engine=&lang=` | `{voices: [{id, name, engine, lang, language}], groups, by_language}` | `tts_voice` |
| `GET /api/tts/voices/sample/{voice}` | an audio sample of the voice | |
| `GET /api/music` | `{tracks: [{id, title, mood_tags, duration, preview_url, license}]}` | `music_track` |
| `GET /api/transitions` | `{transitions: [{value, label, seconds}], groups, signature}` | `transition_type`, `transition_pool` |
| `GET /api/entrance-effects` | `{effects: [{value, label, group, sound, text_ok}]}` | `entrance_pool` |
| `GET /api/hand-styles` | `{groups: [{label, assets: [{id, label, preview_url}]}], default}` | `hand_style` |
| `GET /auto/api/visual_effects` | `{effects, sizes, importances, modes, entrances, exits, text_animations}` | `visual_effects` |
| `GET /api/sfx-library` | `{sounds: [{id, label, family, tags, loop}]}` | |
| `GET /auto/api/video_formats` | `{aspects, resolutions, default_aspect, default_resolution, max_resolution}` | `aspect_ratio`, `resolution` |
| `GET /api/caption-styles` | `{styles: [{id, label, blurb, font_family, words_per_beat, ...}], default, positions, highlights, animations, emphasis_modes, fonts, form_fields}` | `caption_style`, `caption_font` |
| `GET /api/caption-styles/{id}/preview?w=360&animated=1` | the style as a looping animated WebP (a PNG with `animated=0`); add any `caption_*` field to preview your overrides | |

## Captions

Word-synced captions over the video, off unless `captions=on`: a few words per beat, the spoken word highlighted, one key word a beat emphasised (numbers, money, words written in the picture), drawn above the drawing hand.

```python
from wisko import Wisko

client = Wisko()
print([s["id"] for s in client.catalogues.caption_styles()["styles"]])
client.catalogues.caption_preview("neon_glow", "neon.webp")      # see how it moves first
job = client.jobs.create(images=["01.png"], narration="This one trick saves $500 every month.",
                         captions="on", caption_style="neon_glow", caption_active_color="#ff3cac")
```

| Field | Values | Default |
|---|---|---|
| `captions` | `on`, `off` | `off` |
| `caption_style` | an id from `GET /api/caption-styles` | `hormozi_bold` |
| `caption_words` | 1–8 words at a time | the style's |
| `caption_position` | `auto`, `bottom`, `middle`, `top` | `bottom` |
| `caption_emphasis` | `auto`, `off` | `auto` |
| `caption_highlight` | `color`, `box`, `karaoke`, `glow`, `scale`, `none` | the style's |
| `caption_animation` | `pop`, `bounce`, `rise`, `fade`, `none` | the style's |
| `caption_font` | a font id from the catalogue | the style's |
| `caption_size` | 0.03–0.2 of the frame height | the style's |
| `caption_bold`, `caption_italic`, `caption_uppercase`, `caption_glow` | `true`, `false` | the style's |
| `caption_color`, `caption_active_color`, `caption_emphasis_color`, `caption_outline_color`, `caption_glow_color`, `caption_box_color` | `#rrggbb` | the style's |
| `caption_outline_width` | 0–0.3 of the text size | the style's |
| `captions_json` | all of the above as one JSON object, plus `emphasis_words` (`{"profit": true}`) | |

Every other job setting (style, voice, music, hand, transitions, effects, sound) is in the Settings Reference of [llms-full.txt](llms-full.txt).

## Web app endpoints

The Wisko web and desktop apps call these with the signed-in session or the licence key. They are not part of `/v1` and may change; build integrations on `/v1`.

```
POST /api/batch/upload                    multipart archive=<zip>; returns a preflight report
POST /api/batch/{id}/start|pause|cancel
GET  /api/batch/{id}/status
GET  /api/batch/{id}/download             all finished clips (zip)
GET  /api/batch/{id}/item/{seq}/download  one clip (409 not finished, 410 file gone)
GET  /api/pipeline/modes                  services each mode uses
GET  /api/pipeline/health                 per-service health and what degrades
GET  /api/providers                       bring-your-own AI key providers
GET  /api/providers/{kind}/keys           keys and status (secrets never returned)
POST /api/providers/{kind}/keys           {api_key, label}
PATCH|DELETE /api/providers/{kind}/keys/{key_id}
GET  /api/providers/usage                 per-key call accounting
GET  /auto/api/jobs/{id}/details          a project's scenes, words, overrides and captions
POST /auto/api/jobs/{id}/scenes/update    Timeline edits: per-scene overrides, overlays, captions (Timeline add-on)
```

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
