# Bapa's Diary

Every morning GitHub Actions makes one picture of today's date in Bapa's Diary, plus the archive, website and helper jobs in `.github/workflows/`. Read `README.md` before changing anything.

## Deploying

Test changes on the `preview` branch first, as `README.md` explains. Never push straight to `main` without Darpan's go ahead.

## The website (bapas-diary.com)

The website is a separate project from the daily picture and must never put it at risk.

- **Hands off the daily picture.** Website work never edits `make.py`, `collect.py`, `daily.yml`, `bank.yml`, `studio.yml`, `google/`, `archive/`, or the `today` and `bank` releases. Never fetch baps.org between 04:30 and 07:30 UTC (the picture's morning). Go gently on GitHub: few runs, no bursts (the account was suspended 6 to 9 Nov 2026).
- **Where it lives.** The site's code is on branch `claude/project-thread-eawr12`, the only branch that deploys (`website-deploy.yml` to Cloudflare Pages). Website timers sit on `main` only because GitHub runs timed workflows from `main`. Who owns what across the three projects: `handover/website-project-who-does-what.md` in the Claude project's files.
- **Going live.** `website-deploy.yml` runs on a push to ANY `claude/**` branch, so every push of unapproved website work carries `[skip ci]` in its head commit. Show Darpan a mockup on the real page, never a made-up page. His yes in any thread is enough: never ask him to say yes twice or in another thread.
- **His firm rules for the site.** Show Pramukh Swami Maharaj and Mahant Swami Maharaj together, never just one. Bapa pages show only photos with Bapa in them. The word Telegram never appears anywhere in the site (the deploy refuses it). No dates glued onto captions. Today shows today only. Clicking outside any open photo or popup closes it. People emoji use a light brown skin tone (🙏🏽).
- **Secrets.** Never guess the Studio (`/darpan/`) password and never write any secret value in code, logs, memory or replies.
- **Seeing it.** Claude's cloud sessions can open bapas-diary.com and photos.bapas-diary.com. After every deploy, `website-look-check.yml` opens each tab at computer, tablet and phone size and emails Darpan only when something new is wrong. Run the same check by hand with `python3 tools/look_check.py --out look` (pictures and `problems.json` in `look/`, never committed).
- **Brand.** The PSM Pharmacy brand (teal, Outfit) is not for this site. Keep the maroon, gold and ivory devotional look.

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
