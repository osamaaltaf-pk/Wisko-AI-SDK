"""AI-planned video from a prompt.

    export WISKO_API_KEY=wsk_live_...
    python ai_planned_video.py "Why bees matter to farms"
"""
import sys

from wisko import Wisko, RateLimitError, WiskoError

prompt = " ".join(sys.argv[1:]) or "A 60-second explainer on why bees matter to farms."
client = Wisko()

print("plan:", client.me().get("plan"))
try:
    job = client.jobs.create(prompt=prompt, style_id="doodle_notes", duration=60)
    job = client.jobs.wait(job.id, on_progress=lambda j: print(f"  {j.status} {j.progress}% {j.stages}"))
    print("saved", client.jobs.download(job.id, "explainer.mp4"))
except RateLimitError as e:
    print(f"Limit reached, retry after {e.retry_after}s:", e)
except WiskoError as e:
    print("Wisko error:", e)
    sys.exit(1)
