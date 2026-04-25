#!/usr/bin/env bash
# story-cron.sh — Trigger a ContentPipeline workflow run via the Creepy Brain API.
#
# Usage:
#   ./story-cron.sh [PREMISE]
#
# Environment variables (all optional — have defaults):
#   BRAIN_URL        Base URL of the Creepy Brain service  (default: http://localhost:8006)
#   VOICE_NAME       Voice to use for TTS                  (default: old_man_low.wav)
#   TARGET_WORDS     Target story word count                (default: 5000)
#   GENERATE_IMAGES  true/false                             (default: false)
#   STITCH_VIDEO     true/false                             (default: false)
#   OUTPUT_DIR       Directory for run logs                 (default: scripts/output)
#
# Cron example (trigger a new story every day at 03:00):
#   0 3 * * * /path/to/chatterbox-tts-lite/scripts/story-cron.sh "A ghost story set in Victorian London" >> /var/log/story-cron.log 2>&1

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
BRAIN_URL="${BRAIN_URL:-http://localhost:8006}"
VOICE_NAME="${VOICE_NAME:-old_man_low.wav}"
TARGET_WORDS="${TARGET_WORDS:-5000}"
GENERATE_IMAGES="${GENERATE_IMAGES:-false}"
STITCH_VIDEO="${STITCH_VIDEO:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${SCRIPT_DIR}/output}"

# ── Premise ───────────────────────────────────────────────────────────────────
PREMISE="${1:-}"
if [[ -z "$PREMISE" ]]; then
    echo "ERROR: no premise provided. Pass it as the first argument." >&2
    echo "Usage: $0 \"<story premise>\"" >&2
    exit 1
fi

# ── Validate boolean inputs ───────────────────────────────────────────────────
if [[ "$GENERATE_IMAGES" != "true" && "$GENERATE_IMAGES" != "false" ]]; then
    echo "ERROR: GENERATE_IMAGES must be 'true' or 'false' (got: '${GENERATE_IMAGES}')" >&2
    exit 1
fi
if [[ "$STITCH_VIDEO" != "true" && "$STITCH_VIDEO" != "false" ]]; then
    echo "ERROR: STITCH_VIDEO must be 'true' or 'false' (got: '${STITCH_VIDEO}')" >&2
    exit 1
fi
if ! [[ "$TARGET_WORDS" =~ ^[0-9]+$ ]]; then
    echo "ERROR: TARGET_WORDS must be a positive integer (got: '${TARGET_WORDS}')" >&2
    exit 1
fi

# ── Ensure output directory exists ────────────────────────────────────────────
mkdir -p "$OUTPUT_DIR"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="${OUTPUT_DIR}/run-${TIMESTAMP}.json"

echo "[${TIMESTAMP}] Triggering story workflow..."
echo "  Premise      : ${PREMISE}"
echo "  Voice        : ${VOICE_NAME}"
echo "  Target words : ${TARGET_WORDS}"
echo "  Images       : ${GENERATE_IMAGES}"
echo "  Stitch video : ${STITCH_VIDEO}"
echo "  Brain URL    : ${BRAIN_URL}"

# ── Preflight: skip if a workflow is already running or pending ───────────────
ACTIVE_COUNT="$(
    curl --silent --fail \
        "${BRAIN_URL}/api/workflows?status=running&limit=1" \
    | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"
)" || ACTIVE_COUNT=0

if [[ "$ACTIVE_COUNT" -gt 0 ]]; then
    echo "[${TIMESTAMP}] Skipping: a workflow is already running. Will retry next scheduled run."
    exit 0
fi

# ── Build JSON payload via Python (safe encoding, no injection risk) ──────────
PAYLOAD="$(python3 - <<'PYEOF'
import json, os, sys

premise        = os.environ["_PREMISE"]
voice_name     = os.environ["_VOICE_NAME"]
target_words   = int(os.environ["_TARGET_WORDS"])
generate_imgs  = os.environ["_GENERATE_IMAGES"] == "true"
stitch_video   = os.environ["_STITCH_VIDEO"] == "true"

print(json.dumps({
    "premise":         premise,
    "voice_name":      voice_name,
    "target_word_count": target_words,
    "generate_images": generate_imgs,
    "stitch_video":    stitch_video,
}))
PYEOF
)" \
    _PREMISE="$PREMISE" \
    _VOICE_NAME="$VOICE_NAME" \
    _TARGET_WORDS="$TARGET_WORDS" \
    _GENERATE_IMAGES="$GENERATE_IMAGES" \
    _STITCH_VIDEO="$STITCH_VIDEO"

# ── Trigger workflow ───────────────────────────────────────────────────────────
HTTP_RESPONSE="$(
    curl --silent --show-error --write-out "\nHTTP_STATUS:%{http_code}" \
        --request POST \
        --url "${BRAIN_URL}/api/workflows" \
        --header "Content-Type: application/json" \
        --data "$PAYLOAD"
)"

BODY="$(echo "$HTTP_RESPONSE" | sed -e '/^HTTP_STATUS:/d')"
HTTP_STATUS="$(echo "$HTTP_RESPONSE" | grep '^HTTP_STATUS:' | cut -d: -f2)"

# ── Write log ─────────────────────────────────────────────────────────────────
printf '%s\n' "$BODY" > "$LOG_FILE"
echo "[${TIMESTAMP}] HTTP ${HTTP_STATUS} — response saved to ${LOG_FILE}"

# ── Exit code ─────────────----------------------------------------------------------------
if [[ "$HTTP_STATUS" -ge 200 && "$HTTP_STATUS" -lt 300 ]]; then
    WORKFLOW_ID="$(echo "$BODY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id','?'))")"
    echo "[${TIMESTAMP}] Workflow triggered: ${WORKFLOW_ID}"
    exit 0
else
    echo "ERROR: unexpected HTTP status ${HTTP_STATUS}" >&2
    echo "$BODY" >&2
    exit 1
fi
