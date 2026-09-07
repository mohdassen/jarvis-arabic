#!/bin/bash
set -e

STATE_DIR="${OPENCLAW_STATE_DIR:-/data/.openclaw}"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"
SEED_DIR="/opt/jarvis-workspace"
CODEX_PLUGIN_DIR="/opt/codex-runtime/node_modules/@openclaw/codex"
GOG_HOME="${GOG_HOME:-/data/gog}"
GOG_KEY_FILE="/data/.gog-keyring-password"

rm -rf /data/.linuxbrew 2>/dev/null || true
rm -rf "$STATE_DIR/npm/projects" 2>/dev/null || true
rm -rf "$STATE_DIR/npm/.cache" "$STATE_DIR/cache" 2>/dev/null || true

mkdir -p /data "$STATE_DIR" "$WORKSPACE_DIR" "$WORKSPACE_DIR/memory" "$GOG_HOME"
chown -R openclaw:openclaw /data
chmod 700 /data "$GOG_HOME"

# Keep gog's encrypted file-keyring usable across redeploys without putting the
# password in Git, image layers, logs, or OpenClaw memory.
if [ ! -s "$GOG_KEY_FILE" ]; then
  umask 077
  python3 - <<'PY' > "$GOG_KEY_FILE"
import secrets
print(secrets.token_urlsafe(48))
PY
fi
chown openclaw:openclaw "$GOG_KEY_FILE"
chmod 600 "$GOG_KEY_FILE"
export GOG_HOME
export GOG_KEYRING_BACKEND="file"
export GOG_KEYRING_PASSWORD="$(cat "$GOG_KEY_FILE")"

for f in AGENTS.md SOUL.md IDENTITY.md USER.md MEMORY.md; do
  if [ ! -f "$WORKSPACE_DIR/$f" ] && [ -f "$SEED_DIR/$f" ]; then
    cp "$SEED_DIR/$f" "$WORKSPACE_DIR/$f"
  fi
done

if [ -L "$STATE_DIR/npm" ]; then
  rm -f "$STATE_DIR/npm"
fi
mkdir -p "$STATE_DIR/npm"

if command -v gog >/dev/null 2>&1; then
  echo "[jarvis] gog ready: $(gog --version 2>/dev/null | head -n 1)"
else
  echo "[jarvis] ERROR: gog Google Workspace CLI is missing" >&2
  exit 1
fi

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

chown -R openclaw:openclaw "$STATE_DIR" "$WORKSPACE_DIR" "$GOG_HOME"

exec gosu openclaw node src/server.js
