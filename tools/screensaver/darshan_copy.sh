#!/usr/bin/env bash
# Copies the London mandir's daily darshan photos for yesterday and today (London time) into the website's own photo
# store (R2, photos.bapas-diary.com/darshan/), so the screensaver on bapas-diary.com shows them from our own copy and
# never from the mandir's site (Darpan, 29 Oct 2026: "completely self-reliant"). Run each morning by
# .github/workflows/screensaver-darshan.yml. A photo already in R2 is never fetched again, so the mandir is asked only
# for what is new, one file at a time, a second apart. Also one Sarangpur mandir photo a day (tools/screensaver/sarangpur.py).
# Writes darshan/list.json: the photos there for the two days, as the page's own check would find them.
# Needs: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY for R2, R2 (endpoint) and BUCKET.
set -u
base=https://londonmandir.baps.org/wp-content/themes/BAPS/images/daily-murti
here=$(cd "$(dirname "$0")/../.." && pwd)
codes=$(sed -n 's/^const PHOTO_CODES = \[\(.*\)\];.*/\1/p' "$here/site/screensaver/index.html" | tr -d '",')
[ -n "$codes" ] || { echo "::error::no PHOTO_CODES in site/screensaver/index.html"; exit 1; }
work=$(mktemp -d)
aws s3 ls "s3://$BUCKET/darshan/" --recursive --endpoint-url "$R2" | awk '{print $4}' | sed 's#^darshan/##' > "$work/have.txt" || : > "$work/have.txt"
echo "in R2 already: $(wc -l < "$work/have.txt") darshan files"
put() {   # put <local file> <key under darshan/> <content type> <cache control>
  aws s3 cp "$1" "s3://$BUCKET/darshan/$2" --endpoint-url "$R2" --only-show-errors --content-type "$3" --cache-control "$4"
}
got=()
grab() {   # grab <path under daily-murti>: from R2 if there, else from the mandir into R2
  if grep -qxF "$1" "$work/have.txt"; then got+=("$1"); return; fi
  local f="$work/$(echo "$1" | tr / _)"
  if curl -sf --retry 2 -A "Mozilla/5.0" -o "$f" "$base/$1" && [ "$(file -b --mime-type "$f")" = image/jpeg ]; then
    put "$f" "$1" image/jpeg "public, max-age=31536000, immutable" && got+=("$1") && echo "copied $1"
  fi
  sleep 1
}
for day in "$(TZ=Europe/London date -d yesterday +%Y%m%d)" "$(TZ=Europe/London date +%Y%m%d)"; do
  for c in $codes; do grab "$day/${c}_${day:6:2}.jpg"; done
done
grab others/msm-static.jpg
grab others/ss-static.jpg
printf '%s\n' "${got[@]}" | jq -R . | jq -sc . > "$work/list.json"
put "$work/list.json" list.json application/json "public, max-age=300"
echo "::notice::darshan photos for the two days: ${#got[@]} ($(cat "$work/list.json"))"

# Sarangpur: the central shrine photo of the newest day, or nothing (the kit's rule)
mkdir -p "$work/sar"
if python3 "$here/tools/screensaver/sarangpur.py" "$work/sar" && [ -f "$work/sar/sarangpur/today.json" ]; then
  img=$(jq -r .img "$work/sar/sarangpur/today.json")
  put "$work/sar/$img" "sarangpur/$(basename "$img")" image/jpeg "public, max-age=31536000, immutable"
  put "$work/sar/sarangpur/today.json" sarangpur/today.json application/json "public, max-age=300"
  echo "Sarangpur: $(cat "$work/sar/sarangpur/today.json")"
fi
rm -rf "$work"
