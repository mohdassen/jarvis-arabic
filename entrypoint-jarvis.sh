#!/bin/bash
set -e

STATE_DIR="${OPENCLAW_STATE_DIR:-/data/.openclaw}"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"
SEED_DIR="/opt/jarvis-workspace"
CODEX_PLUGIN_DIR="/opt/codex-plugin"

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

# Remove the legacy npm-tree symlink from earlier recovery attempts.
if [ -L "$STATE_DIR/npm" ]; then
  rm -f "$STATE_DIR/npm"
fi
mkdir -p "$STATE_DIR/npm"

# Codex is resolved to this stable path at Docker build time. Register it as a
# linked plugin on every container start; --force keeps this idempotent while
# persisting only lightweight install metadata in /data.
if [ -d "$CODEX_PLUGIN_DIR" ] && [ -f "$CODEX_PLUGIN_DIR/package.json" ]; then
  echo "[jarvis] registering Codex plugin from $CODEX_PLUGIN_DIR"
  gosu openclaw env \
    OPENCLAW_STATE_DIR="$STATE_DIR" \
    OPENCLAW_WORKSPACE_DIR="$WORKSPACE_DIR" \
    openclaw plugins install --link "$CODEX_PLUGIN_DIR" --force

  gosu openclaw env \
    OPENCLAW_STATE_DIR="$STATE_DIR" \
    OPENCLAW_WORKSPACE_DIR="$WORKSPACE_DIR" \
    openclaw plugins enable codex >/tmp/codex-enable.log 2>&1 || {
      cat /tmp/codex-enable.log >&2 || true
      exit 1
    }
else
  echo "[jarvis] ERROR: normalized Codex plugin path is missing" >&2
  exit 1
fi

chown -R openclaw:openclaw "$STATE_DIR" "$WORKSPACE_DIR"

exec gosu openclaw node src/server.js
