from pathlib import Path

p = Path('/app/src/server.js')
s = p.read_text()
marker = 'app.get("/setup", requireSetupAuth, (_req, res) => {'
assert marker in s

patch = r'''
// Jarvis protected Google Workspace OAuth bridge (Calendar first).
// Credentials and refresh tokens stay on Railway's persistent /data volume.
const JARVIS_GOG_HOME = process.env.GOG_HOME || "/data/gog";
const JARVIS_GOOGLE_ACCOUNT_FILE = path.join(JARVIS_GOG_HOME, "jarvis-account.txt");
let jarvisGoogle = { state: "idle", email: "", authUrl: "", output: "" };

function jarvisGoogleEnv() {
  return {
    ...process.env,
    GOG_HOME: JARVIS_GOG_HOME,
    GOG_KEYRING_BACKEND: process.env.GOG_KEYRING_BACKEND || "file",
  };
}

async function runGog(args) {
  return runCmd("gog", args, { env: jarvisGoogleEnv(), stripOutput: true });
}

function extractGoogleAuthUrl(output) {
  const text = String(output || "");
  const m = text.match(/auth_url\s+([^\s]+)/i) || text.match(/(https:\/\/accounts\.google\.com\/[^\s]+)/i);
  return m ? m[1].trim() : "";
}

async function jarvisGoogleStatus() {
  try {
    const r = await runGog(["auth", "list", "--json"]);
    const ok = r.code === 0 && /@/.test(String(r.output || ""));
    return { ok, output: stripAnsi(r.output || "").slice(-6000) };
  } catch (e) {
    return { ok: false, output: e?.message || String(e) };
  }
}

function googleSetupHtml() {
  return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jarvis - Google Calendar</title><style>
  body{font-family:system-ui,-apple-system,sans-serif;max-width:760px;margin:24px auto;padding:20px;color:#111}h1{font-size:32px}.card{margin:16px 0;padding:18px;border:1px solid #ddd;border-radius:16px;background:#fafafa}input,textarea{width:100%;box-sizing:border-box;font:15px system-ui;padding:12px;border:1px solid #bbb;border-radius:10px;margin:8px 0 14px}textarea{min-height:150px;font:13px ui-monospace,SFMono-Regular,Menlo,monospace}button,.btn{display:inline-block;padding:13px 18px;border:0;border-radius:11px;background:#111;color:#fff;font-size:16px;font-weight:700;text-decoration:none}.muted{color:#666}.ok{background:#f1fff3}.bad{background:#fff3f3}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#111;color:#eee;padding:12px;border-radius:10px;max-height:250px;overflow:auto}
  </style></head><body><h1>Jarvis — Google Calendar</h1><p class="muted">ابدأ بصلاحية قراءة التقويم فقط. لا ترسل ملف Google OAuth أو أي سر داخل ChatGPT؛ أدخله هنا مباشرة.</p>
  <div class="card"><label>Google account email</label><input id="email" type="email" placeholder="name@gmail.com"><label>Desktop OAuth client JSON</label><textarea id="credentials" placeholder='{"installed":{"client_id":"...","client_secret":"..."}}'></textarea><button onclick="startAuth()">1. Start Google Login</button></div>
  <div id="authCard" class="card" style="display:none"><p><a id="authLink" class="btn" target="_blank" rel="noopener">2. Open Google Login</a></p><p class="muted">بعد الموافقة، انسخ عنوان الصفحة النهائي كاملًا من شريط المتصفح والصقه أدناه.</p><textarea id="redirectUrl" placeholder="http://localhost:.../?code=...&state=..."></textarea><button onclick="finishAuth()">3. Finish & Test Calendar</button></div>
  <div id="result" class="card">Ready.</div>
<script>
function show(obj, bad=false){const el=document.getElementById('result');el.className='card '+(bad?'bad':'ok');el.textContent=typeof obj==='string'?obj:JSON.stringify(obj,null,2)}
async function startAuth(){
  const email=document.getElementById('email').value.trim();
  const credentials=document.getElementById('credentials').value.trim();
  show('Starting Google OAuth…');
  const r=await fetch('/setup/api/google/start',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email,credentials})});
  const j=await r.json(); if(!r.ok){show(j,true);return;} document.getElementById('authLink').href=j.authUrl;document.getElementById('authCard').style.display='block';show('OAuth URL created. Open Google Login.');
}
async function finishAuth(){
  const redirectUrl=document.getElementById('redirectUrl').value.trim();show('Finishing authorization and testing Calendar…');
  const r=await fetch('/setup/api/google/finish',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({redirectUrl})});
  const j=await r.json();show(j,!r.ok);
}
</script></body></html>`;
}

app.get("/setup/google", requireSetupAuth, async (_req, res) => {
  res.set("Cache-Control", "no-store, no-cache, must-revalidate");
  res.type("html").send(googleSetupHtml());
});

app.get("/setup/api/google/status", requireSetupAuth, async (_req, res) => {
  const status = await jarvisGoogleStatus();
  res.set("Cache-Control", "no-store");
  res.json({ ok: true, connected: status.ok, state: jarvisGoogle.state, email: jarvisGoogle.email || null });
});

app.post("/setup/api/google/start", requireSetupAuth, async (req, res) => {
  try {
    const email = String(req.body?.email || "").trim();
    const raw = String(req.body?.credentials || "").trim();
    if (!/^\S+@\S+\.\S+$/.test(email)) return res.status(400).json({ok:false,error:"Valid Google account email is required"});
    if (!raw || raw.length > 100000) return res.status(400).json({ok:false,error:"Desktop OAuth client JSON is required"});
    let parsed;
    try { parsed = JSON.parse(raw); } catch (e) { return res.status(400).json({ok:false,error:"Invalid OAuth JSON"}); }
    const client = parsed?.installed || parsed?.web;
    if (!client?.client_id || !client?.client_secret) return res.status(400).json({ok:false,error:"OAuth JSON must contain client_id and client_secret"});

    fs.mkdirSync(JARVIS_GOG_HOME, {recursive:true, mode:0o700});
    const tmp = path.join(JARVIS_GOG_HOME, `.oauth-client-${crypto.randomBytes(8).toString('hex')}.json`);
    fs.writeFileSync(tmp, raw, {encoding:"utf8", mode:0o600});
    try {
      const setCreds = await runGog(["auth","credentials","set",tmp]);
      if (setCreds.code !== 0) return res.status(502).json({ok:false,error:"Could not store Google OAuth credentials",output:stripAnsi(setCreds.output||"").slice(-3000)});
    } finally { try { fs.unlinkSync(tmp); } catch {} }

    const step1 = await runGog(["--readonly","auth","add",email,"--services","calendar","--remote","--step","1","--json"]);
    const authUrl = extractGoogleAuthUrl(step1.output);
    if (step1.code !== 0 || !authUrl) return res.status(502).json({ok:false,error:"Could not start Google OAuth",output:stripAnsi(step1.output||"").slice(-4000)});
    jarvisGoogle = {state:"waiting",email,authUrl,output:stripAnsi(step1.output||"")};
    res.json({ok:true,state:"waiting",authUrl});
  } catch (e) {
    log.error("google-oauth", e?.message || String(e));
    res.status(500).json({ok:false,error:e?.message || String(e)});
  }
});

app.post("/setup/api/google/finish", requireSetupAuth, async (req, res) => {
  try {
    const redirectUrl = String(req.body?.redirectUrl || "").trim();
    const email = jarvisGoogle.email;
    if (!email || jarvisGoogle.state !== "waiting") return res.status(409).json({ok:false,error:"Start Google Login first"});
    if (!/^https?:\/\//i.test(redirectUrl)) return res.status(400).json({ok:false,error:"Paste the complete final redirect URL from the browser"});

    const step2 = await runGog(["--readonly","auth","add",email,"--services","calendar","--remote","--step","2","--auth-url",redirectUrl,"--json"]);
    if (step2.code !== 0) return res.status(502).json({ok:false,error:"Google authorization exchange failed",output:stripAnsi(step2.output||"").slice(-5000)});

    fs.writeFileSync(JARVIS_GOOGLE_ACCOUNT_FILE, email+"\n", {encoding:"utf8",mode:0o600});
    const test = await runGog(["--readonly","--account",email,"calendar","events","--today","--json"]);
    const auth = await jarvisGoogleStatus();
    jarvisGoogle.state = test.code === 0 ? "success" : "authorized";
    res.status(test.code === 0 ? 200 : 502).json({
      ok: test.code === 0,
      connected: auth.ok,
      email,
      calendarTestExit: test.code,
      calendarOutput: stripAnsi(test.output||"").slice(-10000),
    });
  } catch (e) {
    log.error("google-oauth", e?.message || String(e));
    res.status(500).json({ok:false,error:e?.message || String(e)});
  }
});

'''

s = s.replace(marker, patch + marker)
p.write_text(s)
print('Google Calendar OAuth bridge patched')
