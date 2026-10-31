"""Check task-to-architecture navigation and filtering; does not replay or deploy."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
from browser_smoke import CDP, CHROME, ROOT, URL, get_json


def wait_ready(cdp, expression, timeout=10):
    deadline=time.monotonic()+timeout
    while not cdp.evaluate(expression):
        if time.monotonic()>deadline:
            raise RuntimeError('Page readiness timeout')
        time.sleep(.1)


def main():
    profile=tempfile.mkdtemp(prefix='ai-vids-review-test-')
    proc=subprocess.Popen([CHROME,'--headless=new','--disable-gpu','--no-first-run',
                           '--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                          creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        portfile=Path(profile)/'DevToolsActivePort';deadline=time.monotonic()+20
        while not portfile.exists():
            if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Chrome failed to start')
            time.sleep(.1)
        port=portfile.read_text().splitlines()[0]
        target=next(t for t in get_json(f'http://127.0.0.1:{port}/json/list') if t['type']=='page')
        cdp=CDP(target['webSocketDebuggerUrl'])
        cdp.call('Runtime.enable');cdp.call('Page.enable');cdp.viewport(1440,1000)
        cdp.call('Page.navigate',{'url':URL+'/review'})
        wait_ready(cdp,"document.querySelectorAll('.task').length===38")
        assert cdp.evaluate("document.querySelectorAll('g[data-arch-ref]').length")==19
        assert cdp.evaluate('PLAN.tasks.reduce((sum,t)=>sum+t.weight,0)')==100
        cdp.evaluate("document.querySelector('[data-arch-ref=B3]').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
        assert cdp.evaluate("Array.from(document.querySelectorAll('.task')).map(t=>t.id)")==['T12','T13']
        assert '7%' in cdp.evaluate("document.querySelector('#count').textContent")
        cdp.evaluate("document.querySelectorAll('.task details').forEach(d=>d.open=true);document.querySelector('details.arch').open=false")
        cdp.screenshot('review-tasks.png')
        cdp.evaluate("focusTask('T13');document.querySelector('.task details').open=true;document.querySelector('.deps button').click()")
        assert cdp.evaluate("document.querySelector('.task').id")=='T28'
        cdp.evaluate("document.querySelector('#reset').click();document.querySelector('#status-filter').value='gap';render()")
        assert cdp.evaluate("Array.from(document.querySelectorAll('.task')).map(t=>t.id)")==['T34']
        cdp.evaluate("document.querySelector('#reset').click();choose('A')")
        assert cdp.evaluate("document.querySelectorAll('.task').length")==7
        assert '18%' in cdp.evaluate("document.querySelector('#count').textContent")
        cdp.viewport(390,844)
        for ref in ['A','B','C','D']:
            cdp.evaluate(f"choose('{ref}')")
            assert cdp.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),ref
        cdp.call('Page.navigate',{'url':(ROOT/'docs'/'TASK_REVIEW.html').as_uri()})
        wait_ready(cdp,"document.querySelectorAll('.task').length===38")
        assert cdp.evaluate("document.querySelectorAll('g[data-arch-ref]').length")==19
        cdp.call('Page.navigate',{'url':URL})
        wait_ready(cdp,"!!document.querySelector('[href=\"/review\"]')")
        assert cdp.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        cdp.viewport(1680,1500)
        cdp.call('Page.navigate',{'url':URL+'/architecture.svg'})
        wait_ready(cdp,"document.querySelectorAll('g[data-arch-ref]').length===19")
        cdp.screenshot('architecture.png')
        assert not cdp.errors,cdp.errors
        result={'status':'PASS','tasks':38,'architecture_nodes':19,'effort_total':100,
                'checks':['node filtering','task dependencies','gap filter','group weights',
                          'mobile 390px','offline HTML','local server route','main UI link'],
                'javascript_errors':cdp.errors}
        (ROOT/'runtime'/'review-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
        cdp.ws.close()
    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill()


if __name__=='__main__':main()
