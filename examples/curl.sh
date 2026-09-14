#!/usr/bin/env bash
# The whole flow with curl and jq. Needs WISKO_API_KEY.
set -euo pipefail
BASE=${WISKO_BASE_URL:-https://app.wiskoai.com}
AUTH="Authorization: Bearer ${WISKO_API_KEY:?set WISKO_API_KEY}"

curl -s "$BASE/v1/me" -H "$AUTH" | jq .

JOB=$(curl -s -X POST "$BASE/v1/jobs" -H "$AUTH" -H "Idempotency-Key: $(date +%s)-$RANDOM" \
  -F images=@01.png -F images=@02.png \
  -F $'narration=A black bear finds a bramble.\nIt picks the ripest berries.' \
  -F style_id=doodle_notes | jq -r .id)
echo "job $JOB"

while true; do
  S=$(curl -s "$BASE/v1/jobs/$JOB" -H "$AUTH")
  STATUS=$(echo "$S" | jq -r .status)
  echo "$STATUS $(echo "$S" | jq -r .progress)%"
  case "$STATUS" in done) break ;; failed|cancelled) echo "$S" | jq .; exit 1 ;; esac
  sleep 5
done

curl -s -L "$BASE/v1/jobs/$JOB/video" -H "$AUTH" -o "$JOB.mp4"
echo "saved $JOB.mp4"
