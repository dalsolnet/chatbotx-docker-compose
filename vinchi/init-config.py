#!/usr/bin/env python3
"""Generate a local secret file once. Does not install, deploy, or call any API."""
import argparse
import os
from pathlib import Path
import re
import secrets

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domain',required=True,help='Public DNS name; no https:// or path')
    args=parser.parse_args()
    domain=args.domain.lower()
    if len(domain)>253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}',domain) or domain.endswith(('.example','.test','.invalid','.local','.internal')) or domain=='example.com':
        parser.error('Use a real DNS hostname you control.')
    target=Path(__file__).resolve().parent/'.env'
    values={'CHATBOTX_DOMAIN':domain,'CHATBOTX_VERSION':'1.10.0'}
    for name in ['POSTGRES_PASSWORD','BETTER_AUTH_SECRET','ENCRYPTION_KEY','JAVASCRIPT_EXECUTOR_TOKEN','REALTIME_BROADCAST_SECRET','S3_SECRET_ACCESS_KEY','TELEGRAM_WEBHOOK_SECRET']:
        values[name]=secrets.token_hex(32)
    values.update(TELEGRAM_BOT_ID='disabled',SMTP_FROM='',SMTP_SERVER='')
    try:
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as out:
            out.write('# Local secrets. Never upload or commit this file.\n')
            for key,value in values.items():out.write(f"{key}='{value}'\n")
    except FileExistsError:
        parser.error('.env already exists; refusing to overwrite encryption keys.')
    print('Created .env with private permissions. Set SMTP_FROM and SMTP_SERVER locally before validation.')

if __name__=='__main__':main()
