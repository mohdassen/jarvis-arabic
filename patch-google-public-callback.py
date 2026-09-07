from pathlib import Path

p = Path('/app/src/server.js')
s = p.read_text()

old = 'let jarvisGoogle = { state: "idle", email: "", authUrl: "", output: "" };'
new = 'let jarvisGoogle = { state: "idle", email: "", authUrl: "", redirectUri: "", output: "" };'
assert old in s
s = s.replace(old, new, 1)

old = '''    const step1 = await runGog(["--readonly","auth","add",email,"--services","calendar","--remote","--step","1","--json"]);\n    const authUrl = extractGoogleAuthUrl(step1.output);\n    if (step1.code !== 0 || !authUrl) return res.status(502).json({ok:false,error:"Could not start Google OAuth",output:stripAnsi(step1.output||"").slice(-4000)});\n    jarvisGoogle = {state:"waiting",email,authUrl,output:stripAnsi(step1.output||"")};\n    res.json({ok:true,state:"waiting",authUrl});'''
new = '''    // Use Jarvis' public HTTPS callback instead of a loopback callback.\n    // Public callbacks require a Google OAuth client of type Web application.\n    const proto = String(req.headers["x-forwarded-proto"] || req.protocol || "https").split(",")[0].trim();\n    const host = String(req.headers["x-forwarded-host"] || req.get("host") || "").split(",")[0].trim();\n    const redirectUri = `${proto}://${host}/setup/google/callback`;\n    if (!parsed?.web) {\n      return res.status(400).json({ok:false,error:"Use a Google OAuth client of type Web application, not Desktop app.",requiredRedirectUri:redirectUri});\n    }\n    const allowedRedirects = Array.isArray(parsed.web.redirect_uris) ? parsed.web.redirect_uris.map(String) : [];\n    if (!allowedRedirects.includes(redirectUri)) {\n      return res.status(400).json({ok:false,error:"The Web OAuth client does not contain Jarvis' exact Authorized redirect URI.",requiredRedirectUri:redirectUri});\n    }\n    const step1 = await runGog(["--readonly","auth","add",email,"--services","calendar","--remote","--step","1","--redirect-uri",redirectUri,"--json"]);\n    const authUrl = extractGoogleAuthUrl(step1.output);\n    if (step1.code !== 0 || !authUrl) return res.status(502).json({ok:false,error:"Could not start Google OAuth",output:stripAnsi(step1.output||"").slice(-4000)});\n    jarvisGoogle = {state:"waiting",email,authUrl,redirectUri,output:stripAnsi(step1.output||"")};\n    res.json({ok:true,state:"waiting",authUrl,redirectUri});'''
assert old in s
s = s.replace(old, new, 1)

old = '''    const step2 = await runGog(["--readonly","auth","add",email,"--services","calendar","--remote","--step","2","--auth-url",redirectUrl,"--json"]);'''
new = '''    const step2Args = ["--readonly","auth","add",email,"--services","calendar","--remote","--step","2","--auth-url",redirectUrl];\n    if (jarvisGoogle.redirectUri) step2Args.push("--redirect-uri", jarvisGoogle.redirectUri);\n    step2Args.push("--json");\n    const step2 = await runGog(step2Args);'''
assert old in s
s = s.replace(old, new, 1)

marker = 'app.post("/setup/api/google/finish", requireSetupAuth, async (req, res) => {'
assert marker in s
callback = r'''
// Public OAuth callback. Security is provided by gog's PKCE + state validation;
// no setup secret, client secret, authorization code, or refresh token is logged.
app.get("/setup/google/callback", async (req, res) => {
  try {
    const email = jarvisGoogle.email;
    const redirectUri = jarvisGoogle.redirectUri;
    if (!email || jarvisGoogle.state !== "waiting" || !redirectUri) {
      return res.status(409).type("html").send("<h2>Google login session is not active.</h2><p>Return to Jarvis Google setup and start again.</p>");
    }
    const qpos = req.originalUrl.indexOf("?");
    const suffix = qpos >= 0 ? req.originalUrl.slice(qpos) : "";
    const authUrl = redirectUri + suffix;
    const step2 = await runGog(["--readonly","auth","add",email,"--services","calendar","--remote","--step","2","--auth-url",authUrl,"--redirect-uri",redirectUri,"--json"]);
    if (step2.code !== 0) {
      jarvisGoogle.state = "failed";
      const safe = stripAnsi(step2.output || "")
        .replace(/code=[^&\\s]+/gi, "code=[REDACTED]")
        .replace(/state=[^&\\s]+/gi, "state=[REDACTED]")
        .replace(/ya29\\.[A-Za-z0-9._-]+/g, "[REDACTED_TOKEN]")
        .slice(-2500);
      log.error("google-oauth", `exchange failed: ${safe}`);
      return res.status(502).type("html").send("<h2>Google authorization exchange failed.</h2><p>Return to Jarvis Google setup and retry.</p>");
    }
    fs.writeFileSync(JARVIS_GOOGLE_ACCOUNT_FILE, email+"\\n", {encoding:"utf8",mode:0o600});
    const test = await runGog(["--readonly","--account",email,"calendar","events","--today","--json"]);
    jarvisGoogle.state = test.code === 0 ? "success" : "authorized";
    const ok = test.code === 0;
    return res.status(ok ? 200 : 502).type("html").send(`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jarvis Google</title><style>body{font-family:system-ui;padding:32px;max-width:640px;margin:auto}.ok{padding:20px;border-radius:16px;background:#effff2}.bad{padding:20px;border-radius:16px;background:#fff2f2}a{display:inline-block;margin-top:16px;padding:12px 16px;background:#111;color:#fff;border-radius:10px;text-decoration:none;font-weight:700}</style></head><body><div class="${ok?'ok':'bad'}"><h2>${ok?'Google Calendar connected ✅':'Google connected, Calendar test failed'}</h2><p>${ok?'Jarvis can now read your calendar.':'Return to setup to inspect the Calendar test.'}</p><a href="/openclaw">Open Jarvis</a></div></body></html>`);
  } catch (e) {
    log.error("google-oauth", e?.message || String(e));
    return res.status(500).type("html").send("<h2>Google OAuth failed.</h2><p>Return to Jarvis Google setup and retry.</p>");
  }
});

'''
s = s.replace(marker, callback + marker, 1)

# Update setup copy to make the required client type explicit and avoid localhost guidance.
s = s.replace('Desktop OAuth client JSON', 'Web OAuth client JSON')
s = s.replace('placeholder=\'{"installed":{"client_id":"...","client_secret":"..."}}\'', 'placeholder=\'{"web":{"client_id":"...","client_secret":"...","redirect_uris":["https://..."]}}\'')
s = s.replace('بعد الموافقة، انسخ عنوان الصفحة النهائي كاملًا من شريط المتصفح والصقه أدناه.', 'بعد الموافقة سيعود Google تلقائيًا إلى Jarvis. استخدم الحقل أدناه فقط كخيار احتياطي إذا لم يتم الرجوع تلقائيًا.')
s = s.replace('placeholder="http://localhost:.../?code=...&state=..."', 'placeholder="Fallback only: paste the complete redirect URL here"')
s = s.replace('3. Finish & Test Calendar', 'Fallback: Finish & Test Calendar')

p.write_text(s)
print('Google public callback patch applied')
