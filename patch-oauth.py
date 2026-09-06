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
body{font-family:system-ui,-apple-system,sans-serif;max-width:680px;margin:24px auto;padding:20px;color:#111}h1{font-size:34px;margin-bottom:12px}.lead{font-size:18px;line-height:1.6}button,.login{display:inline-block;font-size:18px;font-weight:700;padding:14px 20px;border:0;border-radius:12px;background:#111;color:#fff;text-decoration:none}.card{margin:18px 0;padding:18px;border:1px solid #ddd;border-radius:16px;background:#fafafa}.hidden{display:none}.code{font:700 32px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:2px;overflow-wrap:anywhere}.status{font-size:17px;font-weight:600}.error{white-space:pre-wrap;background:#fff3f3;padding:12px;border-radius:10px;font:13px ui-monospace,SFMono-Regular,Menlo,monospace}small{color:#666}
</style></head><body><h1>Jarvis - ChatGPT Login</h1><p class="lead">اضغط الزر مرة واحدة. سيظهر فقط رابط OpenAI ورمز تسجيل الدخول.</p><button id="start">Start ChatGPT Login</button><div id="auth" class="card hidden"><div class="status">جاهز لتسجيل الدخول</div><p><a id="login" class="login" href="https://auth.openai.com/codex/device" target="_blank" rel="noopener">Open ChatGPT Login</a></p><div>Device Code</div><div id="code" class="code">Preparing…</div><small>أدخل هذا الكود في صفحة OpenAI. لا ترسله لأي شخص.</small></div><div id="state" class="card status">Ready.</div><pre id="err" class="error hidden"></pre><script>
const state=document.getElementById('state'),auth=document.getElementById('auth'),login=document.getElementById('login'),code=document.getElementById('code'),start=document.getElementById('start'),err=document.getElementById('err');
function clean(s){return (s||'').replace(/\x1b\[[0-?]*[ -\/]*[@-~]/g,'').replace(/\r/g,'')}
function parse(s){const text=clean(s);const urls=text.match(/https?:\/\/[^\s<>"']+/g)||[];const url=urls.find(u=>/auth\.openai\.com\/codex\/device/i.test(u))||urls.find(u=>/auth\.openai\.com/i.test(u))||'https://auth.openai.com/codex/device';
 const patterns=[/\b[A-Z0-9]{4}-[A-Z0-9]{4}\b/g,/\b[A-Z0-9]{4}(?:-[A-Z0-9]{4}){1,3}\b/g,/\b[A-Z0-9]{8}\b/g]; let c=''; for(const p of patterns){const m=text.match(p);if(m&&m.length){c=m[0];break}}
 const useful=text.split('\n').filter(l=>l.trim()&&!/Waiting for device authorization/i.test(l)&&!/^[\\|\/().\-\s]+$/.test(l)).slice(-8).join('\n');return {url,code:c,useful}}
start.onclick=async()=>{start.disabled=true;auth.classList.remove('hidden');code.textContent='Preparing…';state.textContent='Preparing device authorization…';err.classList.add('hidden');await fetch('/setup/api/oauth/start',{method:'POST',credentials:'same-origin',cache:'no-store'});poll()};
async function poll(){try{const r=await fetch('/setup/api/oauth/status',{credentials:'same-origin',cache:'no-store'});const j=await r.json();const x=parse(j.output);login.href=x.url;if(x.code){code.textContent=x.code;state.textContent='افتح OpenAI وأدخل الكود أعلاه.'}else if(j.state==='running'){state.textContent='Generating Device Code…'}if(j.state==='running'){setTimeout(poll,700)}else if(j.state==='success'){state.textContent='SUCCESS — ChatGPT connected.';auth.classList.add('hidden');start.disabled=true}else if(j.state==='failed'){state.textContent='Login failed.';start.disabled=false;if(x.useful){err.textContent=x.useful;err.classList.remove('hidden')}}else{start.disabled=false}}catch(e){state.textContent='Status error';err.textContent=String(e);err.classList.remove('hidden');start.disabled=false}}
poll();
</script></body></html>`);
});

app.post("/setup/api/oauth/start", requireSetupAuth, async (_req, res) => {
  if (jarvisOauth.proc && jarvisOauth.state === "running") return res.json({ok:true,state:"running"});
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
  res.set("Cache-Control","no-store"); res.json({ok:true,state:"running"});
});

app.get("/setup/api/oauth/status", requireSetupAuth, (_req,res) => { res.set("Cache-Control","no-store, no-cache, must-revalidate"); res.set("Pragma","no-cache"); res.json({ok:true,state:jarvisOauth.state,exitCode:jarvisOauth.exitCode,output:jarvisOauth.output}); });

'''
s=s.replace(marker,patch+marker)
p.write_text(s)
print('OAuth bridge patched')
