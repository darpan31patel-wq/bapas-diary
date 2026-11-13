#!/usr/bin/env bash
# Darpan, 9 Nov 2026 (after GitHub suspended his account for three days): "I never ever want to be in a situation where
# I'm reliant on one thing." One gentle nightly run that puts a copy of every part of Bapa's Diary in a second company:
#   code      -> GitLab (every branch, every night, only what changed) and a full git bundle on Sundays to Drive + R2
#   database  -> bapas.db (photos, days, News articles) to Google Drive and the private R2 bucket bapas-diary-backups
#   Studio    -> the Studio changes log and the missed searches / feedback (read through the website) to Drive
#   sign ups  -> the weekly darshan email list (Resend) to Drive only (people's emails never go to R2)
#   releases  -> the GitHub release files the builds need (database, faces, tags, bank...), Sundays, changes only
#   checks    -> emails Darpan only when something is wrong: a backup step failed, the 2pm picture on GitHub is older
#                than a day, or the Drive Bank of ready made 2pm pictures has fewer than 30 days left
# It only READS the 2pm picture chain (release today, Drive Bank); it never changes make.py, daily.yml, bank.yml or
# deliver.gs. Keeps the last 7 nights plus the first of every month. Never prints a secret.
set -uo pipefail
DAY=$(date -u +%F); DOW=$(date -u +%u); TODAY_UK=$(TZ=Europe/London date +%F)
DRIVE="gdrive:Bapa's Diary backups/Everything"
BUCKET=bapas-diary-backups
PROBLEMS=()
problem() { echo "::warning::$1"; PROBLEMS+=("$1"); }
step() { echo; echo "== $1"; }

drive_ls() { rclone lsf "$DRIVE/$1"; }
drive_rm() { rclone deletefile "$DRIVE/$1/$2"; }
r2() { aws s3 "$@" --endpoint-url "$R2" --only-show-errors; }
r2_ls() { aws s3 ls "s3://$BUCKET/$1/" --endpoint-url "$R2" | awk '{print $4}'; }
r2_rm() { r2 rm "s3://$BUCKET/$1/$2"; }
keep_recent() {   # $1 = drive or r2, $2 = folder; names start YYYY-MM-DD; keeps 7 nights + the 1st of each month
  local cut f d; cut=$(date -u -d '7 days ago' +%F)
  "$1_ls" "$2" | while read -r f; do
    d=${f:0:10}; [[ $d =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || continue
    if [[ $d < $cut && ${d:8:2} != 01 ]]; then "$1_rm" "$2" "$f" && echo "  removed old copy $f"; fi
  done
}
drive_keep() { keep_recent drive "$1"; }
r2_keep() { keep_recent r2 "$1"; }

R2_OK=0
step "R2 bucket $BUCKET (private, no web address)"
if aws s3api head-bucket --bucket "$BUCKET" --endpoint-url "$R2" 2>/dev/null || aws s3api create-bucket --bucket "$BUCKET" --endpoint-url "$R2" >/dev/null 2>&1; then
  R2_OK=1; echo "ready"
else
  problem "R2 backup bucket missing. In Cloudflare: R2, Create bucket, name it $BUCKET, leave it private."
fi

step "Database (bapas.db with News articles)"
if gh release download database -p bapas.db.gz -O bapas.db.gz --clobber; then
  ls -la bapas.db.gz
  rclone copyto bapas.db.gz "$DRIVE/database/$DAY bapas.db.gz" && drive_keep database || problem "Database copy to Drive failed"
  if [ $R2_OK = 1 ]; then r2 cp bapas.db.gz "s3://$BUCKET/database/$DAY-bapas.db.gz" && r2_keep database || problem "Database copy to R2 failed"; fi
else problem "Could not fetch the database from GitHub"; fi

step "Code: every branch and tag"
if [ -d mirror.git ]; then git -C mirror.git remote set-url origin "$GH_URL"; else git clone -q --mirror "$GH_URL" mirror.git; fi
if git -C mirror.git fetch -q --prune origin '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*'; then
  echo "$(git -C mirror.git for-each-ref | wc -l) branches and tags"
  if [ -n "${GITLAB_TOKEN:-}" ]; then
    # Darpan only makes the account and one token; this finds his name, makes the private project bapas-diary the
    # first time, copies every branch, and keeps the Cloudflare keys the emergency deploy (.gitlab-ci.yml) needs in it
    echo "::add-mask::$GITLAB_TOKEN"
    gl() { curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "$@"; }
    GLAPI=https://gitlab.com/api/v4
    GLUSER=$(gl "$GLAPI/user" | jq -r '.username // empty')
    REPO=${GITLAB_REPO:-$GLUSER/bapas-diary}
    ENC=$(jq -rn --arg r "$REPO" '$r|@uri')
    if [ -z "$GLUSER" ]; then problem "GitLab would not open with the GITLAB_TOKEN secret (wrong or expired token)"
    else
      [ "$(gl -o /dev/null -w '%{http_code}' "$GLAPI/projects/$ENC")" = 200 ] || \
        gl -X POST "$GLAPI/projects" --data-urlencode "path=${REPO#*/}" --data-urlencode "name=Bapas Diary" \
          -d visibility=private -d initialize_with_readme=false | jq -c '{made: .path_with_namespace, error: .message}'
      GL="https://oauth2:$GITLAB_TOKEN@gitlab.com/$REPO.git"
      if git -C mirror.git push -q --prune "$GL" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' 2>&1 | sed "s#$GITLAB_TOKEN#***#g"; [ "${PIPESTATUS[0]}" = 0 ]; then
        echo "GitLab copy up to date: gitlab.com/$REPO"
      else problem "GitLab copy failed"; fi
      for v in CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do   # kept masked in GitLab, never printed
        gl -o /dev/null -X PUT "$GLAPI/projects/$ENC/variables/$v" --data-urlencode "value=${!v}" -d masked=true -d raw=true \
          -w '%{http_code}' | grep -q 200 || gl -o /dev/null -X POST "$GLAPI/projects/$ENC/variables" -d "key=$v" \
          --data-urlencode "value=${!v}" -d masked=true -d raw=true || problem "Could not keep $v in GitLab"
      done
    fi
  else
    echo "GitLab copy waits for the GITLAB_TOKEN secret"
  fi
  if [ "$DOW" = 7 ] || [ "${FULL:-}" = yes ]; then
    git -C mirror.git bundle create "../$DAY-bapas-diary.bundle" --all && ls -la "$DAY-bapas-diary.bundle"
    rclone copyto "$DAY-bapas-diary.bundle" "$DRIVE/code/$DAY bapas-diary.bundle" || problem "Weekly code copy to Drive failed"
    [ $R2_OK = 1 ] && { r2 cp "$DAY-bapas-diary.bundle" "s3://$BUCKET/code/$DAY-bapas-diary.bundle" || problem "Weekly code copy to R2 failed"; }
    rm -f "$DAY-bapas-diary.bundle"
    # four Sundays are enough for the full copies (GitLab holds every day in between)
    rclone lsf "$DRIVE/code" | sort | head -n -4 | while read -r f; do rclone deletefile "$DRIVE/code/$f"; done
    [ $R2_OK = 1 ] && r2_ls code | sort | head -n -4 | while read -r f; do r2_rm code "$f"; done
  fi
else problem "Could not read the code from GitHub"; fi

# the emergency publish on GitLab needs site/latest-site.zip in R2; if a deploy could not put it there, use Drive's copy
if [ $R2_OK = 1 ] && ! aws s3 ls "s3://$BUCKET/site/latest-site.zip" --endpoint-url "$R2" >/dev/null 2>&1; then
  rclone copyto "$DRIVE/site/latest site.zip" latest-site.zip && r2 cp latest-site.zip "s3://$BUCKET/site/latest-site.zip" \
    && echo "site/latest-site.zip put in R2 from Drive" || problem "No site copy in R2 for the emergency publish"
  rm -f latest-site.zip
fi
[ $R2_OK = 1 ] && r2_keep site   # the site copies each deploy leaves (website-deploy.yml)

step "GitHub releases the website and 2pm picture are built from (Sundays: only files that changed)"
# database, faces, deep tags, image search, today, bank, backup ... everything except mockups and tests. Drive and R2
# keep releases/TAG/FILE; releases/list.txt remembers each file's size and date so unchanged files are never fetched twice.
if [ "$DOW" = 7 ] || [ "${FULL:-}" = yes ]; then
  rclone copyto "$DRIVE/releases/list.txt" have.txt 2>/dev/null || : > have.txt
  gh api "repos/$GITHUB_REPOSITORY/releases?per_page=100" --paginate \
    --jq '.[] | select(.tag_name | test("mockup|-test$|check") | not) | .tag_name as $t | .assets[] | "\($t)/\(.name)\t\(.size)\t\(.updated_at)"' > now.txt
  n=0; while IFS=$'\t' read -r path size upd; do
    grep -qxF "$path"$'\t'"$size"$'\t'"$upd" have.txt && continue
    tag=${path%%/*}; name=${path#*/}
    if gh release download "$tag" -p "$name" -O asset.bin --clobber; then
      rclone copyto asset.bin "$DRIVE/releases/$path" || problem "Release file $path to Drive failed"
      [ $R2_OK = 1 ] && { r2 cp asset.bin "s3://$BUCKET/releases/$path" || problem "Release file $path to R2 failed"; }
      n=$((n+1))
    else problem "Could not fetch release file $path"; fi
    rm -f asset.bin
  done < now.txt
  rclone copyto now.txt "$DRIVE/releases/list.txt"
  echo "$n release files copied, $(wc -l < now.txt) kept in all"
fi

step "Studio changes log, missed searches and feedback (read through the website itself)"
# the Cloudflare key may not read the stores, so these come the same way Darpan reads them: the Studio with its
# password, /api/missed and /api/feedback with the MISSED_KEY word. Nothing is printed but the counts.
SITE=https://bapas-diary.com
if [ -n "${STUDIO_PASSWORD:-}" ]; then
  printf %s "$STUDIO_PASSWORD" | curl -s -o /dev/null -c jar.txt --data-urlencode password@- "$SITE/darpan/api/log"
  if curl -s -f -b jar.txt "$SITE/darpan/api/log" -o studio-log.json && jq -e '.entries' studio-log.json >/dev/null; then
    echo "Studio changes log: $(jq '.entries | length' studio-log.json) entries"
    gzip -f studio-log.json && { rclone copyto studio-log.json.gz "$DRIVE/studio/$DAY studio-log.json.gz" || problem "Studio log copy to Drive failed"; }
  else problem "Could not open the Studio changes log (the STUDIO_PASSWORD secret may not match the website)"; fi
  rm -f jar.txt
fi
if [ -n "${MISSED_KEY:-}" ]; then
  for what in missed feedback; do
    if printf %s "$MISSED_KEY" | curl -s -f -G --data-urlencode "key@-" "$SITE/api/$what" -o "$what.json" && jq -e . "$what.json" >/dev/null; then
      echo "$what: saved"; gzip -f "$what.json"
      rclone copyto "$what.json.gz" "$DRIVE/studio/$DAY $what.json.gz" || problem "$what copy to Drive failed"
    else problem "Could not read $what from the website"; fi
  done
fi
drive_keep studio

step "Weekly darshan email sign ups (Resend), Drive only"
if [ -n "${RESEND_API_KEY:-}" ]; then
  python3 - <<'PY' > signups.json || problem "Could not read the email sign up list"
import json, os, urllib.request
h = {'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'], 'User-Agent': 'bapas-diary-backup'}
get = lambda p: json.load(urllib.request.urlopen(urllib.request.Request('https://api.resend.com' + p, headers=h), timeout=60))
out = {}
for a in get('/audiences').get('data', []):
    out[a['name']] = get(f"/audiences/{a['id']}/contacts").get('data', [])
json.dump(out, open('/dev/stdout', 'w'), indent=1)
PY
  [ -s signups.json ] && { gzip -f signups.json; rclone copyto signups.json.gz "$DRIVE/signups/$DAY signups.json.gz" && drive_keep signups || problem "Sign up list copy to Drive failed"; }
fi

step "Standby website on Netlify (only when the site has changed)"
# Darpan, 13 Nov 2026: a second home for the pages, so bapas-diary.netlify.app (or bapas-diary-standby) is always ready to
# take over if Cloudflare ever fails. The plain pages work there; the Studio, sign up and feedback need Cloudflare.
if [ -n "${NETLIFY_TOKEN:-}" ]; then
  echo "::add-mask::$NETLIFY_TOKEN"
  nl() { curl -s -H "Authorization: Bearer $NETLIFY_TOKEN" "$@"; }
  NAPI=https://api.netlify.com/api/v1
  SITE_ID=$(nl "$NAPI/sites?filter=all" | jq -r '[.[] | select(.name|test("^bapas-diary"))][0].id // empty')
  if [ -z "$SITE_ID" ]; then
    for name in bapas-diary bapas-diary-standby bapas-diary-backup; do
      SITE_ID=$(nl -X POST -H 'Content-Type: application/json' -d "{\"name\":\"$name\"}" "$NAPI/sites" | jq -r '.id // empty')
      [ -n "$SITE_ID" ] && break
    done
  fi
  if [ -z "$SITE_ID" ]; then problem "Netlify would not open with the NETLIFY_TOKEN secret"
  elif rclone copyto "$DRIVE/site/latest site.zip" site.zip; then
    NOW=$(md5sum site.zip | cut -c1-32); WAS=$(rclone cat "$DRIVE/site/netlify.txt" 2>/dev/null)
    if [ "$NOW" = "$WAS" ]; then echo "Netlify standby already has this site"
    else
      rm -rf standby && mkdir standby && unzip -q site.zip 'out/*' -d standby && (cd standby/out && zip -qr ../../standby.zip .)
      URL=$(nl -X POST -H 'Content-Type: application/zip' --data-binary @standby.zip --max-time 1800 "$NAPI/sites/$SITE_ID/deploys" | jq -r '.ssl_url // .url // empty')
      if [ -n "$URL" ]; then echo "Netlify standby updated: $URL"; printf %s "$NOW" | rclone rcat "$DRIVE/site/netlify.txt"
      else problem "Netlify standby update failed"; fi
      rm -rf standby standby.zip
    fi
    rm -f site.zip
  else problem "No site copy in Drive for the Netlify standby"; fi
fi

step "Checks on the 2pm picture (reading only)"
made=$(gh release download today -p date.txt -O - 2>/dev/null | tr -d '[:space:]')
echo "2pm picture on GitHub was last made for: ${made:-unknown}"
if [ -z "$made" ] || [[ $made < $(TZ=Europe/London date -d yesterday +%F) ]]; then
  problem "The 2pm picture on GitHub was last made for ${made:-an unknown day}. The send uses the Drive Bank until it runs again."
fi
left=$(rclone lsf "gdrive:FamilyPhotos/Bank" --include '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].jpg' 2>/dev/null | cut -c1-10 | awk -v t="$TODAY_UK" '$0>=t' | sort -u | wc -l)
echo "Drive Bank: $left ready made 2pm pictures from today on"
[ "$left" -ge 30 ] || problem "The Drive Bank has only $left ready made 2pm pictures left."

step "Summary"
printf '%s\n' "Backup night $DAY" "${PROBLEMS[@]:-everything copied}" | tee summary.txt
rclone copyto summary.txt "$DRIVE/last night.txt" || true
if [ ${#PROBLEMS[@]} -gt 0 ] && [ -n "${RESEND_API_KEY:-}" ]; then
  python3 - "${PROBLEMS[@]}" <<'PY' || true
import json, os, sys, urllib.request
items = ''.join(f'<li>{p}</li>' for p in sys.argv[1:])
body = {'from': "Bapa's Diary <hello@bapas-diary.com>", 'to': [os.environ.get('SUMMARY_TO') or 'hello@bapas-diary.com'],
        'subject': "Bapa's Diary backups need a look",
        'html': f"<p>Jai Swaminarayan 🙏🏽</p><p>Last night's backup found:</p><ul>{items}</ul><p>Everything else was copied. Just tell Claude.</p>"}
urllib.request.urlopen(urllib.request.Request('https://api.resend.com/emails', data=json.dumps(body).encode(),
    headers={'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'], 'Content-Type': 'application/json', 'User-Agent': 'bapas-diary-backup'}), timeout=60)
print('email sent')
PY
fi
exit 0
