---
name: google-calendar
description: Read the user's Google Calendar through the installed gog CLI for daily agenda and meeting preparation.
---

# Google Calendar for Jarvis

Use the local `gog` CLI for Google Calendar. The account is authenticated separately through the protected Jarvis setup page and credentials remain outside the workspace.

For read operations, always use read-only mode and machine-readable output:

```bash
gog --readonly --no-input calendar events --today --json --wrap-untrusted
```

For a bounded date range, inspect current command syntax first when needed:

```bash
gog schema calendar events --json
```

When the user asks "شو عندي اليوم؟" or equivalent, retrieve today's events and summarize them in local Riyadh time. Do not invent events when the command returns none.

For meeting preparation, first identify the next relevant event from Calendar, then use its title, attendees, description, and links as context for any later Gmail/Drive lookup once those services are connected.

Default behavior is read-only. Never create, update, delete, move, RSVP, or otherwise mutate a calendar event unless the user explicitly asks for that action and confirms the exact target.
