# Wisko AI — Developer API & SDK

**Wisko** turns images and narration — or a single prompt — into hand-drawn whiteboard explainer videos. A hand draws each element as the narrator mentions it, text is written letter by letter, and the camera follows along.

This repository holds the public pieces for developers:

| Path | What |
|---|---|
| [`python/`](python/) | The official Python SDK (`wisko`) |
| [`docs/API.md`](docs/API.md) | REST API reference (every public endpoint, fields, errors, limits) |
| [`examples/`](examples/) | Runnable examples: manual video, AI-planned video, raw `curl` |

Website: [wiskoai.com](https://wiskoai.com) · App: [app.wiskoai.com](https://app.wiskoai.com)

---

## What the platform does

| Mode | You send | You get |
|---|---|---|
| **Manual** | Images in scene order + one narration line per image | A video where each image is drawn in sync with its line |
| **AI-planned (Agent)** | A prompt (images optional, used as references) | Wisko plans the scenes, generates the art, narrates and renders |

Every job — from the web app, the desktop app, a batch or the API — goes through the same pipeline and the same plan rules:

1. **Plan** (AI-planned jobs) — the script and scenes are written.
2. **Images** — generated (AI-planned) or yours (manual).
3. **Narration** — text-to-speech in the voice you choose; the narration decides the video's length.
4. **Vision** — each element and its words are found, so drawing lands on the right cue.
5. **Render** — hand drawing, text reveal, camera, sound, final MP4.

## Plans and billing

- **Desktop plans** (Solo, Solo Batch, Auto) and add-ons (Shorts, Short-Batch, Timeline) are monthly licences.
- **Cloud** has no subscription. Videos are paid with **credits** bought in packs of **$20, $100 or $500** (1 credit = $1, credits never expire):
  - **Wisko Compute** — from 1 credit per video, priced by the finished narration's length (up to 15 / 25 / 50 minutes), up to 200 images per video.
  - **BYO GCP** — half a credit per video of any length, on workers in your own Google Cloud.
  - **Shorts** — a tenth of a credit each.
- Credits are reserved from an estimate when a job starts and settled on the finished video's real length; a failed job is refunded in full.
- **Enterprise / custom** plans (e.g. 1000 images per job, unlimited jobs per day) are set up by Wisko — [contact us](https://wiskoai.com/contact).

**Bring your own AI keys.** Model calls (planning, image generation, vision, paid voices) run on *your* provider keys, added once in the app under **Settings → API keys** (Google AI Studio / Vertex, OpenAI, Anthropic, fal, Replicate, ElevenLabs, …). A job that needs a key you have not added is refused before it starts, with the missing step named. Subscription plans that include Wisko-managed keys say so on the plan.

## Quick start (Python)

```bash
pip install "git+https://github.com/osamaaltaf-pk/Wisko-AI-SDK.git#subdirectory=python"
```

1. Get a Wisko licence key (`wsk_...`) from the app or your purchase email.
2. Create an API key — shown **once**, store it safely. Easiest: sign in at [app.wiskoai.com/settings#developers](https://app.wiskoai.com/settings#developers) → **Developers** → **Create API key**. Or with your licence key:

   ```bash
   curl -X POST https://app.wiskoai.com/v1/keys \
     -H "X-License-Key: $WISKO_LICENSE_KEY" \
     -H "Content-Type: application/json" \
     -d '{"label": "my app"}'
   ```

3. Make a video:

```python
from wisko import Wisko

client = Wisko(api_key="wsk_live_...")            # or set WISKO_API_KEY

job = client.jobs.create(
    images=["01.png", "02.png"],                   # one image per scene, in order
    narration=["A black bear finds a bramble.",    # exactly one line per image
               "It picks the ripest berries."],
    style_id="doodle_notes",
    tts_voice="kokoro_af_heart",
)
job = client.jobs.wait(job.id, on_progress=lambda j: print(j.status, j.progress))
client.jobs.download(job.id, "bear.mp4")
```

AI-planned:

```python
job = client.jobs.create(prompt="A 60-second explainer on why bees matter to farms.",
                         style_id="doodle_notes", duration=60)
```

More in [`python/README.md`](python/README.md) and [`examples/`](examples/).

## Rules every job follows

- **Images per job** are capped by your plan (`GET /v1/me` → `limits.images_per_job`).
- **Manual jobs:** narration rows must equal the number of images (a blank row in the middle is a silent scene; trailing blank lines are ignored). A mismatch is refused before anything is queued or charged.
- **Jobs at a time**, **requests per minute** and **jobs per day** are limited per plan and per API key; over the limit you get `429` with `Retry-After` — nothing is queued.
- **Idempotency:** send an `Idempotency-Key` header on create (the SDK always does); a retried create returns the original job instead of making a second one.

## Security

- Never put an API key in client-side code or a public repository. Use environment variables.
- Keys can be listed and revoked on the dashboard's **Developers** page, or with your licence key (`GET /v1/keys`, `DELETE /v1/keys/{key_prefix}`).
- Only a key's prefix is ever shown after creation.
- Report a security issue to **privacy@wiskoai.com**.

## Support

- Docs: [`docs/API.md`](docs/API.md)
- Email: **support@wiskoai.com**
- Issues with the SDK: open a GitHub issue in this repository.

---

© Wisko AI. The SDK is provided for use with the Wisko service; see [`python/pyproject.toml`](python/pyproject.toml) for licence terms.
