"""Terminal-only Chrome/CDP driver for local acceptance checks."""
import json,os,subprocess,time
from websockets.sync.client import connect
from verify_m1_browser import free_port,wait_http

class Browser:
    def __init__(self,artifacts):
        self.artifacts=artifacts;artifacts.mkdir(parents=True,exist_ok=True)
        self.port=free_port();self.sequence=0;self.answers=[];self.errors=[];self.checks=[]
    def __enter__(self):
        self.process=subprocess.Popen(['C:/Program Files/Google/Chrome/Application/chrome.exe','--headless=new','--disable-extensions',
            '--no-first-run','--disable-background-networking',f'--remote-debugging-port={self.port}',f'--user-data-dir={self.artifacts/"profile"}','about:blank'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        pages=json.loads(wait_http(f'http://127.0.0.1:{self.port}/json/list'))
        self.ws=connect(next(p for p in pages if p['type']=='page')['webSocketDebuggerUrl'])
        for method in ('Page.enable','Runtime.enable','Network.enable'):self.cdp(method)
        self.cdp('Network.setBlockedURLs',{'urls':['*fonts.googleapis.com*','*fonts.gstatic.com*']})
        self.cdp('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
        return self
    def cdp(self,method,params=None):
        self.sequence+=1;sequence=self.sequence
        self.ws.send(json.dumps({'id':sequence,'method':method,'params':params or {}}))
        while True:
            message=json.loads(self.ws.recv(timeout=40))
            if message.get('method')=='Page.javascriptDialogOpening':
                dialog=message['params'];value=self.answers.pop(0) if dialog['type']=='prompt' and self.answers else dialog.get('defaultPrompt','')
                self.ws.send(json.dumps({'id':100000+sequence,'method':'Page.handleJavaScriptDialog','params':{'accept':True,'promptText':value}}))
            if message.get('method')=='Runtime.exceptionThrown':self.errors.append(message['params']['exceptionDetails'].get('text','Runtime error'))
            if message.get('method')=='Runtime.consoleAPICalled' and message['params']['type']=='error':self.errors.append('Console error')
            if message.get('id')==sequence:
                if 'error' in message:raise RuntimeError(str(message['error']))
                return message.get('result',{})
    def js(self,expression):
        result=self.cdp('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True,'userGesture':True})
        if 'exceptionDetails' in result:raise RuntimeError('Browser expression failed: '+str(result['exceptionDetails'].get('text')))
        return result.get('result',{}).get('value')
    def expect(self,expression,label):
        for _ in range(250):
            if self.js(f'(()=>{{try{{return Boolean({expression})}}catch{{return false}}}})()'):
                self.checks.append(label);print('Passed:',label,flush=True);return
            time.sleep(.1)
        # Do not dump page contents: confirmation may contain a private code.
        print(json.dumps(self.js('({url:location.pathname,error:document.querySelector("#checkout-error-banner")?.textContent,disabled:document.querySelector("#btn-place-order")?.disabled,invalid:[...document.querySelectorAll("#checkout-form :invalid")].map(n=>n.id)})')),flush=True)
        raise RuntimeError('Acceptance failed: '+label)
    def goto(self,url):self.cdp('Page.navigate',{'url':url})
    def click(self,selector):self.js('document.querySelector('+json.dumps(selector)+').click()')
    def fill(self,selector,value,checked=False):self.js(f'''(()=>{{const n=document.querySelector({json.dumps(selector)});n.{'checked' if checked else 'value'}={json.dumps(value)};n.dispatchEvent(new Event('input',{{bubbles:true}}));n.dispatchEvent(new Event('change',{{bubbles:true}}));}})()''')
    def submit(self,selector):self.click(selector+' button[type="submit"]')
    def __exit__(self,*args):
        self.ws.close();self.process.terminate()
        try:self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
