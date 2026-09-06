from pathlib import Path
p=Path('/app/src/server.js')
s=p.read_text()
marker='app.get("/setup", requireSetupAuth, (_req, res) => {'
assert marker in s
patch=r'''
// Jarvis browser OAuth bridge: password-protected and limited to OpenAI device-code auth.
let jarvisOauth = { proc: null, output: "", state: "idle", exitCode: null };

function jarvisOauthParsed() {
  const text = stripAnsi(jarvisOauth.output || "").replace(/\r/g, "");
  const urls = text.match(/https?:\/\/[^\s<>"']+/g) || [];
  const url = urls.find(u => /auth\.openai\.com\/codex\/device/i.test(u)) || urls.find(u => /auth\.openai\.com/i.test(u)) || "https://auth.openai.com/codex/device";
  const patterns = [/\b[A-Z0-9]{4}-[A-Z0-9]{4}\b/g, /\b[A-Z0-9]{4}(?:-[A-Z0-9]{4}){1,3}\b/g, /\b[A-Z0-9]{8}\b/g];
  let code = "";
  for (const p of patterns) { const m = text.match(p); if (m && m.length) { code = m[0]; break; } }
  const useful = text.split("\n").filter(l => l.trim() && !/Waiting for device authorization/i.test(l) && !/^[\\|\/().\-\s]+$/.test(l)).slice(-8).join("\n");
  return { url, code, useful };
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
    body = '<div class="card bad">Login failed.</div>' + (x.useful ? '<pre class="error">'+esc(x.useful)+'</pre>' : '') + '<form method="post" action="/setup/oauth/start"><button type="submit">Try Again</button></form>';
  } else if (running) {
    body = '<div class="card"><div class="status">OpenAI authorization is running</div><p><a class="login" href="'+esc(x.url)+'" target="_blank" rel="noopener">Open ChatGPT Login</a></p><div class="label">Device Code</div><div class="code">'+(x.code ? esc(x.code) : 'Generating…')+'</div><small>أدخل هذا الكود في صفحة OpenAI. ستتحدث هذه الصفحة تلقائياً.</small></div>';
  } else {
    body = '<form method="post" action="/setup/oauth/start"><button type="submit">Start ChatGPT Login</button></form><div class="card status">Ready.</div>';
  }
  return '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">'+refresh+'<title>Jarvis - ChatGPT Login</title><style>body{font-family:system-ui,-apple-system,sans-serif;max-width:680px;margin:24px auto;padding:20px;color:#111}h1{font-size:34px;margin-bottom:12px}.lead{font-size:18px;line-height:1.6}button,.login{display:inline-block;font-size:18px;font-weight:700;padding:14px 20px;border:0;border-radius:12px;background:#111;color:#fff;text-decoration:none}.card{margin:18px 0;padding:18px;border:1px solid #ddd;border-radius:16px;background:#fafafa}.code{font:700 32px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:2px;overflow-wrap:anywhere}.status{font-size:17px;font-weight:600}.label{margin-top:12px}.ok{background:#f1fff3}.bad{background:#fff3f3}.error{white-space:pre-wrap;background:#fff3f3;padding:12px;border-radius:10px;font:13px ui-monospace,SFMono-Regular,Menlo,monospace}small{color:#666}</style></head><body><h1>Jarvis - ChatGPT Login</h1><p class="lead">تسجيل دخول OpenAI بدون JavaScript. اضغط الزر مرة واحدة فقط.</p>'+body+'</body></html>';
}

app.get("/setup/oauth", requireSetupAuth, (_req, res) => {
  res.set("Cache-Control","no-store, no-cache, must-revalidate");
  res.type("html").send(jarvisOauthHtml());
});

async function startJarvisOauth() {
  if (jarvisOauth.proc && jarvisOauth.state === "running") return;
  jarvisOauth = { proc: null, output: "", state: "running", exitCode: null };
  const args = clawArgs(["models","auth","login","--provider","openai","--device-code"]);
  const openclawCmd = [OPENCLAW_NODE, ...args].map(v => JSON.stringify(String(v))).join(" ");
  const cmd = `stty cols 160 rows 50 >/dev/null 2>&1; exec ${openclawCmd}`;
  const proc = childProcess.spawn("/usr/bin/script", ["-qefc", cmd, "/dev/null"], { env: {...process.env, COLUMNS:"160", LINES:"50", TERM:"xterm-256color", OPENCLAW_STATE_DIR: STATE_DIR, OPENCLAW_WORKSPACE_DIR: WORKSPACE_DIR}, stdio:["ignore","pipe","pipe"] });
  jarvisOauth.proc = proc;
  const append = d => { jarvisOauth.output += stripAnsi(d.toString("utf8")).replace(/\r/g, ""); if (jarvisOauth.output.length > 60000) jarvisOauth.output = jarvisOauth.output.slice(-60000); };
  proc.stdout.on("data", append); proc.stderr.on("data", append);
  proc.on("error", e => { jarvisOauth.output += `\n${e}\n`; jarvisOauth.state="failed"; });
  proc.on("close", async code => {
    jarvisOauth.exitCode=code;
    if(code===0){
      const setModel=await runCmd(OPENCLAW_NODE,clawArgs(["config","set","agents.defaults.model.primary","openai/gpt-5.6-sol"]));
      jarvisOauth.output += `\n[model] ${stripAnsi(setModel.output)}`;
      const setMode=await runCmd(OPENCLAW_NODE,clawArgs(["config","set","gateway.mode","local"]));
      jarvisOauth.output += `\n[gateway] ${stripAnsi(setMode.output)}`;
      const setToken=await runCmd(OPENCLAW_NODE,clawArgs(["config","set","gateway.auth.token",OPENCLAW_GATEWAY_TOKEN]));
      jarvisOauth.output += `\n[token] exit=${setToken.code}`;
      try { await syncTrustedProxies(); await syncAllowedOrigins(); await restartGateway(); jarvisOauth.state="success"; }
      catch(e){ jarvisOauth.output += `\nGateway start error: ${e.message}`; jarvisOauth.state="failed"; }
    } else jarvisOauth.state="failed";
    jarvisOauth.proc=null;
  });
}

app.post("/setup/oauth/start", requireSetupAuth, async (_req, res) => {
  await startJarvisOauth();
  res.redirect(303, "/setup/oauth");
});

// Keep API endpoints for diagnostics/backward compatibility.
app.post("/setup/api/oauth/start", requireSetupAuth, async (_req, res) => { await startJarvisOauth(); res.set("Cache-Control","no-store"); res.json({ok:true,state:jarvisOauth.state}); });
app.get("/setup/api/oauth/status", requireSetupAuth, (_req,res) => { res.set("Cache-Control","no-store, no-cache, must-revalidate"); res.set("Pragma","no-cache"); res.json({ok:true,state:jarvisOauth.state,exitCode:jarvisOauth.exitCode,output:jarvisOauth.output}); });

'''
s=s.replace(marker,patch+marker)
p.write_text(s)
print('OAuth bridge patched')
