#!/bin/bash
set -e

STATE_DIR="${OPENCLAW_STATE_DIR:-/data/.openclaw}"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"
SEED_DIR="/opt/jarvis-workspace"
PLUGIN_SEED_DIR="/opt/openclaw-plugin-seed"

# Recovery first: remove only reproducible caches/assets that previously filled
# the small Railway volume. Preserve config, OAuth credentials, sessions,
# workspace and memory.
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

# Older recovery logic exposed the whole npm tree through a symlink. Remove
# that legacy link if present. OpenClaw needs an install record, not only files.
if [ -L "$STATE_DIR/npm" ]; then
  rm -f "$STATE_DIR/npm"
fi
mkdir -p "$STATE_DIR/npm"

# The official Codex plugin is prebuilt into the immutable image. Register it
# with OpenClaw as a linked local plugin so the install metadata is persisted in
# /data while the large plugin payload stays in the image and consumes no
# persistent-volume capacity.
CODEX_PLUGIN_DIR="$(find "$PLUGIN_SEED_DIR" -type f -name openclaw.plugin.json -print 2>/dev/null | head -n 1 | xargs -r dirname)"
if [ -n "$CODEX_PLUGIN_DIR" ] && [ -d "$CODEX_PLUGIN_DIR" ]; then
  if ! gosu openclaw env \
      OPENCLAW_STATE_DIR="$STATE_DIR" \
      OPENCLAW_WORKSPACE_DIR="$WORKSPACE_DIR" \
      openclaw plugins inspect codex --json >/tmp/codex-inspect.json 2>/dev/null; then
    echo "[jarvis] registering Codex plugin from $CODEX_PLUGIN_DIR"
    gosu openclaw env \
      OPENCLAW_STATE_DIR="$STATE_DIR" \
      OPENCLAW_WORKSPACE_DIR="$WORKSPACE_DIR" \
      openclaw plugins install --link "$CODEX_PLUGIN_DIR" --force
  fi

  # Explicitly enable it. This is idempotent and keeps the existing config.
  gosu openclaw env \
    OPENCLAW_STATE_DIR="$STATE_DIR" \
    OPENCLAW_WORKSPACE_DIR="$WORKSPACE_DIR" \
    openclaw plugins enable codex >/tmp/codex-enable.log 2>&1 || {
      cat /tmp/codex-enable.log >&2 || true
      exit 1
    }
else
  echo "[jarvis] ERROR: prebuilt Codex plugin directory not found" >&2
  exit 1
fi

chown -R openclaw:openclaw "$STATE_DIR" "$WORKSPACE_DIR"

exec gosu openclaw node src/server.js
