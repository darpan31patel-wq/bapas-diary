# Bapa's Diary

Every evening this makes one picture: **today's date in Bapa's Diary**, with one darshan of Bapa
from every year on this date, hung like polaroids on gold cords. It lands in Darpan's Google Drive at 7:30pm UK time.

![Tonight's picture](https://github.com/darpan31patel-wq/bapas-diary/releases/download/today/bapas-diary.jpg)

## How it works

1. **GitHub makes the picture** (`.github/workflows/daily.yml`, around 6:15pm UK time, with a second try an hour later).
   `make.py` reads the day's On This Day list from the Darshan Screensaver
   (`darshan-screensaver.pages.dev/memories/MM-DD.json`), downloads the photos from baps.org,
   picks one photo per year where it recognises Bapa's face (favouring a close darshan),
   crops around his whole head (a year where his face can't be seen is shown whole, never cropped),
   lays them out (two cords, cards shrink a little on days with many years) and saves
   `bapas-diary.jpg` to the release called **today**.
2. **Google puts it in Drive** (`google/deliver.gs`, a script in Darpan's own Google account):
   at 7:30pm it copies the picture into the Drive folder **Bapa's Diary**, named like `13 October 2026.jpg`.
   It tries again at 9:30pm and sends an email if the picture never arrived.

Nothing here needs Claude. New years' photos for each date are added to the screensaver's
On This Day lists by the screensaver's own routine; if that ever stops, this keeps working with the photos already there.

## Make one by hand

Actions tab, **Bapa's Diary**, **Run workflow**. Leave the date blank for today, or type any date (YYYY-MM-DD) to
see that day's picture under the run's *Artifacts*. Only today's date is sent to Google Drive.

On a computer: `pip install -r requirements.txt` then `python make.py --date 2026-10-12` (picture in `out/`).

## Fonts

IM Fell DW Pica (OFL), Cinzel (OFL, for the day number, see `fonts/OFL-Cinzel.txt`), Arimo (Apache 2.0).
