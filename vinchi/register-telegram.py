#!/usr/bin/env python3
"""Run ONLY for your staging bot after connecting it inside ChatbotX."""
import getpass
import json
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlencode

def main():
    config={}
    for line in (Path(__file__).resolve().parent/'.env').read_text().splitlines():
        if not line or line.startswith('#') or '=' not in line:continue
        key,value=line.split('=',1);config[key]=value.strip().strip("'\"")
    bot_id=config.get('TELEGRAM_BOT_ID','')
    if not bot_id.isdigit():raise ValueError('Set TELEGRAM_BOT_ID to the numeric staging bot ID and recreate proxy first.')
    domain=config['CHATBOTX_DOMAIN'];secret=config['TELEGRAM_WEBHOOK_SECRET']
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,256}',secret):raise ValueError('Invalid webhook secret.')
    token=getpass.getpass('Staging bot token (hidden): ')
    if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+',token):raise ValueError('Invalid bot token.')
    def call(method,payload):
        req=urllib.request.Request(f'https://api.telegram.org/bot{token}/{method}',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        # Never print HTTP errors: their URL contains the bot token.
        try:
            with urllib.request.urlopen(req,timeout=20) as response:data=json.load(response)
        except Exception:raise RuntimeError('Telegram request failed. Verify connection and token.') from None
        if not data.get('ok'):raise RuntimeError('Telegram rejected the request.')
        return data['result']
    if str(call('getMe',{})['id'])!=bot_id:raise ValueError('Token does not match TELEGRAM_BOT_ID.')
    url=f'https://{domain}/integrations/telegram/webhook?'+urlencode({'botId':bot_id})
    call('setWebhook',{'url':url,'secret_token':secret,'drop_pending_updates':False})
    info=call('getWebhookInfo',{})
    if info.get('url')!=url:raise RuntimeError('Webhook URL verification failed.')
    print('Webhook URL registered. Now test a real inbound message and verify unsigned requests return 403.')

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,KeyError,FileNotFoundError) as error:
        print(str(error),file=sys.stderr);sys.exit(1)
