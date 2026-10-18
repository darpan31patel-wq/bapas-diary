# Bapa's Diary photo database, for the screensaver project

This copy lives in the GitHub repo on the `database` branch, so other projects can read it from a fixed address:

- one day: `https://raw.githubusercontent.com/darpan31patel-wq/bapas-diary/database/export/by-day/10-18.json` (swap 10-18 for the day)
- everything: `https://raw.githubusercontent.com/darpan31patel-wq/bapas-diary/database/export/bapas-diary-photos.json` (33 MB)

Both addresses allow use from a web page on another site. When the database is rebuilt, the new files are committed here and the addresses stay the same.

Built 18 October 2026 from every vicharan page on baps.org, 1999 to 2026. Nothing was cut out: every captioned photo is in, murtis and devotees too.

## What is in this folder (`export/`)

- `bapas-diary-photos.json` (33 MB): the whole database in one file. 366 days, 25 to 28 years on most days, 361,277 photo entries (260,107 different photos; a photo from a trip page can stand in for several nearby days).
- `by-day/MM-DD.json` (366 small files, about 100 KB each): the same data, one file per day of the year. This matches how the screensaver already loads `memories/MM-DD.json`, so it may be the easier one to use on a web page.
- `README.md`: this note.

## How the file is laid out

```json
{
  "about": "...",
  "built": "2026-10-18",
  "image_url": "https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/WebImages/{id}.jpg",
  "years": [1999, 2000, ..., 2026],
  "days": {
    "10-18": [
      {
        "year": 1999,
        "date": "1999-10-18",
        "place": "Nairobi, Kenya",
        "album": "3228",
        "photos": [
          {"id": "TP_1999_115_0a", "caption": "BAPS Shri Swaminarayan Mandir, Nairobi"},
          {"id": "TP_1999_112_29", "caption": "Swamishri in a divine mood"}
        ]
      }
    ]
  }
}
```

- `days` has one key per day of the year, `"01-01"` to `"12-31"` (including `"02-29"`).
- Each day is a list of groups. A group is one year at one place on baps.org (one album). A year can have more than one group when the day's photos sit in two albums.
- `date` is the day the photos were really taken. It is only different from the day when nothing exists for that exact day in that year, so the nearest day of the same trip (within a week) stands in. For example 18 October has 2007 photos from 19 October 2007.
- `place` is taken from the baps.org page title, so it reads like "Gondal, India" or "Detroit, Cleveland".
- Captions are written in full. A caption starting "Swamishri" is a photo of Bapa (Pramukh Swami Maharaj before 13 August 2016, Mahant Swami Maharaj from then on). Other captions are murtis, devotees, mandirs and so on. A few captions are empty.
- The picture itself is not in the file. Build its web address from `image_url` by filling in the group's `album` and the photo's `id`:

```
https://www.baps.org/Data/Sites/1/Media/GalleryImages/3228/WebImages/TP_1999_115_0a.jpg
```

In JavaScript:

```js
const db = await (await fetch('bapas-diary-photos.json')).json();     // or by-day/10-18.json for one day
const today = db.days['10-18'];                                        // list of groups
for (const g of today)
  for (const p of g.photos)
    console.log(g.year, g.date, g.place, p.caption,
      `https://www.baps.org/Data/Sites/1/Media/GalleryImages/${g.album}/WebImages/${p.id}.jpg`);
```

Pictures are served by baps.org and are about 800 px wide. Loading many at once makes baps.org slow, so load a few at a time.

## Things to know

- The file has every photo, not only the good ones. Bapa's Diary itself runs a face check on the day's photos to pick one clear darshan per year. The screensaver can do the same, or simply prefer captions that start "Swamishri".
- 2026 only runs up to the crawl date. New vicharan pages after 18 October 2026 are not in this file until it is rebuilt.
- A handful of pages (3 in 2008, 3 in 2021, 1 in 2025) failed to load during the crawl and are missing.

## How it was made, and how to rebuild it

Everything lives in the GitHub repo `darpan31patel-wq/bapas-diary`, branch `preview` (the database is not on `main`; `main` makes the daily family picture).

1. **Crawl baps.org** with `tools/crawl.js`, run in Darpan's own Chrome (baps.org blocks plain scripts). It reads every vicharan page of a year and saves `bapas-diary-YYYY.json`, one per year. The 28 year files and `bapas-diary-fixes.json` (dates for pages that did not name a day) are kept in this project's folder `bapas-diary-crawl/`. To refresh a year, crawl that year again and replace its file.
2. **Build the database** of 366 text files:
   ```
   python tools/build_db.py /path/to/bapas-diary-crawl
   ```
   This writes `archive/vicharan/MM-DD.txt`. Each photo's date comes from its file name or its page title; a missing day borrows the nearest day of the same trip.
3. **Export the JSON** for other projects:
   ```
   python tools/export_db.py --out bapas-diary-photos.json --split by-day
   ```
   `--urls` writes the full picture address on every photo as well (the file grows to about 70 MB).

Any Claude session with the repo can run steps 2 and 3 in a minute. Step 1 needs Chrome.
