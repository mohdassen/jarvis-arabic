#!/bin/bash
set -e

STATE_DIR="${OPENCLAW_STATE_DIR:-/data/.openclaw}"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"
SEED_DIR="/opt/jarvis-workspace"
PLUGIN_SEED_DIR="/opt/openclaw-plugin-seed"

# Recovery first: previous deploys copied large runtime assets into the small
# persistent Railway volume and filled it. These paths contain reproducible
# binaries/caches only; OAuth credentials, OpenClaw config, workspace and memory
# are intentionally left untouched.
rm -rf /data/.linuxbrew 2>/dev/null || true
rm -rf "$STATE_DIR/npm/projects" 2>/dev/null || true
rm -rf "$STATE_DIR/npm/.cache" "$STATE_DIR/cache" 2>/dev/null || true

mkdir -p /data "$STATE_DIR" "$WORKSPACE_DIR" "$WORKSPACE_DIR/memory"
chown -R openclaw:openclaw /data
chmod 700 /data

# Keep Homebrew in the immutable container image instead of duplicating it on
# the persistent volume. It can be recreated on every image build and should
# not consume /data capacity.

for f in AGENTS.md SOUL.md IDENTITY.md USER.md MEMORY.md; do
  if [ ! -f "$WORKSPACE_DIR/$f" ] && [ -f "$SEED_DIR/$f" ]; then
    cp "$SEED_DIR/$f" "$WORKSPACE_DIR/$f"
  fi
done

# Expose the prebuilt plugin payload from the image without copying hundreds of
# MB into /data. A symlink is enough because the image remains mounted for the
# life of the container.
if [ -d "$PLUGIN_SEED_DIR/npm" ]; then
  rm -rf "$STATE_DIR/npm"
  ln -s "$PLUGIN_SEED_DIR/npm" "$STATE_DIR/npm"
fi

chown -R openclaw:openclaw "$STATE_DIR" "$WORKSPACE_DIR"

exec gosu openclaw node src/server.js
