"""Static safety contracts; does NOT claim Docker/Caddy/runtime verification."""
from pathlib import Path
import ast
import json
import os
import shutil
import subprocess
import tempfile
import yaml

p=Path(__file__).resolve().parents[1]
config=yaml.safe_load((p/'compose.yaml').read_text());services=config['services']
assert set(n for n,s in services.items() if s.get('ports'))=={'proxy'}
assert set(services['proxy']['ports'])=={'80:80','443:443'}
assert 'adminer' not in services and 'mailhog' not in services
for n in ['builder','worker','realtime','migrate']:
    env=services[n]['environment']
    assert env['RUN_DB_SEED']=='false' and env['RUN_DB_MIGRATE']=='false'
    assert env['NEXT_PUBLIC_EDITION']=='community'
    assert env['S3_ENDPOINT'].startswith('https://') and 'S3_ENPOINT' not in env
    assert 'latest' not in services[n]['image']
assert services['migrate']['profiles']==['maintenance']
assert services['migrate']['command']==['migrate']
assert config['networks']['javascript-executor-network']['internal'] is True
assert services['javascript-executor']['read_only'] is True
assert services['javascript-executor']['cap_drop']==['ALL']
assert 'set download' in services['filesystem-init']['entrypoint'][-1]
assert 'pnpm dlx' not in services['realtime']['entrypoint'][-1]
proxy=(p/'Caddyfile').read_text()
assert 'X-Telegram-Bot-Api-Secret-Token' in proxy and 'query botId=' in proxy
assert 'respond "Webhook verification required" 403' in proxy
assert 'handle_path /ws/*' in proxy
assert '@storage path /chatbotx /chatbotx/*' in proxy
assert json.loads((p/'sources.lock.json').read_text())['deployment']['runtimeValidated'] is False
for filename in ['init-config.py','register-telegram.py']:ast.parse((p/filename).read_text())
with tempfile.TemporaryDirectory() as directory:
    script=Path(directory)/'init-config.py';shutil.copy(p/'init-config.py',script)
    assert subprocess.run(['python3',str(script),'--domain','http://bad'],capture_output=True).returncode!=0
    assert subprocess.run(['python3',str(script),'--domain','staging.my-company.com'],capture_output=True).returncode==0
    target=Path(directory)/'.env';original=target.read_bytes()
    assert os.stat(target).st_mode & 0o777==0o600
    assert b"SMTP_SERVER=''" in original and b"TELEGRAM_BOT_ID='disabled'" in original
    assert subprocess.run(['python3',str(script),'--domain','staging.my-company.com'],capture_output=True).returncode!=0
    assert target.read_bytes()==original
print('PASS: static deployment safety contracts and secret-generator behavior. Docker and provider calls not run.')
