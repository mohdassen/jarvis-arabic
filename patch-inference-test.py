from pathlib import Path

p = Path('/app/src/server.js')
s = p.read_text()
marker = 'app.get("/setup", requireSetupAuth, (_req, res) => {'
assert marker in s

patch = r'''
// Jarvis protected end-to-end inference diagnostic.
// Uses OpenClaw's supported `agent` CLI through the running Gateway, so this
// exercises the same configured agent/model/auth path without exposing secrets.
app.post("/setup/api/jarvis/inference-test", requireSetupAuth, async (_req, res) => {
  try {
    await ensureGatewayRunning();

    const auth = await runCmd(
      OPENCLAW_NODE,
      clawArgs(["models", "auth", "list", "--agent", "main", "--provider", "openai", "--json"]),
    );

    const turn = await runCmd(
      OPENCLAW_NODE,
      clawArgs([
        "agent",
        "--agent", "main",
        "--message", "Reply exactly JARVIS_OK",
        "--timeout", "90",
        "--json",
      ]),
      { stripOutput: true },
    );

    const clean = stripAnsi(turn.output || "").trim();
    const ok = turn.code === 0 && /JARVIS_OK/.test(clean);

    return res.status(ok ? 200 : 502).json({
      ok,
      agent: "main",
      expected: "JARVIS_OK",
      authCommandExit: auth.code,
      authProfilePresent: auth.code === 0 && /openai/i.test(stripAnsi(auth.output || "")),
      inferenceCommandExit: turn.code,
      output: clean.slice(-12000),
    });
  } catch (err) {
    log.error("jarvis-test", `inference test failed: ${err?.message || String(err)}`);
    return res.status(500).json({ ok: false, error: err?.message || String(err) });
  }
});

'''

s = s.replace(marker, patch + marker)
p.write_text(s)
print('Jarvis inference test endpoint patched')
