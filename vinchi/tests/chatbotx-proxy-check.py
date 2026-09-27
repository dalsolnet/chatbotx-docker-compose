"""Run with a trusted Caddy 2.10.2 binary path. Uses only loopback and synthetic data."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

class Stub(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200);self.end_headers();self.wfile.write(self.path.encode())
    do_POST=do_GET
    def log_message(self,*args):pass

binary=str(Path(sys.argv[1]).resolve())
stub=ThreadingHTTPServer(('127.0.0.1',0),Stub)
threading.Thread(target=stub.serve_forever,daemon=True).start()
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));proxy_port=sock.getsockname()[1]
env={**os.environ,'CHATBOTX_DOMAIN':f'http://127.0.0.1:{proxy_port}','TELEGRAM_BOT_ID':'123','TELEGRAM_WEBHOOK_SECRET':'test-only-012345678901234567890123456789'}
source=(Path(__file__).resolve().parents[1]/'Caddyfile').read_text()
for upstream in ['builder:3000','realtime:1999','filesystem:9000']:
    source=source.replace(upstream,f'127.0.0.1:{stub.server_port}')
source='{\n admin off\n auto_https off\n persist_config off\n}\n'+source
try:
    with tempfile.TemporaryDirectory() as d:
        config=Path(d)/'Caddyfile';config.write_text(source)
        with (Path(d)/'log').open('w+') as log:
            proc=subprocess.Popen([binary,'run','--config',str(config),'--adapter','caddyfile'],env=env,stdout=log,stderr=log)
            try:
                def request(path,secret=None):
                    req=urllib.request.Request(f'http://127.0.0.1:{proxy_port}'+path,headers={'X-Telegram-Bot-Api-Secret-Token':secret} if secret else {})
                    try:
                        with urllib.request.urlopen(req,timeout=2) as r:return r.status,r.read().decode()
                    except urllib.error.HTTPError as e:return e.code,e.read().decode()
                for attempt in range(50):
                    try:
                        if request('/')[0]==200:break
                    except urllib.error.URLError:time.sleep(.1)
                else:raise RuntimeError('Local test proxy did not start')
                good=env['TELEGRAM_WEBHOOK_SECRET'];path='/integrations/telegram/webhook?botId='
                assert request(path+'123')[0]==403
                assert request(path+'123','wrong')[0]==403
                assert request(path+'999',good)[0]==403
                assert request(path+'123',good)[0]==200
                assert request(path+'999&botId=123',good)[0]==403
                assert request(path+'123&botId=999',good)[0]==403
                for alias in ['Telegram','TELEGRAM','telegram_','%54elegram']:
                    assert request('/integrations/'+alias+'/webhook?botId=123')[0] in (403,404),alias
                assert request('/integrations/whatsapp/webhook')[0]==200
                assert request('/integrations/instagram-facebook/callback')[0]==200
                assert request('/chatbotx/private/file?X-Amz-Signature=test')[1]=='/chatbotx/private/file?X-Amz-Signature=test'
                assert request('/ws/parties/workspaces/123')[1]=='/parties/workspaces/123'
                print('PASS: real local Caddy routing — missing/wrong secret, bot mismatch, duplicate botId, channel aliases, storage signature path and realtime prefix.')
            finally:
                proc.terminate();proc.wait(timeout=5)
finally:stub.shutdown();stub.server_close()
