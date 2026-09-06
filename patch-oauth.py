from pathlib import Path
p=Path('/app/src/server.js')
s=p.read_text()
marker='app.get("/setup", requireSetupAuth, (_req, res) => {'
assert marker in s
patch=r'''
// Jarvis browser OAuth bridge: password-protected and limited to OpenAI device-code auth.
let jarvisOauth = { proc: null, output: "", state: "idle", exitCode: null };
const JARVIS_AGENT_ID = "main";

function normalizeJarvisTerminal(input) {
  let text = String(input || "");
  text = text.replace(/\x1B\][^\x07]*(?:\x07|\x1B\\)/g, "");
  text = text.replace(/\x1B\[[0-?]*[ -\/]*[@-~]/g, "");
  text = text.replace(/\x1B[@-_]/g, "");
  text = text.replace(/\r/g, "\n");
  while (/[^\n]\x08/.test(text)) text = text.replace(/[^\n]\x08/g, "");
  text = text.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");
  return text;
}

function jarvisOauthParsed() {
  const text = normalizeJarvisTerminal(jarvisOauth.output);
  const urls = text.match(/https?:\/\/[^\s<>"']+/gi) || [];
  const url = urls.find(u => /auth\.openai\.com\/codex\/device/i.test(u)) || urls.find(u => /auth\.openai\.com/i.test(u)) || "https://auth.openai.com/codex/device";
  let code = "";
  const patterns = [
    /\b[A-Z0-9]{3,8}(?:-[A-Z0-9]{3,8}){1,3}\b/gi,
    /(?:device\s*(?:code|authorization)[^A-Z0-9]{0,40})([A-Z0-9][A-Z0-9\-]{5,24})/i,
    /(?:enter|use)\s+(?:the\s+)?(?:code\s+)?([A-Z0-9][A-Z0-9\-]{5,24})/i
  ];
  for (const p of patterns) {
    const m = text.match(p);
    if (!m) continue;
    const candidate = Array.isArray(m) ? (m[1] || m[0]) : m;
    if (candidate && !/WAITING|DEVICE|OPENAI|AUTHORIZ/i.test(candidate)) { code = candidate.trim(); break; }
  }
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  const usefulLines = lines.filter(l =>
    !/Waiting for device authorization/i.test(l) &&
    !/^OpenAI authorization is running$/i.test(l) &&
    !/^[\\|\/().\-\s]+$/.test(l)
  );
  const useful = usefulLines.slice(0, 50).join("\n");
  return { url, code, useful };
}

async function jarvisOpenAiAuthExists() {
  try {
    const r = await runCmd(OPENCLAW_NODE, clawArgs(["models","auth","list","--agent",JARVIS_AGENT_ID,"--provider","openai","--json"]));
    if (r.code !== 0) return false;
    const out = String(r.output || "").trim();
    if (!out) return false;
    try {
      const j = JSON.parse(out);
      if (Array.isArray(j)) return j.length > 0;
      if (Array.isArray(j?.profiles)) return j.profiles.length > 0;
      if (Array.isArray(j?.items)) return j.items.length > 0;
      if (j && typeof j === "object") return JSON.stringify(j).includes("openai:") || JSON.stringify(j).includes('"provider":"openai"');
    } catch (_) {
      return /openai:/i.test(out) && !/no .*profile|none|empty/i.test(out);
    }
  } catch (_) {}
  return false;
}

async function finishJarvisOauth() {
  const setModel=await runCmd(OPENCLAW_NODE,clawArgs(["config","set","agents.defaults.model.primary","openai/gpt-5.6-sol"]));
  jarvisOauth.output += `\n[model] ${stripAnsi(setModel.output)}`;
  const setMode=await runCmd(OPENCLAW_NODE,clawArgs(["config","set","gateway.mode","local"]));
  jarvisOauth.output += `\n[gateway] ${stripAnsi(setMode.output)}`;
  const setToken=await runCmd(OPENCLAW_NODE,clawArgs(["config","set","gateway.auth.token",OPENCLAW_GATEWAY_TOKEN]));
  jarvisOauth.output += `\n[token] exit=${setToken.code}`;
  await syncTrustedProxies();
  await syncAllowedOrigins();
  await restartGateway();
  jarvisOauth.state="success";
}

function jarvisOauthHtml() {
  const x = jarvisOauthParsed();
  const running = jarvisOauth.state === "running";
  const success = jarvisOauth.state === "success";
  const failed = jarvisOauth.state === "failed";
  const esc = v => String(v || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  const refresh = running ? '<meta http-equiv="refresh" content="2">' : '';
  let body = '';
  if (success) {
    body = '<div class="card ok">SUCCESS — ChatGPT connected.</div><p><a class="login" href="/openclaw">Open Jarvis</a></p>';
  } else if (failed) {
    body = '<div class="card bad">Login failed.</div>' + (x.useful ? '<pre class="debug">'+esc(x.useful)+'</pre>' : '') + '<form method="post" action="/setup/oauth/start"><button type="submit">Try Again</button></form>';
  } else if (running) {
    body = '<div class="card"><div class="status">OpenAI authorization is running</div><p><a class="login" href="'+esc(x.url)+'" target="_blank" rel="noopener">Open ChatGPT Login</a></p><div class="label">Device Code</div><div class="code">'+(x.code ? esc(x.code) : 'Generating…')+'</div><small>أدخل هذا الكود في صفحة OpenAI.</small></div>';
    if (!x.code && x.useful) body += '<div class="card"><div class="status">OAuth output</div><pre class="debug">'+esc(x.useful)+'</pre></div>';
  } else {
    body = '<form method="post" action="/setup/oauth/start"><button type="submit">Start ChatGPT Login</button></form><div class="card status">Ready.</div>';
  }
  return '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">'+refresh+'<title>Jarvis - ChatGPT Login</title><style>body{font-family:system-ui,-apple-system,sans-serif;max-width:680px;margin:24px auto;padding:20px;color:#111}h1{font-size:34px;margin-bottom:12px}.lead{font-size:18px;line-height:1.6}button,.login{display:inline-block;font-size:18px;font-weight:700;padding:14px 20px;border:0;border-radius:12px;background:#111;color:#fff;text-decoration:none}.card{margin:18px 0;padding:18px;border:1px solid #ddd;border-radius:16px;background:#fafafa}.code{font:700 32px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:2px;overflow-wrap:anywhere}.status{font-size:17px;font-weight:600}.label{margin-top:12px}.ok{background:#f1fff3}.bad{background:#fff3f3}.debug{white-space:pre-wrap;overflow-wrap:anywhere;background:#111;color:#eee;padding:12px;border-radius:10px;font:13px ui-monospace,SFMono-Regular,Menlo,monospace;max-height:260px;overflow:auto}small{color:#666}</style></head><body><h1>Jarvis - ChatGPT Login</h1><p class="lead">تسجيل دخول OpenAI. اضغط الزر مرة واحدة فقط.</p>'+body+'</body></html>';
}

app.get("/setup/oauth", requireSetupAuth, async (_req, res) => {
  // A successful OpenAI device authorization can occasionally make the CLI exit
  // non-zero after the profile was already saved. Recover automatically.
  if (jarvisOauth.state === "failed" && await jarvisOpenAiAuthExists()) {
    try { await finishJarvisOauth(); } catch (e) { jarvisOauth.output += `\nGateway finalize error: ${e.message}`; }
  }
  res.set("Cache-Control","no-store, no-cache, must-revalidate");
  res.type("html").send(jarvisOauthHtml());
});

async function startJarvisOauth() {
  if (jarvisOauth.proc && jarvisOauth.state === "running") return;
  if (await jarvisOpenAiAuthExists()) {
    jarvisOauth = { proc: null, output: "Existing OpenAI auth profile found.", state: "running", exitCode: 0 };
    try { await finishJarvisOauth(); } catch(e) { jarvisOauth.output += `\nGateway finalize error: ${e.message}`; jarvisOauth.state="failed"; }
    return;
  }
  jarvisOauth = { proc: null, output: "", state: "running", exitCode: null };
  const args = clawArgs(["models","auth","login","--provider","openai","--agent",JARVIS_AGENT_ID,"--device-code","--set-default"]);
  const openclawCmd = [OPENCLAW_NODE, ...args].map(v => JSON.stringify(String(v))).join(" ");
  const cmd = `stty cols 180 rows 60 >/dev/null 2>&1; exec ${openclawCmd}`;
  const proc = childProcess.spawn("/usr/bin/script", ["-qefc", cmd, "/dev/null"], { env: {...process.env, COLUMNS:"180", LINES:"60", TERM:"xterm-256color", NO_COLOR:"1", FORCE_COLOR:"0", OPENCLAW_STATE_DIR: STATE_DIR, OPENCLAW_WORKSPACE_DIR: WORKSPACE_DIR}, stdio:["ignore","pipe","pipe"] });
  jarvisOauth.proc = proc;
  const append = d => { jarvisOauth.output += d.toString("utf8"); if (jarvisOauth.output.length > 120000) jarvisOauth.output = jarvisOauth.output.slice(-120000); };
  proc.stdout.on("data", append); proc.stderr.on("data", append);
  proc.on("error", e => { jarvisOauth.output += `\n${e}\n`; jarvisOauth.state="failed"; });
  proc.on("close", async code => {
    jarvisOauth.exitCode=code;
    const saved = await jarvisOpenAiAuthExists();
    if(code===0 || saved){
      try { await finishJarvisOauth(); }
      catch(e){ jarvisOauth.output += `\nGateway finalize error: ${e.message}`; jarvisOauth.state="failed"; }
    } else jarvisOauth.state="failed";
    jarvisOauth.proc=null;
  });
}

app.post("/setup/oauth/start", requireSetupAuth, async (_req, res) => { await startJarvisOauth(); res.redirect(303, "/setup/oauth"); });
app.post("/setup/api/oauth/start", requireSetupAuth, async (_req, res) => { await startJarvisOauth(); res.set("Cache-Control","no-store"); res.json({ok:true,state:jarvisOauth.state}); });
app.get("/setup/api/oauth/status", requireSetupAuth, (_req,res) => { const x=jarvisOauthParsed(); res.set("Cache-Control","no-store, no-cache, must-revalidate"); res.set("Pragma","no-cache"); res.json({ok:true,state:jarvisOauth.state,exitCode:jarvisOauth.exitCode,url:x.url,code:x.code,output:x.useful}); });

'''
s=s.replace(marker,patch+marker)
p.write_text(s)
print('OAuth bridge patched')
