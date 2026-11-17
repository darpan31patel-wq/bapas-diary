# Bapa's Diary

Every morning GitHub Actions makes one picture of today's date in Bapa's Diary, plus the archive, website and helper jobs in `.github/workflows/`. Read `README.md` before changing anything.

## Deploying

Test changes on the `preview` branch first, as `README.md` explains. Never push straight to `main` without Darpan's go ahead.

## How Darpan likes to work

- Darpan owns PSM Pharmacy and builds these projects with Claude. He has no tech background: explain in plain, warm, short steps.
- Concise replies, no filler. No dashes in replies. Emoji are welcome.
- Ask one question at a time, and only when you truly need to. Otherwise make the sensible call and say what you chose.
- Always look for ways to make things better (tools, design, speed, workflow). Tell him, and when it is clearly worth it, set it up and do it.
- Pull before you start. He works on these repos from several sessions at once. Never force push.

## Design and visual checks

- For any page, screen or UI change, use the **frontend-design** skill before writing code (it is on Darpan's claude.ai account; in a local session on his Mac it is the `frontend-design` plugin). Choose a deliberate look. No generic AI template styling.
- Never call UI work done without looking at it:
  1. Serve the page locally, for example `python3 -m http.server 8080` in the folder that holds it (the browser blocks `file://`).
  2. Open it with the **Playwright MCP** (set up in `.mcp.json`; tools named `browser_*`) or a short Playwright script.
  3. Screenshot it at the sizes listed under "Screens to check" below, plus phone 390x844.
  4. Look at every screenshot. Fix overflow, clipping, overlaps, weak contrast, tiny text and empty space. Check the console for errors.
- Playwright screenshots land in `.playwright-mcp/`, which is git ignored. Never commit them.

### Screens to check

Desktop 1440x900 and tablet 1280x800. Keep the existing devotional look unless asked.
