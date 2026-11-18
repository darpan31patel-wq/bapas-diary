# Bapa's Diary

Every morning this makes one picture: **today's date in Bapa's Diary**, with one darshan of Bapa
from every year on this date, hung like ivory polaroids on cords. It lands in Darpan's Google Drive at 8:30am UK time.

![Today's picture](https://github.com/darpan31patel-wq/bapas-diary/releases/download/today/bapas-diary.jpg)

## How it works

1. **GitHub makes the picture** (`.github/workflows/daily.yml`, around 6:15am UK time, with a second try an hour later).
   `make.py` reads the day's On This Day list from the Darshan Screensaver
   (our own saved copy in `archive/memories/MM-DD.json`, refreshed by `lists.yml` from `darshan-screensaver.pages.dev/memories`), downloads the photos from baps.org,
   picks one photo per year where it recognises Bapa's face (favouring a close darshan),
   crops around his whole head (a year where his face can't be seen is shown whole, never cropped),
   lays them out (two cords; on busy days the cards get narrower and the photos taller) and saves
   `bapas-diary.jpg` to the release called **today**.
2. **Google puts it in Drive** (`google/deliver.gs`, a script in Darpan's own Google account):
   at 8:30am it copies the picture into the Drive folder **Bapa's Diary**, named like `13 October 2026.jpg`.
   It tries again at 10:30am and sends an email if the picture never arrived.

**New photos each year** (`collect.py`, in the same morning run). baps.org pages are behind a Cloudflare check
GitHub can't pass, but its photos load fine and vicharan photos are named
`GalleryImages/<album>/WebImages/<YYYY>_<MM>_<DD>_<NNN>_<Place>.jpg` with album numbers that only go up.
So each morning it tries the next album numbers with the last few days' dates and Bapa's likely place
(the vicharan schedule, where he was last, or his usual places), lists the album it finds, keeps up to 30 photos
where it recognises Bapa and adds them to `archive/MM-DD.json`. `make.py` adds those to the On This Day list,
so 13 October 2027 includes 13 October 2026. `archive/state.json` says how far it has got.

Nothing here needs Claude. If no new photos turn up for two weeks (say baps.org renames its photos), the run opens
an issue on this repo, which GitHub emails to you; the pictures keep working with every photo already saved.

## The other pictures and jobs

- **The special picture.** The same morning run picks the most special thing about the day (a festival, a big day,
  a Today in BAPS History story, a Satpurush in UK & Europe diary entry) and makes `bapas-diary-special.png`
  (`make.py`, looks in `looks.py`, colours and fonts in `style.py`). The list of chosen days is `archive/special-days.json`.
- **The Studio** lives on the website (bapas-diary.com/darpan/), which is its own project. It reads the photo packs
  that **Studio photo packs** (`studio.yml`, 9:30 UTC) writes to the branch `studio`, and can ask that job to remake a day.
  **Weekly Studio lessons** (`learn.yml`, Sundays) learns from Darpan's own Studio choices.
- **Backups.** **Backup bank** (`bank.yml`, nightly) keeps the next 90 days of pictures ready in case a morning fails.
  **Copy for Drive** and **Backup everything** keep copies of the code and data.
- **The two Telegram channels** (`telegram/`) are refreshed with **Refresh the Telegram channels**.
- Jobs whose names start with `website-` belong to the website and never touch the 2pm picture.

## Make one by hand

Actions tab, **Bapa's Diary**, **Run workflow**. Leave the date blank for today, or type any date (YYYY-MM-DD) to
see that day's picture under the run's *Artifacts*. Only today's date, made from `main`, is sent to Google Drive.

## Trying a change safely: before and after

1. Make the change on a test branch (or on **preview**, which is kept the same as `main` between tests). Never straight on `main`.
2. Actions tab, **Bapa's Diary**, **Run workflow**, *Use workflow from*: that branch, and in the date box type
   `before:` and some dates, for example `before:2026-11-17,2026-11-12`.
3. Each date is made twice, once the way `main` makes it today and once with the change. The run saves them on that branch in
   `preview/`: `<date>-side-by-side.jpg` (before above, after below), `<date>-close-up.jpg` (the middle of both at
   the size people see when they zoom in on a phone) and the same for any special picture. `tools/before_after.py` draws them.
4. Darpan looks at the before and after pictures and says yes. Only then does the change go to `main`, and the next morning's picture uses it.

A run on any branch other than `main` never touches today's picture or Google Drive and skips the photo collector.
A plain date on a test branch saves just that day's picture to `preview/<date>.jpg`.

On a computer: `pip install -r requirements.txt` then `python make.py --date 2026-10-12` (picture in `out/`).
The photos come from Darpan's Drive archive or baps.org, so a computer needs to reach one of them;
the GitHub run above always can.

## Fonts

EB Garamond (OFL, see `fonts/OFL-EB-Garamond.txt`) for the title, years and footer; Arimo (Apache 2.0) for the places.
