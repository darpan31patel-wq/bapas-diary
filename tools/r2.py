"""Save photos from the website's R2 bucket (bapas-diary-photos), for website tools only. Needs CF_TOKEN and
CF_ACCOUNT (the Cloudflare secrets): the S3 key id is the token's id and the secret is sha256 of the token."""
import hashlib, json, os, urllib.request

import boto3

_s3 = None


def client():
    global _s3
    if _s3 is None:
        tok, acct = os.environ['CF_TOKEN'], os.environ['CF_ACCOUNT']
        req = urllib.request.Request('https://api.cloudflare.com/client/v4/user/tokens/verify',
                                     headers={'Authorization': f'Bearer {tok}'})
        kid = json.load(urllib.request.urlopen(req))['result']['id']
        _s3 = boto3.client('s3', endpoint_url=f'https://{acct}.r2.cloudflarestorage.com', region_name='auto',
                           aws_access_key_id=kid, aws_secret_access_key=hashlib.sha256(tok.encode()).hexdigest())
    return _s3


def get(key, path):
    """Save one key to path (skipped when it is already there). True when the photo is there."""
    if os.path.exists(path):
        return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        client().download_file(os.environ.get('BUCKET', 'bapas-diary-photos'), key, path)
        return True
    except Exception:
        return False
