#!/bin/bash
set -e

STATE_DIR="${OPENCLAW_STATE_DIR:-/data/.openclaw}"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"
SEED_DIR="/opt/jarvis-workspace"
CODEX_PLUGIN_DIR="/opt/codex-runtime/node_modules/@openclaw/codex"
PAIR_REQUEST_ID="6b3771f1-1d91-41d7-bfc6-1a543a0ab5a8"

rm -rf /data/.linuxbrew 2>/dev/null || true
rm -rf "$STATE_DIR/npm/projects" 2>/dev/null || true
rm -rf "$STATE_DIR/npm/.cache" "$STATE_DIR/cache" 2>/dev/null || true

mkdir -p /data "$STATE_DIR" "$WORKSPACE_DIR" "$WORKSPACE_DIR/memory"
chown -R openclaw:openclaw /data
chmod 700 /data

for f in AGENTS.md SOUL.md IDENTITY.md USER.md MEMORY.md; do
  if [ ! -f "$WORKSPACE_DIR/$f" ] && [ -f "$SEED_DIR/$f" ]; then
    cp "$SEED_DIR/$f" "$WORKSPACE_DIR/$f"
  fi
done

if [ -L "$STATE_DIR/npm" ]; then
  rm -f "$STATE_DIR/npm"
fi
mkdir -p "$STATE_DIR/npm"

if [ -d "$CODEX_PLUGIN_DIR" ] && [ -f "$CODEX_PLUGIN_DIR/package.json" ]; then
  echo "[jarvis] registering Codex plugin from $CODEX_PLUGIN_DIR"
  gosu openclaw env OPENCLAW_STATE_DIR="$STATE_DIR" OPENCLAW_WORKSPACE_DIR="$WORKSPACE_DIR" \
    openclaw plugins install --link "$CODEX_PLUGIN_DIR" --force --accept-capabilities

  gosu openclaw env OPENCLAW_STATE_DIR="$STATE_DIR" OPENCLAW_WORKSPACE_DIR="$WORKSPACE_DIR" \
    openclaw plugins enable codex --accept-capabilities
else
  echo "[jarvis] ERROR: Codex runtime package is missing at $CODEX_PLUGIN_DIR" >&2
  exit 1
fi

chown -R openclaw:openclaw "$STATE_DIR" "$WORKSPACE_DIR"

# One-time approval of Abu Yamen's currently pending browser pairing request.
# Runs after the wrapper has had enough time to start the local Gateway.
(
  sleep 35
  for attempt in 1 2 3; do
    echo "[jarvis] approving browser pairing request $PAIR_REQUEST_ID (attempt $attempt)"
    if gosu openclaw env OPENCLAW_STATE_DIR="$STATE_DIR" OPENCLAW_WORKSPACE_DIR="$WORKSPACE_DIR" \
      openclaw devices approve "$PAIR_REQUEST_ID"; then
      echo "[jarvis] browser pairing approved"
      exit 0
    fi
    sleep 8
  done
  echo "[jarvis] browser pairing approval did not complete"
) &

exec gosu openclaw node src/server.js
