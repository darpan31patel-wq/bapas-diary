"""Break one BAPS video into moments that Search can find (Darpan, 31 Oct 2026: "if there is a 20 min video, could you
asset tag the video and break the moments up, so it comes up in search").

Step 1, cut: find where the camera cuts (ffmpeg's scene change score), join the shots into moments of about 30 seconds
to 2 minutes, and pull frames from each moment.

    python3 tools/video_moments.py cut VIDEO --id YOUTUBE_ID --work WORK_FOLDER [--date YYYY-MM-DD --place "Morbi, India"]

  WORK_FOLDER/draft.json   {"id", "date", "place", "title", "secs", "moments": [{"at", "end", "sheet", "thumb"}, ...]}
  WORK_FOLDER/sheet-AT.jpg  four frames of the moment side by side, to describe it from
  WORK_FOLDER/thumb-AT.jpg  the frame shown on the Search card (480 wide)

  The YouTube id is the one in the video's link (watch?v=ID). The date, place and title come from data/youtube (the
  Guruhari Darshan playlist, tools/youtube/match.py) when the id is there; --date and --place are for anything else.

Step 2, describe: each moment gets a few words (what is happening, where, who is seen), a few tags, and whether Bapa
himself is clearly in it, in person (Darpan, 25 Oct 2026: a murti, a portrait or a framed photo is not Bapa). This is
written into WORK_FOLDER/notes.json by whoever looks at the sheets:

    {"AT": {"text": "Swamishri gives darshan to the children of Morbi", "tags": "children, garland", "bapa": 1}, ...}
  A moment left out of notes.json, or with "skip": 1, is not kept (blank screens, titles). "join": 1 adds it to the
  moment before (the same thing carrying on), so a moment runs as long as what is happening.

Step 3, save: the moments go into the repo, ready for the website build.

    python3 tools/video_moments.py save WORK_FOLDER

  data/video-moments/ID.json   {"id", "date", "place", "title", "m": [[at, end, text, tags, bapa], ...]}
  data/video-moments/ID/AT.jpg the card frame of each moment

  The guru's name follows the date (Darpan, 31 Oct 2026): before 13 August 2016 Swamishri is Pramukh Swami Maharaj,
  after it Mahant Swami Maharaj. "Swamishri" in a note is written out as the right name, and a note that names the
  wrong guru as Swamishri stops the save.

The website build (tools/build_search.py --moments data/video-moments) puts every moment into Search, each opening the
video on YouTube at its own second, and gives the gold Video Darshan links their list of moments.
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOUTUBE = os.path.join(HERE, 'data', 'youtube')
SAVED = os.path.join(HERE, 'data', 'video-moments')
PSM_TO_MSM = datetime.date(2016, 8, 13)
SHORTEST, LONGEST = 30, 120    # seconds: a moment is at least this long, and longer ones are cut at their shots


def guru(date):
    """The guru who is Swamishri on that day (Darpan, 31 Oct 2026)."""
    return 'Pramukh Swami Maharaj' if date and datetime.date.fromisoformat(date[:10]) < PSM_TO_MSM else 'Mahant Swami Maharaj'


def named(text, date):
    """'Swamishri' written out as the day's guru the first time, and a check that the other guru is not called Swamishri."""
    g = guru(date)
    other = 'Mahant Swami Maharaj' if g.startswith('Pramukh') else 'Pramukh Swami Maharaj'
    # the other guru may be named (a murti of Pramukh Swami Maharaj, Pujya Mahant Swami as a senior sadhu), but never
    # as the one who is giving the darshan: a note that starts with his name is the wrong guru
    if re.match(re.escape(other), text.strip(), re.I):
        raise SystemExit(f'Wrong guru for {date}: "{text}" (on this day Swamishri is {g})')
    return re.sub(r'\bSwamishri\b', g, text, count=1) if g not in text else text


def about(vid):
    """Date, place and title of a playlist video, from data/youtube."""
    for line in open(os.path.join(YOUTUBE, 'flat.tsv'), encoding='utf-8'):
        f = line.rstrip('\n').split('\t')
        if f[0] == vid:
            title, secs = f[1], int(f[2] or 0) if len(f) > 2 else 0
            break
    else:
        return {}
    days = json.load(open(os.path.join(YOUTUBE, 'days.json'), encoding='utf-8'))
    date = min((d for d, vs in days.items() if any(v['id'] == vid for v in vs)), default='')
    # the place is after the date in the title: "Guruhari Darshan, 23-24 Oct 2026, Morbi, India | Nagar Yatra"
    m = re.search(r'\d{4},\s*([^|]+?)\s*(?:\||$)', title)
    return {'date': date, 'place': m.group(1).strip() if m else '', 'title': title, 'secs': secs}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def length(video):
    return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video]).stdout.strip())


def cuts(video, score=0.3):
    """The seconds where the picture changes to a new shot (a small copy of the picture is enough to see it)."""
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', video, '-an', '-sn', '-dn',
                          '-vf', f"scale=320:-2,select='gt(scene,{score})',showinfo", '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    return [float(t) for t in re.findall(r'pts_time:([\d.]+)', out)]


def moments(shots, total):
    """Shots joined into moments of SHORTEST to LONGEST seconds; a long shot alone is cut into even pieces."""
    edges = sorted({0.0, *[t for t in shots if 0 < t < total], total})
    out, start = [], 0.0
    for t in edges[1:]:
        if t - start < SHORTEST and total - t >= SHORTEST:
            continue                              # too short yet: the next shot joins it
        while t - start > LONGEST:                # one long shot (a whole Puja or assembly in one take)
            n = int((t - start) // LONGEST) + 1
            step = (t - start) / n
            out.append((start, start + step)); start += step
        out.append((start, t)); start = t
    if out and out[-1][1] < total:
        out[-1] = (out[-1][0], total)
    return [(round(a), round(b)) for a, b in out if b - a >= 1]


def frame(video, at, path, width):
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{at:.2f}', '-i', video, '-frames:v', '1',
         '-vf', f'scale={width}:-2', '-q:v', '4', path])


def cut(a):
    os.makedirs(a.work, exist_ok=True)
    info = about(a.id) if a.id else {}
    total = length(a.video)
    found = cuts(a.video)
    ms = moments(found, total)
    draft = {'id': a.id, 'date': a.date or info.get('date', ''), 'place': a.place or info.get('place', ''),
             'title': info.get('title', ''), 'secs': round(total), 'cuts': len(found), 'moments': []}
    for at, end in ms:
        # four frames across the moment for the sheet, and the card frame a third of the way in (past any fade)
        span = end - at
        times = [at + span * f for f in (0.12, 0.37, 0.62, 0.87)]
        parts = []
        for i, t in enumerate(times):
            p = os.path.join(a.work, f'f-{at}-{i}.jpg'); frame(a.video, t, p, 480); parts.append(p)
        sheet = os.path.join(a.work, f'sheet-{at}.jpg')
        run(['ffmpeg', '-v', 'error', '-y'] + sum((['-i', p] for p in parts), []) +
            ['-filter_complex', 'hstack=inputs=4', '-q:v', '4', sheet])
        for p in parts:
            os.remove(p)
        thumb = os.path.join(a.work, f'thumb-{at}.jpg')
        frame(a.video, at + span / 3, thumb, 480)
        draft['moments'].append({'at': at, 'end': end, 'sheet': os.path.basename(sheet), 'thumb': os.path.basename(thumb)})
    json.dump(draft, open(os.path.join(a.work, 'draft.json'), 'w'), indent=1, ensure_ascii=False)
    print(f"{len(found)} camera cuts, {len(ms)} moments in {total / 60:.1f} minutes -> {a.work}")
    print(f"date {draft['date'] or '?'}, place {draft['place'] or '?'}, Swamishri is {guru(draft['date']) if draft['date'] else '?'}")


def save(a):
    draft = json.load(open(os.path.join(a.work, 'draft.json'), encoding='utf-8'))
    notes = json.load(open(os.path.join(a.work, 'notes.json'), encoding='utf-8'))
    vid, date = draft['id'], draft['date']
    if not re.fullmatch(r'[\w-]{11}', vid or ''):
        raise SystemExit('The moments need the YouTube id of the video (cut --id), so each one can open at its second.')
    if not date:
        raise SystemExit('The moments need the date of the video (cut --date), for Search and the guru name.')
    keep = []
    for m in draft['moments']:
        n = notes.get(str(m['at']))
        if not n or n.get('skip'):
            continue
        if n.get('join') and keep:          # the same thing carrying on: the moment before simply runs longer
            keep[-1][1] = m['end']
            continue
        keep.append([m['at'], m['end'], named(n['text'].strip(), date), n.get('tags', '').strip(), 1 if n.get('bapa') else 0])
    os.makedirs(os.path.join(SAVED, vid), exist_ok=True)
    for f in os.listdir(os.path.join(SAVED, vid)):
        os.remove(os.path.join(SAVED, vid, f))
    for at, *_ in keep:
        shutil.copy(os.path.join(a.work, f'thumb-{at}.jpg'), os.path.join(SAVED, vid, f'{at}.jpg'))
    out = {'id': vid, 'date': date, 'place': draft['place'], 'title': draft['title'], 'secs': draft['secs'], 'm': keep}
    with open(os.path.join(SAVED, f'{vid}.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f'{len(keep)} moments of {len(draft["moments"])} kept -> data/video-moments/{vid}.json')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='step', required=True)
    c = sub.add_parser('cut')
    c.add_argument('video')
    c.add_argument('--id', default='', help='the YouTube id (watch?v=ID)')
    c.add_argument('--work', required=True)
    c.add_argument('--date', default='')
    c.add_argument('--place', default='')
    s = sub.add_parser('save')
    s.add_argument('work')
    a = ap.parse_args()
    cut(a) if a.step == 'cut' else save(a)


if __name__ == '__main__':
    main()
