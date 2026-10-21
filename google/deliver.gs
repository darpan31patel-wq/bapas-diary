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
 */

const FOLDER_NAME = "Bapa's Diary";
const BACKUP_NAME = "Bapa's Diary backup";
const SOURCE = 'https://github.com/darpan31patel-wq/bapas-diary/releases/download/today/';
const BANK = 'https://api.github.com/repos/darpan31patel-wq/bapas-diary/releases/tags/bank';
const TZ = 'Europe/London';
// Safety and backups (Darpan, 21 Oct 2026). Every delivery and every change to Bapa's Diary on GitHub gets a row in
// this Google Sheet (made for you), and every night at 3am a dated copy of your Google scripts, the log and the
// picture maker goes into the backups folder, keeping the last KEEP_NIGHTS nights.
const LOG_SHEET_NAME = "Bapa's Diary log";
const BACKUPS_NAME = "Bapa's Diary backups";
const KEEP_NIGHTS = 30;
const PACKED_FROM = 'https://github.com/darpan31patel-wq/bapas-diary/releases/download/backup/';
const CHANGES_FROM = 'https://api.github.com/repos/darpan31patel-wq/bapas-diary/commits?sha=main&per_page=100&since=';

function setup() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('deliver').timeBased().atHour(8).nearMinute(30).everyDays(1).inTimezone(TZ).create();
  ScriptApp.newTrigger('deliverLate').timeBased().atHour(10).nearMinute(30).everyDays(1).inTimezone(TZ).create();
  ScriptApp.newTrigger('syncBank').timeBased().everyHours(2).create();
  ScriptApp.newTrigger('nightlyBackup').timeBased().atHour(3).everyDays(1).inTimezone(TZ).create();
  logSheet_('Deliveries');   // makes the log sheet now, so you can find it in Drive
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
      logRow_('Deliveries', [today, used ? 'Backup' : 'Missing', used ? "Fresh picture didn't come, backup used" : 'No fresh picture and no backup']);
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
  logRow_('Deliveries', [today, 'Fresh', isLastTry ? 'Arrived at the 10:30 try' : 'Arrived at 8:30']);
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

// ---- The log sheet ----
function logSheet_(tab) {
  const props = PropertiesService.getScriptProperties();
  let ss = null;
  try { ss = SpreadsheetApp.openById(props.getProperty('logSheetId')); } catch (e) {}
  if (!ss) {
    ss = SpreadsheetApp.create(LOG_SHEET_NAME);
    props.setProperty('logSheetId', ss.getId());
    const heads = { Deliveries: ['When', 'For the day', 'Fresh or backup', 'Details'], Changes: ['When', 'What changed', 'Link'] };
    Object.keys(heads).forEach((name, i) => {
      const sh = i ? ss.insertSheet(name) : ss.getSheets()[0].setName(name);
      sh.getRange(1, 1, 1, heads[name].length).setValues([heads[name]]).setFontWeight('bold').setBackground('#f3e8d6');
      sh.setFrozenRows(1);
      sh.setColumnWidth(1, 150);
    });
  }
  return ss.getSheetByName(tab);
}

// Newest rows go at the top, under the headings. Never stops a delivery if the sheet can't be reached.
function logRow_(tab, cells, when) {
  try {
    const sh = logSheet_(tab);
    sh.insertRowAfter(1);
    sh.getRange(2, 1, 1, cells.length + 1).setValues([[when || new Date()].concat(cells)]).setFontWeight('normal').setBackground(null);
  } catch (e) { console.log('Log sheet: ' + e); }
}

// Each change made to Bapa's Diary on GitHub since last time (not the daily picture commits).
function logChanges_() {
  const props = PropertiesService.getScriptProperties();
  const since = props.getProperty('changesSince') || new Date(Date.now() - 86400000).toISOString();
  const res = UrlFetchApp.fetch(CHANGES_FROM + encodeURIComponent(since), { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) { console.log('GitHub changes: ' + res.getResponseCode()); return; }
  let newest = since;
  JSON.parse(res.getContentText()).reverse().forEach(c => {
    const when = c.commit.committer.date, line = c.commit.message.split('\n')[0];
    if (new Date(when) <= new Date(since)) return;
    if (new Date(when) > new Date(newest)) newest = when;
    if (/^(Bapa's Diary for|Preview for)/.test(line)) return;
    logRow_('Changes', [line, c.html_url], new Date(when));
  });
  props.setProperty('changesSince', newest);
}

// ---- Nightly backups into Drive ----
// 3am: a folder named with the date inside "Bapa's Diary backups", with a copy of every Google script you own
// (this one and any others), the log sheet and the packed picture maker. "Run without GitHub" inside it always
// has the newest picture maker and the guide to running it on your Mac (RUN-ON-MAC.txt).
function nightlyBackup() {
  const today = Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd');
  try { logChanges_(); } catch (e) { console.log('Changes: ' + e); }
  const root = child_(DriveApp.getRootFolder(), BACKUPS_NAME);
  const night = child_(root, today);
  const saved = [], problems = [];
  const scripts = DriveApp.getFilesByType(MimeType.GOOGLE_APPS_SCRIPT);
  while (scripts.hasNext()) {
    const f = scripts.next();
    if (f.isTrashed() || / \(backup \d{4}-\d{2}-\d{2}\)$/.test(f.getName())) continue;   // never a backup of a backup
    const name = f.getName() + ' (backup ' + today + ')';
    try { f.makeCopy(name, night); saved.push(name); } catch (e) { problems.push(name + ': ' + e); }
  }
  const logId = PropertiesService.getScriptProperties().getProperty('logSheetId');
  if (logId) {
    try { DriveApp.getFileById(logId).makeCopy(LOG_SHEET_NAME + ' (backup ' + today + ')', night); saved.push(LOG_SHEET_NAME); }
    catch (e) { problems.push(LOG_SHEET_NAME + ': ' + e); }
  }
  const offline = child_(root, 'Run without GitHub');
  [['bapas-diary-code.zip', night], ['bapas-diary-code.zip', offline], ['models.zip', offline], ['RUN-ON-MAC.txt', offline]].forEach(([name, into]) => {
    try {
      if (name === 'models.zip' && alive_(into, name)) return;   // the face models never change
      const r = UrlFetchApp.fetch(PACKED_FROM + name, { muteHttpExceptions: true });
      if (r.getResponseCode() !== 200) { problems.push(name + ': GitHub said ' + r.getResponseCode()); return; }
      const old = into.getFilesByName(name);
      while (old.hasNext()) old.next().setTrashed(true);
      into.createFile(r.getBlob().setName(name));
      if (into === night) saved.push(name);
    } catch (e) { problems.push(name + ': ' + e); }
  });
  const nights = [];
  const it = root.getFolders();
  while (it.hasNext()) { const f = it.next(); if (!f.isTrashed() && /^\d{4}-\d{2}-\d{2}$/.test(f.getName())) nights.push(f); }
  nights.sort((a, b) => a.getName() < b.getName() ? 1 : -1).slice(KEEP_NIGHTS).forEach(f => f.setTrashed(true));
  console.log('Backup ' + today + ': ' + saved.length + ' saved' + (problems.length ? ', problems: ' + problems.join('; ') : ''));
  if (problems.length) MailApp.sendEmail(Session.getEffectiveUser().getEmail(), "Bapa's Diary: last night's backup was not complete",
    'Saved: ' + (saved.join(', ') || 'nothing') + '\n\nProblems:\n' + problems.join('\n'));
}

function child_(parent, name) {
  const it = parent.getFoldersByName(name);
  while (it.hasNext()) { const f = it.next(); if (!f.isTrashed()) return f; }
  return parent.createFolder(name);
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
