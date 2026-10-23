"""rclone.conf for drive.yml from the RCLONE_DRIVE_TOKEN secret: either the {"access_token": ...} line older rclone
prints, or the eyJ... line newer rclone prints (base64 of {"client_id", "client_secret", "token"})."""
import base64, json, os

t = os.environ['TOKEN'].strip()
if not t.startswith('{'):
    t = json.loads(base64.urlsafe_b64decode(t + '=' * (-len(t) % 4)))['token']
print(f'[gdrive]\ntype = drive\nscope = drive.file\ntoken = {t}')
