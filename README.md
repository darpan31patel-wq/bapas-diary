# Bapa's Diary

Every morning this makes one picture: **today's date in Bapa's Diary**, with one darshan of Bapa
from every year on this date, hung like ivory polaroids on cords. It lands in Darpan's Google Drive at 8:30am UK time.

![Today's picture](https://github.com/darpan31patel-wq/bapas-diary/releases/download/today/bapas-diary.jpg)

## How it works

1. **GitHub makes the picture** (`.github/workflows/daily.yml`, around 6:15am UK time, with a second try an hour later).
   `make.py` reads the day's On This Day list from the Darshan Screensaver
   (`darshan-screensaver.pages.dev/memories/MM-DD.json`), downloads the photos from baps.org,
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

## Make one by hand

Actions tab, **Bapa's Diary**, **Run workflow**. Leave the date blank for today, or type any date (YYYY-MM-DD) to
see that day's picture under the run's *Artifacts*. Only today's date, made from `main`, is sent to Google Drive.

## Trying a change safely

Push the change to the branch **preview** (never straight to `main`), then run the workflow on that branch
(Run workflow, *Use workflow from*: preview, any date). A run on any branch other than `main` never touches
today's picture or Google Drive and skips the photo collector: it saves its picture to `preview/<date>.jpg`
on that branch. When it looks right, merge `preview` into `main`; the next morning's picture uses it.

On a computer: `pip install -r requirements.txt` then `python make.py --date 2026-10-12` (picture in `out/`).

## Fonts

EB Garamond (OFL, see `fonts/OFL-EB-Garamond.txt`) for the title, years and footer; Arimo (Apache 2.0) for the places.
