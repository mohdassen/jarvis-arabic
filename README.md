# Jarvis Arabic

Clean-room POC for a practical Arabic personal AI assistant.

## Goal
Validate OpenClaw as the agent engine before building custom infrastructure.

## Architecture
- OpenClaw: agent runtime, memory, tools, skills
- OpenAI: primary intelligence provider
- Vercel: web/mobile-facing layer where appropriate
- GitHub: source control

## Acceptance scenarios
1. What do I have today?
2. Prepare me for my next meeting.
3. Find the latest correspondence about this client/project.
4. Summarize relevant work documents.
5. Remember/follow up on a task.
6. Continue naturally from the current context without asking for the project again.

## Rule
No reuse or integration of the old `personal-ai-agent` architecture unless a specific isolated component proves useful later.

## Status
POC bootstrap started. OpenAI configuration is intentionally secret-free; credentials must be supplied via the runtime environment or OAuth and must never be committed.
