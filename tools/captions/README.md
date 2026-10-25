# New photos with their captions (website only)

Darpan, 25 Oct 2026: "I want captions and photos" together, daily at 8pm UK, like Chrome did on 18 Oct.

Why Chrome: captions are only written on baps.org's day pages, and those sit behind a Cloudflare check that GitHub
can't pass (and must never try to get past). The photo files carry no caption (tested on GitHub, caption-probe.txt on
branch claude/project-thread-urww6n). In Darpan's own Chrome the pages open like they do for any reader.

Nothing here touches the daily 2pm picture's code. It only adds rows to `crawl/button/YYYY-MM.json` on the `database`
branch (the same file the screensaver button filled), then starts `archive.yml`, which rebuilds `bapas.db` the way the
nightly album scan already does. From there the noon Drive download, the high res R2 copy and the website follow.

## The daily run (a scheduled Claude task, 8pm UK)

1. Not between 04:30 and 07:30 UTC. Check out branch `database` (`git fetch origin +refs/heads/database:refs/remotes/origin/database`).
2. `python3 tools/captions/captions_merge.py --known --crawl crawl` prints the pages already saved.
3. In Darpan's Chrome (Claude in Chrome), open a new tab on `https://www.baps.org/vicharan.aspx`. If baps.org shows a
   check page instead, stop and try tomorrow: never click or solve it.
4. Paste `captions_chrome.js` into the tab with the javascript tool, then `await CAP.run(<known pages>, 3)`.
   It lists the pages it read (new days, the last 3 days again, and each day's linked photo albums).
5. For each part: `CAP.short(i)` (and `CAP.short(i, 90)`, ... while capsTotal is bigger), write it to a file exactly
   (caption pieces joined in order), `python3 tools/captions/captions_merge.py --part that.json --crawl crawl`.
   A "hash does not match" means it was copied wrongly: read that part again.
6. Bapa's schedule (for the Darshan Screensaver, Darpan 25 Oct): `await CAP.schedule()` in the same tab. If it gives
   an error, skip it. Otherwise write it exactly to a file (text joined from
   `CAP.scheduleText(800)`, `(1600)`, ... up to textTotal; drop textTotal) and `captions_merge.py --schedule that.json --crawl crawl`
   (saves `crawl/schedule/latest.json`; the screensaver reads it from raw.githubusercontent.com).
7. Commit `crawl/button` and `crawl/schedule` on `database`, push to `refs/heads/database` (pull first), then
   `gh api -X POST repos/darpan31patel-wq/bapas-diary/actions/workflows/archive.yml/dispatches -f ref=main`.
8. Close the tab. If Chrome isn't connected (Mac off), do nothing: the next run catches up.
