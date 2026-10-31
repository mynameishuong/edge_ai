"""Optional Chrome DevTools smoke test against the running local review server."""
from __future__ import annotations
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request
import websocket

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8765'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'


def get_json(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


class CDP:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, timeout=10, suppress_origin=True)
        self.seq = 0
        self.errors = []

    def call(self, method, params=None):
        self.seq += 1
        self.ws.send(json.dumps({'id': self.seq, 'method': method, 'params': params or {}}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get('method') == 'Runtime.exceptionThrown':
                self.errors.append(message['params'])
            if message.get('id') == self.seq:
                if 'error' in message:
                    raise RuntimeError(message['error'])
                return message.get('result', {})

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', {'expression':expression, 'returnByValue':True, 'awaitPromise':True})
        if 'exceptionDetails' in result:
            raise RuntimeError(result['exceptionDetails'])
        return result.get('result', {}).get('value')

    def screenshot(self, name):
        layout = self.call('Page.getLayoutMetrics')['cssContentSize']
        result = self.call('Page.captureScreenshot', {'format':'png', 'captureBeyondViewport':True,
                           'clip':{'x':0,'y':0,'width':layout['width'],'height':layout['height'],'scale':1}})
        (ROOT/'docs'/name).write_bytes(base64.b64decode(result['data']))

    def viewport(self, width, height):
        self.call('Emulation.setDeviceMetricsOverride', {'width':width,'height':height,'deviceScaleFactor':1,'mobile':False})


def main():
    profile = tempfile.mkdtemp(prefix='ai-vids-chrome-')
    proc = subprocess.Popen([CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
                             '--no-default-browser-check', '--remote-debugging-port=0',
                             '--user-data-dir='+profile, 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        portfile = Path(profile)/'DevToolsActivePort'
        deadline=time.monotonic()+20
        while not portfile.exists():
            if proc.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError('Chrome did not start')
            time.sleep(.1)
        port=portfile.read_text().splitlines()[0]
        targets=get_json(f'http://127.0.0.1:{port}/json/list')
        target=next(x for x in targets if x['type']=='page')
        cdp=CDP(target['webSocketDebuggerUrl'])
        cdp.call('Runtime.enable');cdp.call('Page.enable');cdp.viewport(1440,1000)
        cdp.call('Page.navigate', {'url':URL})
        deadline=time.monotonic()+15
        while not cdp.evaluate("document.readyState==='complete' && !!document.querySelector('.architecture') && document.querySelector('.architecture').naturalWidth>0"):
            if time.monotonic()>deadline: raise RuntimeError('UI did not load')
            time.sleep(.1)
        assert cdp.evaluate('document.title') == 'AI-VIDS · Local Review'
        cdp.screenshot('local-review.png')
        cdp.evaluate("document.querySelector('[data-tab=demo]').click();document.querySelector('#play').click()")
        observed=set(); saved_demo=False;deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            state=get_json(URL+'/api/state')
            observed.update(x['reason'] for x in state['events'])
            last=state['events'][-1] if state['events'] else {}
            if not saved_demo and 9000<=last.get('t_ms',-1)<13000:
                cdp.screenshot('local-demo.png');saved_demo=True
            if not state['running'] and state['events']:break
            time.sleep(.5)
        assert not state['running'], 'Replay exceeded timeout'
        assert not state['error'], state['error']
        assert len(state['events'])==460
        assert {'possible_flooding','unknown_id','ml_anomaly','no_frames'}<=observed, observed
        assert cdp.evaluate("document.querySelector('#p95').textContent!=='—'")
        cdp.evaluate("document.querySelector('[data-tab=validation]').click()")
        assert cdp.evaluate("document.querySelector('#report').textContent.includes('max_score_parity_error')")
        cdp.viewport(390,844)
        for tab in ['arch','demo','validation']:
            cdp.evaluate(f"document.querySelector('[data-tab={tab}]').click()")
            assert cdp.evaluate('document.documentElement.scrollWidth<=window.innerWidth'), f'Mobile overflow in {tab}'
        assert not cdp.errors, cdp.errors
        result={'browser':'Chrome headless / CDP','desktop':'1440x1000','mobile':'390x844',
                'replay_windows':len(state['events']),'observed_reasons':sorted(observed),
                'javascript_errors':cdp.errors,'status':'PASS'}
        (ROOT/'runtime'/'browser-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
        cdp.ws.close()
    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill()
        # Temporary browser profile remains in the system temp directory for review.


if __name__=='__main__':
    main()
