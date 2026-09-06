# Jarvis Arabic

Clean-room POC for a practical Arabic personal AI assistant.

## Goal
Validate OpenClaw as the agent engine before building custom infrastructure.

## Architecture
- OpenClaw: agent runtime, memory, tools, skills
- OpenAI: primary intelligence provider
- Railway: OpenClaw runtime with persistent `/data` volume
- Vercel: web/mobile-facing layer where appropriate
- GitHub: source control

## Acceptance scenarios
1. What do I have today?
2. Prepare me for my next meeting.
3. Find the latest correspondence about this client/project.
4. Summarize relevant work documents.
5. Remember/follow up on a task.
6. Continue naturally from the current context without asking for the project again.

## Jarvis workspace
The Railway image seeds `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, and `MEMORY.md` into the persistent OpenClaw workspace on first boot. Existing workspace files are preserved on later deploys.

## Rule
No reuse or integration of the old `personal-ai-agent` architecture unless a specific isolated component proves useful later.

## Status
Railway runtime is healthy. Jarvis workspace bootstrap and browser-based OpenAI device-code OAuth bridge are implemented in source. The OAuth bridge uses a pseudo-TTY so OpenClaw's interactive safety check also works on Railway's headless runtime. Provider authentication remains runtime-only; credentials must never be committed.
