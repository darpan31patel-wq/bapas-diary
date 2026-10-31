# Do the BAPS videos have chapters or timestamps in their descriptions? (Video moments, Darpan 31 Oct 2026: "yes moments")
for id in "$@"; do
  html=$(curl -s -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36' -H 'Accept-Language: en-GB' -b 'SOCS=CAI; CONSENT=YES+1' "https://www.youtube.com/watch?v=$id")
  desc=$(printf %s "$html" | grep -o '"shortDescription":"[^"]*' | head -1 | cut -c21-)
  echo "== $id bytes=${#html} chapters=$(printf %s "$html" | grep -o '"chapterRenderer"' | wc -l) markers=$(printf %s "$html" | grep -o 'macroMarkersListItemRenderer' | wc -l) stamps=$(printf %s "$desc" | grep -oE '(^|\\n)[0-9]{1,2}:[0-9]{2}(:[0-9]{2})?' | wc -l)"
  printf '%s\n' "${desc:0:500}"
done
