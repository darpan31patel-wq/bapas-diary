"""rclone.conf for drive.yml from the RCLONE_DRIVE_TOKEN secret: either the {"access_token": ...} line older rclone
prints, or the eyJ... line newer rclone prints (base64 of {"client_id", "client_secret", "token"}).
With the RCLONE_CLIENT_ID and RCLONE_CLIENT_SECRET secrets (Darpan's own Google login, 25 Oct 2026: rclone's shared
one hits Google's limits and is retired during 2026) it uses his login, and sees the whole Drive (scope drive), so the
files the shared login made stay in reach; without them, the shared login as before."""
import base64, json, os

t = os.environ['TOKEN'].strip()
if not t.startswith('{'):
    t = json.loads(base64.urlsafe_b64decode(t + '=' * (-len(t) % 4)))['token']
cid, secret = os.environ.get('CLIENT_ID', '').strip(), os.environ.get('CLIENT_SECRET', '').strip()
own = f'client_id = {cid}\nclient_secret = {secret}\n' if cid and secret else ''
print(f'[gdrive]\ntype = drive\nscope = {"drive" if own else "drive.file"}\n{own}token = {t}')
