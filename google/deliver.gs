/**
 * Bapa's Diary: puts today's picture into your Google Drive at 8:30am (UK time).
 *
 * How to set up (once):
 *   1. Paste this whole file into a new project at https://script.google.com
 *   2. Choose "setup" in the function menu at the top and press Run.
 *   3. Google asks for permission: Review permissions, pick your account, Advanced,
 *      "Go to Bapa's Diary (unsafe)" (it's your own script), then Allow.
 * That's it. A folder called "Bapa's Diary" appears in your Drive and fills every morning.
 */

const FOLDER_NAME = "Bapa's Diary";
const SOURCE = 'https://github.com/darpan31patel-wq/bapas-diary/releases/download/today/';
const TZ = 'Europe/London';

function setup() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('deliver').timeBased().atHour(8).nearMinute(30).everyDays(1).inTimezone(TZ).create();
  ScriptApp.newTrigger('deliverLate').timeBased().atHour(10).nearMinute(30).everyDays(1).inTimezone(TZ).create();
  folder_();
  deliver();   // if today's picture is already made, it arrives straight away
}

/** 8:30am: copy today's picture into the folder (does nothing if it's already there). */
function deliver() {
  return deliver_(false);
}

/** 10:30am: second try, and an email if today's picture never turned up. */
function deliverLate() {
  return deliver_(true);
}

function deliver_(isLastTry) {
  const now = new Date();
  const today = Utilities.formatDate(now, TZ, 'yyyy-MM-dd');
  const name = Utilities.formatDate(now, TZ, 'd MMMM yyyy') + '.png';
  const folder = folder_();
  const same = folder.getFilesByName(name);
  while (same.hasNext()) if (!same.next().isTrashed()) return true;   // already delivered (a deleted copy doesn't count)

  const stamp = UrlFetchApp.fetch(SOURCE + 'date.txt', { muteHttpExceptions: true });
  if (stamp.getResponseCode() !== 200 || stamp.getContentText().trim() !== today) {
    console.log("Today's picture isn't ready yet");
    if (isLastTry) {
      MailApp.sendEmail(Session.getEffectiveUser().getEmail(), "Bapa's Diary didn't arrive today",
        'The picture for ' + name.replace('.png', '') + " wasn't ready by 10:30am. " +
        'You can see what happened at https://github.com/darpan31patel-wq/bapas-diary/actions');
    }
    return false;
  }
  const picture = UrlFetchApp.fetch(SOURCE + 'bapas-diary.png').getBlob().setName(name);
  folder.createFile(picture);
  return true;
}

function folder_() {
  const found = DriveApp.getFoldersByName(FOLDER_NAME);
  return found.hasNext() ? found.next() : DriveApp.createFolder(FOLDER_NAME);
}
