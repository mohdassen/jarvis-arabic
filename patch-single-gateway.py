from pathlib import Path

p = Path('/app/src/server.js')
s = p.read_text()
old = '''        log.info("wrapper", "running openclaw doctor --fix...");
        const dr = await runCmd(OPENCLAW_NODE, clawArgs(["doctor", "--fix"]));
        log.info("wrapper", `doctor --fix exit=${dr.code}`);
        if (dr.output) log.info("wrapper", dr.output);'''
new = '''        log.info("wrapper", "Jarvis configured; skipping doctor --fix to preserve single gateway ownership");'''
if old not in s:
    raise SystemExit('Expected boot doctor block not found')
s = s.replace(old, new, 1)
p.write_text(s)
print('Single-gateway startup patch applied')
