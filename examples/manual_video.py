"""Manual video: your images, one narration line per image.

    export WISKO_API_KEY=wsk_live_...
    python manual_video.py scene1.png scene2.png
"""
import sys

from wisko import Wisko, WiskoError

images = sys.argv[1:] or ["01.png", "02.png"]
narration = [
    "A black bear finds a bramble at the edge of the forest.",
    "It picks the ripest berries, one careful paw at a time.",
][: len(images)]

client = Wisko()                                  # reads WISKO_API_KEY

try:
    job = client.jobs.create(images=images, narration=narration,
                             style_id="doodle_notes", aspect_ratio="16:9")
    print("job", job.id)
    job = client.jobs.wait(job.id, on_progress=lambda j: print(f"  {j.status} {j.progress}%"))
    print("saved", client.jobs.download(job.id, f"{job.id}.mp4"))
except WiskoError as e:
    print("Wisko error:", e)
    sys.exit(1)
