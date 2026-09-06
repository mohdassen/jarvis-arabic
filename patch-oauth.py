from pathlib import Path
p=Path('/app/src/server.js')
s=p.read_text()
marker='app.get("/setup", requireSetupAuth, (_req, res) => {'
assert marker in s
patch=r'''
// Jarvis browser OAuth bridge: password-protected and limited to OpenAI device-code auth.
let jarvisOauth = { proc: null, output: "", state: "idle", exitCode: null };

app.get("/setup/oauth", requireSetupAuth, (_req, res) => {
  res.type("html").send(`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jarvis - ChatGPT Login</title><style>body{font-family:system-ui;max-width:760px;margin:40px auto;padding:20px}button{font-size:18px;padding:14px 20px}pre{white-space:pre-wrap;background:#111;color:#eee;padding:16px;border-radius:10px;min-height:180px}a{font-size:18px}</style></head><body><h1>Jarvis - ChatGPT Login</h1><p>اضغط الزر مرة واحدة. سيظهر رابط ورمز تسجيل ChatGPT أدناه.</p><button id="start">Start ChatGPT Login</button><pre id="out">Ready.</pre><script>
const out=document.getElementById('out');
document.getElementById('start').onclick=async()=>{out.textContent='Starting...';await fetch('/setup/api/oauth/start',{method:'POST',credentials:'same-origin'});poll()};
async function poll(){try{const r=await fetch('/setup/api/oauth/status',{credentials:'same-origin'});const j=await r.json();out.textContent=j.output||j.state;if(j.state==='running')setTimeout(poll,1000);else if(j.state==='success')out.textContent+='\\n\\nSUCCESS - ChatGPT connected. Open /openclaw';}catch(e){out.textContent=String(e)}}
poll();
</script></body></html>`);
});

app.post("/setup/api/oauth/start", requireSetupAuth, async (_req, res) => {
  if (jarvisOauth.proc && jarvisOauth.state === "running") return res.json({ok:true,state:"running"});
  jarvisOauth = { proc: null, output: "", state: "running", exitCode: null };
  const args = clawArgs(["models","auth","login","--provider","openai","--device-code"]);
  const proc = childProcess.spawn(OPENCLAW_NODE, args, { env: {...process.env, OPENCLAW_STATE_DIR: STATE_DIR, OPENCLAW_WORKSPACE_DIR: WORKSPACE_DIR}, stdio:["ignore","pipe","pipe"] });
  jarvisOauth.proc = proc;
  const append = d => { jarvisOauth.output += stripAnsi(d.toString("utf8")); if (jarvisOauth.output.length > 30000) jarvisOauth.output = jarvisOauth.output.slice(-30000); };
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
  res.json({ok:true,state:"running"});
});

app.get("/setup/api/oauth/status", requireSetupAuth, (_req,res) => res.json({ok:true,state:jarvisOauth.state,exitCode:jarvisOauth.exitCode,output:jarvisOauth.output}));

'''
s=s.replace(marker,patch+marker)
p.write_text(s)
print('OAuth bridge patched')
