/**
 * Bapa's Diary: puts today's picture into your Google Drive at 8:30am (UK time).
 *
 * How to set up (once):
 *   1. Paste this whole file into a new project at https://script.google.com
 *   2. Choose "setup" in the function menu at the top and press Run.
 *   3. Google asks for permission: Review permissions, pick your account, Advanced,
 *      "Go to Bapa's Diary (unsafe)" (it's your own script), then Allow.
 * That's it. A folder called "Bapa's Diary" appears in your Drive and fills every morning.
 *
 * The backup bank (Darpan, 20 Oct 2026): GitHub also makes the next 90 days ahead of time. This script keeps
 * a copy of them in a second folder, "Bapa's Diary backup", and if today's fresh picture still hasn't come
 * by 10:30am it puts today's backup picture into Bapa's Diary instead, so 2pm still has something to send.
 *
 * Bapa's Diary Studio (Darpan, 25 Oct 2026): the Studio tab on your master dashboard can send a picture you made
 * there straight into Drive. "Put it in the Bapa's Diary folder" makes it that day's picture there (today before 2pm or
 * any day ahead, and 2pm sends yours; a day gone by just has its copy updated);
 * "Save as a new export" puts it in a separate folder, "Bapa's Diary Studio exports", and leaves today's alone.
 * To switch it on (once): Deploy > New deployment > Select type: Web app > Execute as: Me, Who has access: Anyone
 * > Deploy (allow it). Then choose "studioCode" in the function menu, press Run, and paste the line it shows into
 * the Studio's "Connect to Google Drive" box. Nobody can send a picture without that code.
 */

const FOLDER_NAME = "Bapa's Diary";
const BACKUP_NAME = "Bapa's Diary backup";
const SOURCE = 'https://github.com/darpan31patel-wq/bapas-diary/releases/download/today/';
const BANK = 'https://api.github.com/repos/darpan31patel-wq/bapas-diary/releases/tags/bank';
const TZ = 'Europe/London';
const STUDIO_NAME = "Bapa's Diary Studio exports";
const SETTINGS_NAME = "Bapa's Diary Studio settings";   // the never again list (a folder of its own, so nothing in it is ever sent)
const NEVER_NAME = 'never again.json';

function setup() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('deliver').timeBased().atHour(8).nearMinute(30).everyDays(1).inTimezone(TZ).create();
  ScriptApp.newTrigger('deliverLate').timeBased().atHour(10).nearMinute(30).everyDays(1).inTimezone(TZ).create();
  ScriptApp.newTrigger('syncBank').timeBased().everyHours(2).create();
  folder_();
  backupFolder_();
  deliver();   // if today's picture is already made, it arrives straight away
  syncBank();  // starts copying the backup bank
}

/** 8:30am: copy today's picture into the folder (does nothing if it's already there). */
function deliver() {
  return deliver_(false);
}

/** 10:30am: second try; if the fresh picture never came, today's backup goes in and you get an email. */
function deliverLate() {
  return deliver_(true);
}

function deliver_(isLastTry) {
  const now = new Date();
  const today = Utilities.formatDate(now, TZ, 'yyyy-MM-dd');
  const day = Utilities.formatDate(now, TZ, 'd MMMM yyyy');
  const name = day + '.png';
  const folder = folder_();
  if (alive_(folder, name)) return true;   // already delivered (a deleted copy doesn't count)

  const stamp = UrlFetchApp.fetch(SOURCE + 'date.txt', { muteHttpExceptions: true });
  if (stamp.getResponseCode() !== 200 || stamp.getContentText().trim() !== today) {
    console.log("Today's picture isn't ready yet");
    if (isLastTry) {
      const used = useBackup_(day);
      MailApp.sendEmail(Session.getEffectiveUser().getEmail(),
        used ? "Bapa's Diary used the backup today" : "Bapa's Diary didn't arrive today",
        'The fresh picture for ' + day + " wasn't ready by 10:30am. " +
        (used ? "Today's picture from the backup bank is in the Bapa's Diary folder instead, so 2pm goes out as normal."
              : 'There was no backup for today either, so nothing is in the folder for 2pm.') +
        '\n\nYou can see what happened at https://github.com/darpan31patel-wq/bapas-diary/actions');
    }
    return false;
  }
  const picture = UrlFetchApp.fetch(SOURCE + 'bapas-diary.png').getBlob().setName(name);
  folder.createFile(picture);
  // the same picture 4096 pixels wide (the most a WhatsApp photo keeps), for the 2pm photos; the PNG goes as the document
  const photo = UrlFetchApp.fetch(SOURCE + 'bapas-diary.jpg', { muteHttpExceptions: true });
  if (photo.getResponseCode() === 200) folder.createFile(photo.getBlob().setName(name.replace('.png', ' photo.jpg')));
  return true;
}

/** Copies today's backup picture (and its photo copy) into Bapa's Diary. True if there was one. */
function useBackup_(day) {
  const backup = backupFolder_(), folder = folder_();
  const png = alive_(backup, day + '.png');
  if (!png) return false;
  png.makeCopy(day + '.png', folder).setDescription('from the backup bank');
  const jpg = alive_(backup, day + ' photo.jpg');
  if (jpg) jpg.makeCopy(day + ' photo.jpg', folder).setDescription('from the backup bank');
  return true;
}

/**
 * Every 2 hours: brings the backup folder in line with the bank on GitHub. New days are copied (a few per run,
 * so the first fill takes a day or so), a day remade on GitHub is copied again, and days gone by are binned.
 * Each day has '16 December 2026.png', '... photo.jpg', and when there is one '... caption.txt' (the channel
 * story for under your 2pm caption) and '... special.png' (the big day picture).
 */
function syncBank() {
  const started = Date.now();
  const res = UrlFetchApp.fetch(BANK, { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) { console.log('No bank on GitHub yet: ' + res.getResponseCode()); return; }
  const backup = backupFolder_();
  const today = Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd');
  const kinds = { '.png': '.png', '.jpg': ' photo.jpg', '-caption.txt': ' caption.txt', '-special.png': ' special.png' };
  const wanted = {};
  JSON.parse(res.getContentText()).assets.forEach(a => {
    const m = a.name.match(/^(\d{4})-(\d{2})-(\d{2})(\.png|\.jpg|-caption\.txt|-special\.png)$/);
    if (!m || a.name.slice(0, 10) < today) return;
    const day = Utilities.formatDate(new Date(+m[1], +m[2] - 1, +m[3], 12), TZ, 'd MMMM yyyy');
    wanted[day + kinds[m[4]]] = a;
  });
  const have = {};
  const it = backup.getFiles();
  while (it.hasNext()) {
    const f = it.next();
    if (f.isTrashed()) continue;
    if (!wanted[f.getName()]) f.setTrashed(true);   // a day gone by, or one the bank no longer has
    else have[f.getName()] = f;
  }
  let copied = 0;
  for (const name of Object.keys(wanted).sort(byDate_)) {
    const a = wanted[name], old = have[name];
    if (old && old.getDescription() === a.updated_at) continue;
    if (Date.now() - started > 4 * 60 * 1000) break;   // Google stops scripts at 6 minutes; the next run carries on
    const blob = UrlFetchApp.fetch(a.browser_download_url).getBlob().setName(name);
    if (old) old.setTrashed(true);
    backup.createFile(blob).setDescription(a.updated_at);
    copied++;
  }
  console.log('Backup bank: copied ' + copied + ', ' + Object.keys(wanted).filter(n => n.endsWith('.png') && !n.endsWith('special.png')).length + ' days on GitHub');
}

/** Sorts '16 December 2026 photo.jpg' style names by their date, soonest first. */
function byDate_(a, b) {
  const t = n => new Date(n.replace(/ (photo\.jpg|caption\.txt|special\.png)$|\.png$/, '')).getTime() || 0;
  return t(a) - t(b) || (a < b ? -1 : 1);
}

function alive_(folder, name) {
  const it = folder.getFilesByName(name);
  while (it.hasNext()) { const f = it.next(); if (!f.isTrashed()) return f; }
  return null;
}

function folder_() {
  const found = DriveApp.getFoldersByName(FOLDER_NAME);
  return found.hasNext() ? found.next() : DriveApp.createFolder(FOLDER_NAME);
}

function backupFolder_() {
  const found = DriveApp.getFoldersByName(BACKUP_NAME);
  return found.hasNext() ? found.next() : DriveApp.createFolder(BACKUP_NAME);
}

/** Shows the line to paste into the Studio's "Connect to Google Drive" box (makes a new secret code the first time). */
function studioCode() {
  const props = PropertiesService.getScriptProperties();
  let key = props.getProperty('STUDIO_KEY');
  if (!key) { key = Utilities.getUuid().replace(/-/g, ''); props.setProperty('STUDIO_KEY', key); }
  const url = ScriptApp.getService().getUrl();
  if (!url) { console.log('Deploy the script as a web app first (Deploy > New deployment > Web app), then run studioCode again.'); return; }
  console.log('Paste this into the Studio:  ' + url + '#' + key);
}

/** Adds a photo ({photo: {i, caption, date, year}}) or words ({caption}) to the never again list the morning run reads. */
function never_(p) {
  const found = DriveApp.getFoldersByName(SETTINGS_NAME);
  const folder = found.hasNext() ? found.next() : DriveApp.createFolder(SETTINGS_NAME);
  const file = alive_(folder, NEVER_NAME);
  let list = { photos: [], captions: [] };
  if (file) { try { list = Object.assign(list, JSON.parse(file.getBlob().getDataAsString())) } catch (e) {} }
  if (p.photo) list.photos.push(Object.assign({ added: Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd') }, p.photo));
  else if (p.caption && list.captions.indexOf(p.caption) < 0) list.captions.push(p.caption);
  else if (!p.caption) return { ok: false, error: 'Nothing to add to the never again list.' };
  const text = JSON.stringify(list, null, 1);
  if (file) file.setContent(text); else folder.createFile(NEVER_NAME, text, 'application/json');
  return { ok: true, mode: 'never', photos: list.photos.length, captions: list.captions.length };
}

/** A picture from the Studio. {key, mode: 'replace' | 'new', date: 'yyyy-MM-dd', png, jpg (base64)} */
function doPost(e) {
  const answer = o => ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
  try {
    const p = JSON.parse(e.postData.contents);
    const key = PropertiesService.getScriptProperties().getProperty('STUDIO_KEY');
    if (!key || p.key !== key) return answer({ ok: false, error: 'The Studio code is wrong. Run studioCode in the script and paste the new line into the Studio.' });
    if (p.mode === 'ping') return answer({ ok: true, mode: 'ping', version: 3 });   // the Studio's "Check the connection"
    if (p.mode === 'never') return answer(never_(p));   // Never use this photo again (Darpan, 29 Oct 2026)
    const when = new Date(p.date + 'T12:00:00Z');
    const day = Utilities.formatDate(when, TZ, 'd MMMM yyyy');
    const today = Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd');
    const png = Utilities.newBlob(Utilities.base64Decode(p.png), 'image/png');
    const jpg = p.jpg ? Utilities.newBlob(Utilities.base64Decode(p.jpg), 'image/jpeg') : null;
    if (p.mode === 'replace') {
      // any day goes back into Bapa's Diary as that day's picture (Darpan, 28 Oct 2026: re-export to its folder). A day ahead
      // is kept, since the 8:30am delivery leaves a day alone once its picture is there; a day gone by is only updated
      const folder = folder_();
      const oldPng = alive_(folder, day + '.png');
      const hour = +Utilities.formatDate(new Date(), TZ, 'H');
      const when2pm = p.date < today ? 'past' : p.date > today ? 'ahead' : hour >= 14 ? 'after' : 'before';
      if (oldPng) oldPng.setTrashed(true);
      const oldJpg = alive_(folder, day + ' photo.jpg');
      if (oldJpg) oldJpg.setTrashed(true);
      folder.createFile(png.setName(day + '.png')).setDescription('from the Studio');
      if (jpg) folder.createFile(jpg.setName(day + ' photo.jpg')).setDescription('from the Studio');
      return answer({ ok: true, mode: 'replace', folder: FOLDER_NAME, name: day + '.png', when2pm: when2pm, time: Utilities.formatDate(new Date(), TZ, 'HH:mm') });
    }
    const found = DriveApp.getFoldersByName(STUDIO_NAME);
    const out = found.hasNext() ? found.next() : DriveApp.createFolder(STUDIO_NAME);
    const name = day + ' studio ' + Utilities.formatDate(new Date(), TZ, 'HH.mm');
    out.createFile(png.setName(name + '.png'));
    if (jpg) out.createFile(jpg.setName(name + ' photo.jpg'));
    return answer({ ok: true, mode: 'new', folder: STUDIO_NAME, name: name + '.png', time: Utilities.formatDate(new Date(), TZ, 'HH:mm') });
  } catch (err) {
    return answer({ ok: false, error: String(err) });
  }
}
