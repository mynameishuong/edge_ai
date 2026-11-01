"""Check the offline model reader and compare its trace with the native scorer."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
from browser_smoke import CDP,CHROME,ROOT,get_json


def main():
    folder=ROOT/'docs'/'inspect'
    data=json.loads((folder/'binary-model-guide.json').read_text(encoding='utf-8'))
    assert len(data['records'])==7514
    assert data['meta']['nodes']==7448 and data['meta']['tree_count']==64
    cpp=subprocess.check_output([str(ROOT/'build'/'ai-vids.exe'),'score',str(ROOT/'models'/'demo.forest'),
                                 str(ROOT/'data'/'demo_features.csv')],text=True)
    assert abs(float(cpp.splitlines()[408])-data['trace']['score'])<1e-12
    profile=tempfile.mkdtemp(prefix='ai-vids-model-reader-')
    proc=subprocess.Popen([CHROME,'--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=0',
                           '--user-data-dir='+profile,'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                          creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        portfile=Path(profile)/'DevToolsActivePort';deadline=time.monotonic()+20
        while not portfile.exists():
            if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Chrome startup failed')
            time.sleep(.1)
        port=portfile.read_text().splitlines()[0]
        target=next(t for t in get_json(f'http://127.0.0.1:{port}/json/list') if t['type']=='page')
        cdp=CDP(target['webSocketDebuggerUrl']);cdp.call('Runtime.enable');cdp.call('Page.enable')
        cdp.viewport(1440,1000)
        cdp.call('Page.navigate',{'url':(folder/'AI_VIDS_BINARY_MODEL_LINE_BY_LINE.vi.html').as_uri()})
        deadline=time.monotonic()+15
        while not cdp.evaluate("document.querySelectorAll('#model-rows tr').length===98"):
            if cdp.errors:raise RuntimeError(cdp.errors)
            if time.monotonic()>deadline:raise RuntimeError('Model guide failed to load')
            time.sleep(.1)
        assert cdp.evaluate('D.meta.lines')==7514
        cdp.evaluate('sourceJump(280)')
        assert cdp.evaluate("document.querySelector('#source-280').classList.contains('focus')")
        cdp.evaluate('nodeJump(0,28)')
        assert cdp.evaluate("document.querySelector('#model-32 td.raw').textContent")==data['records'][31]['raw']
        cdp.evaluate("document.querySelector('#tree-filter').value='all';pg=37;renderModel()")
        assert cdp.evaluate("document.querySelectorAll('#model-rows tr').length")==114
        assert cdp.evaluate("!!document.querySelector('#model-7514')")
        cdp.evaluate("show('trace');document.querySelector('#trace-tree').value='0';renderTrace()")
        assert cdp.evaluate("document.querySelectorAll('#trace-rows tr').length")==7
        assert '12.955689' in cdp.evaluate("document.querySelector('#leaf').textContent")
        preview=folder/'preview';preview.mkdir(exist_ok=True)
        layout=cdp.call('Page.getLayoutMetrics')['cssContentSize']
        result=cdp.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True,
                        'clip':{'x':0,'y':0,'width':layout['width'],'height':layout['height'],'scale':1}})
        import base64
        (preview/'trace.png').write_bytes(base64.b64decode(result['data']))
        cdp.viewport(390,844)
        for tab in ['overview','source','model','trace']:
            cdp.evaluate(f"show('{tab}')")
            assert cdp.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),tab
        assert not cdp.errors,cdp.errors
        report={'status':'PASS','model_lines':7514,'nodes':7448,'trees':64,
                'source_explained_lines':len(data['source']),'native_score':data['trace']['score'],
                'checks':['offline HTML','source navigation','node child navigation','all-model pagination',
                          'tree trace','native C++ score parity','mobile layout'], 'javascript_errors':cdp.errors}
        (folder/'guide-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2));cdp.ws.close()
    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill()


if __name__=='__main__':main()
