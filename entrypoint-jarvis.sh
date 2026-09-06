#!/bin/bash
set -e

STATE_DIR="${OPENCLAW_STATE_DIR:-/data/.openclaw}"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"
SEED_DIR="/opt/jarvis-workspace"
PLUGIN_SEED_DIR="/opt/openclaw-plugin-seed"

mkdir -p /data "$STATE_DIR" "$WORKSPACE_DIR" "$WORKSPACE_DIR/memory"
chown -R openclaw:openclaw /data
chmod 700 /data

if [ ! -d /data/.linuxbrew ]; then
  cp -a /home/linuxbrew/.linuxbrew /data/.linuxbrew
fi
rm -rf /home/linuxbrew/.linuxbrew
ln -sfn /data/.linuxbrew /home/linuxbrew/.linuxbrew

for f in AGENTS.md SOUL.md IDENTITY.md USER.md MEMORY.md; do
  if [ ! -f "$WORKSPACE_DIR/$f" ] && [ -f "$SEED_DIR/$f" ]; then
    cp "$SEED_DIR/$f" "$WORKSPACE_DIR/$f"
  fi
done

# Seed the prebuilt OpenClaw npm plugin project into persistent state.
# This only touches managed npm/plugin files and leaves OAuth/config intact.
if [ -d "$PLUGIN_SEED_DIR/npm" ]; then
  mkdir -p "$STATE_DIR/npm"
  cp -a "$PLUGIN_SEED_DIR/npm/." "$STATE_DIR/npm/"
fi

chown -R openclaw:openclaw "$STATE_DIR" "$WORKSPACE_DIR"

exec gosu openclaw node src/server.js
