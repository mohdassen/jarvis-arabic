from pathlib import Path
p=Path('/app/src/server.js')
s=p.read_text()
marker='app.get("/setup", requireSetupAuth, (_req, res) => {'
assert marker in s
patch=r'''
// Jarvis browser OAuth bridge: password-protected and limited to OpenAI device-code auth.
let jarvisOauth = { proc: null, output: "", state: "idle", exitCode: null };

app.get("/setup/oauth", requireSetupAuth, (_req, res) => {
  res.type("html").send(`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jarvis - ChatGPT Login</title><style>
body{font-family:system-ui,-apple-system,sans-serif;max-width:760px;margin:24px auto;padding:20px;color:#111}h1{font-size:34px;margin-bottom:12px}.lead{font-size:18px;line-height:1.6}button,.login{display:inline-block;font-size:18px;font-weight:700;padding:14px 20px;border:0;border-radius:12px;background:#111;color:#fff;text-decoration:none}.card{margin:18px 0;padding:18px;border:1px solid #ddd;border-radius:16px;background:#fafafa}.hidden{display:none}.code{font:700 30px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:2px;word-break:break-all}.status{font-size:17px;font-weight:600}.raw{white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;background:#111;color:#eee;padding:14px;border-radius:12px;max-height:220px;overflow:auto;font:13px ui-monospace,SFMono-Regular,Menlo,monospace}small{color:#666}
</style></head><body><h1>Jarvis - ChatGPT Login</h1><p class="lead">اضغط الزر مرة واحدة. عندما يصبح تسجيل الدخول جاهزاً سيظهر الرابط والكود بشكل واضح.</p><button id="start">Start ChatGPT Login</button><div id="auth" class="card hidden"><div class="status">جاهز لتسجيل الدخول</div><p><a id="login" class="login" target="_blank" rel="noopener">Open ChatGPT Login</a></p><div>Device Code</div><div id="code" class="code"></div><small>لا ترسل هذا الكود لأي شخص.</small></div><div id="state" class="card status">Ready.</div><details><summary>Technical output</summary><pre id="out" class="raw"></pre></details><script>
const out=document.getElementById('out'), state=document.getElementById('state'), auth=document.getElementById('auth'), login=document.getElementById('login'), code=document.getElementById('code'), start=document.getElementById('start');
function compactTTY(s){return (s||'').replace(/\r/g,'').replace(/(?:^|\n)([^\n])(?=\n|$)/g,'$1').replace(/\n{3,}/g,'\n\n')}
function extract(s){const text=compactTTY(s);const urls=text.match(/https?:\/\/[^\s<>"']+/g)||[];const url=urls.find(u=>/auth\.openai\.com|openai\.com/i.test(u))||urls[0]||'';const codes=text.match(/\b[A-Z0-9]{4}(?:-[A-Z0-9]{4})+\b/g)||[];return {text,url,code:codes[0]||''}}
start.onclick=async()=>{start.disabled=true;state.textContent='Starting ChatGPT authorization…';await fetch('/setup/api/oauth/start',{method:'POST',credentials:'same-origin',cache:'no-store'});poll()};
async function poll(){try{const r=await fetch('/setup/api/oauth/status',{credentials:'same-origin',cache:'no-store'});const j=await r.json();const x=extract(j.output);out.textContent=x.text||j.state;if(x.url){login.href=x.url;auth.classList.remove('hidden')}if(x.code){code.textContent=x.code;auth.classList.remove('hidden')}if(j.state==='running'){state.textContent=x.url?'Waiting for you to complete ChatGPT login…':'Preparing device authorization…';setTimeout(poll,900)}else if(j.state==='success'){state.textContent='SUCCESS — ChatGPT connected.';start.disabled=true;auth.classList.add('hidden');}else if(j.state==='failed'){state.textContent='Login failed. See Technical output.';start.disabled=false}else{state.textContent=j.state;start.disabled=false}}catch(e){state.textContent='Status error: '+e;start.disabled=false}}
poll();
</script></body></html>`);
});

app.post("/setup/api/oauth/start", requireSetupAuth, async (_req, res) => {
  if (jarvisOauth.proc && jarvisOauth.state === "running") return res.json({ok:true,state:"running"});
  jarvisOauth = { proc: null, output: "", state: "running", exitCode: null };
  const args = clawArgs(["models","auth","login","--provider","openai","--device-code"]);
  // OpenClaw intentionally requires an interactive TTY even for device-code auth.
  // Railway is headless, so run the CLI inside util-linux `script`. Set a sane PTY
  // size first; otherwise mobile browsers can receive output wrapped one character per line.
  const openclawCmd = [OPENCLAW_NODE, ...args].map(v => JSON.stringify(String(v))).join(" ");
  const cmd = `stty cols 120 rows 40 >/dev/null 2>&1; exec ${openclawCmd}`;
  const proc = childProcess.spawn("/usr/bin/script", ["-qefc", cmd, "/dev/null"], { env: {...process.env, COLUMNS:"120", LINES:"40", TERM:"xterm-256color", OPENCLAW_STATE_DIR: STATE_DIR, OPENCLAW_WORKSPACE_DIR: WORKSPACE_DIR}, stdio:["ignore","pipe","pipe"] });
  jarvisOauth.proc = proc;
  const append = d => { jarvisOauth.output += stripAnsi(d.toString("utf8")).replace(/\r/g, ""); if (jarvisOauth.output.length > 30000) jarvisOauth.output = jarvisOauth.output.slice(-30000); };
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
  res.set("Cache-Control","no-store");
  res.json({ok:true,state:"running"});
});

app.get("/setup/api/oauth/status", requireSetupAuth, (_req,res) => { res.set("Cache-Control","no-store, no-cache, must-revalidate"); res.set("Pragma","no-cache"); res.json({ok:true,state:jarvisOauth.state,exitCode:jarvisOauth.exitCode,output:jarvisOauth.output}); });

'''
s=s.replace(marker,patch+marker)
p.write_text(s)
print('OAuth bridge patched')
