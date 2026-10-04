import { test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { chromium } from 'playwright';
import { existsSync, mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';

// Real HTTP origin, real workers, browser network disconnection; no SW mocks.
test('PWA real offline recovery and two-version multi-tab update', {tags:['pwa']}, async () => {
  expect(existsSync(resolve('website/pwa.py'))).toBe(true);
  const root=mkdtempSync(join(tmpdir(),'mdaai-pwa-'));
  let disconnected=false;
  const publish=(version:string)=>{
    writeFileSync(join(root,'index.html'),`<!doctype html><title>${version}</title><main id="main"><h1>${version}</h1><input id="draft"><footer></footer></main><script defer src="/assets/pwa.js"></script>`);
    for(let i=0;i<45;i++) writeFileSync(join(root,`public-${i}.html`),`<!doctype html><title>Public ${i}</title><h1>${version}</h1>`);
    writeFileSync(join(root,'large.html'),'<!doctype html><title>Too large</title>'+ 'x'.repeat(600*1024));
    execFileSync('python3',['-B','-c','import sys;sys.path.insert(0,"website");from pwa import write_pwa;write_pwa(sys.argv[1])',root]);
    const first=readFileSync(join(root,'service-worker.js'),'utf8');
    execFileSync('python3',['-B','-c','import sys;sys.path.insert(0,"website");from pwa import write_pwa;write_pwa(sys.argv[1])',root]);
    expect(readFileSync(join(root,'service-worker.js'),'utf8')).toBe(first);
  };
  publish('A');
  const server=createServer((req,res)=>{
    if(disconnected){req.socket.destroy();return;}
    const path=new URL(req.url!,'http://localhost').pathname;
    if(path==='/api/private'){res.end('private');return;}
    const file=join(root,path==='/'?'index.html':path);
    if(!existsSync(file)){res.writeHead(404);res.end('not found');return;}
    res.setHeader('Cache-Control','no-cache');
    res.setHeader('Content-Type',path.endsWith('.js')?'text/javascript':'text/html');
    res.end(readFileSync(file));
  });
  await new Promise<void>(r=>server.listen(0,'127.0.0.1',r));
  const origin=`http://127.0.0.1:${(server.address() as any).port}`;
  const browser=await chromium.launch();
  const context=await browser.newContext();
  const one=await context.newPage();
  try {
    await one.goto(origin);
    await one.waitForFunction(()=>!!navigator.serviceWorker.controller);
    await one.reload();
    const two=await context.newPage();await two.goto(origin);
    await two.locator('#draft').fill('retain me');
    await two.evaluate(()=>caches.open('unrelated-app').then(c=>c.put('/unrelated',new Response('safe'))));
    await one.evaluate(()=>fetch('/api/private'));
    await context.setOffline(true);disconnected=true;
    await one.reload();expect(await one.title()).toBe('A');
    await one.goto(origin+'/never-loaded/');expect(await one.locator('h1').textContent()).toBe('MDAAI is offline');
    disconnected=false;await context.setOffline(false);await one.goto(origin);expect(await one.title()).toBe('A');
    publish('B');
    await one.evaluate(async()=>{const r=await navigator.serviceWorker.getRegistration();await r!.update();});
    await one.locator('#pwa-update').waitFor({state:'visible'});
    await two.locator('#pwa-update').waitFor({state:'visible'});
    await two.locator('#pwa-later').click();expect(await two.locator('#pwa-update').isVisible()).toBe(false);
    await context.setOffline(true);disconnected=true;
    await one.locator('#pwa-refresh').click();
    expect(await one.locator('#pwa-message').textContent()).toContain('Reconnect');
    expect(await one.title()).toBe('A');
    disconnected=false;await context.setOffline(false);
    await one.evaluate(()=>{const b=document.querySelector('#pwa-refresh') as HTMLButtonElement;b.click();b.click();});
    await one.waitForFunction(()=>document.title==='B');
    expect(await one.locator('#pwa-update').isVisible()).toBe(false);
    expect(await two.title()).toBe('A');expect(await two.locator('#draft').inputValue()).toBe('retain me');
    await two.locator('#pwa-update').waitFor({state:'visible'});
    expect(await two.evaluate(async()=>!!(await navigator.serviceWorker.getRegistration())!.waiting)).toBe(false);
    await two.locator('#pwa-refresh').click();await two.waitForFunction(()=>document.title==='B');
    const keys=await two.evaluate(()=>caches.keys());expect(keys.filter(k=>k.startsWith('mdaai-public-')).length).toBe(1);expect(keys).toContain('unrelated-app');
    const urls=await two.evaluate(async()=>{const k=(await caches.keys()).find(k=>k.startsWith('mdaai-public-'))!;return (await (await caches.open(k)).keys()).map(r=>new URL(r.url).pathname);});
    expect(urls).not.toContain('/api/private');
    expect(await two.evaluate(async()=> (await fetch('/missing-online/')).status)).toBe(404);
    await two.evaluate(async()=> {await fetch('/large.html');await fetch('/?personal=secret');await fetch('/public-0.html',{headers:{Authorization:'Bearer test-only'}});for(let i=0;i<45;i++) await fetch(`/public-${i}.html`);});
    await two.waitForFunction(async()=>{const k=(await caches.keys()).find(k=>k.startsWith('mdaai-public-'))!;const c=await caches.open(k);return !!(await c.match('/public-44.html'));});
    const bounded=await two.evaluate(async()=>{const k=(await caches.keys()).find(k=>k.startsWith('mdaai-public-'))!;return (await (await caches.open(k)).keys()).map(r=>new URL(r.url).pathname+new URL(r.url).search);});
    expect(bounded.length).toBeLessThanOrEqual(40);expect(bounded).toContain('/offline.html');expect(bounded).not.toContain('/large.html');expect(bounded).not.toContain('/?personal=secret');
    await two.setViewportSize({width:320,height:640});
    expect(await two.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    expect(await two.locator('#pwa-install-help').textContent()).toContain('browser');
    console.log('Verified: cached navigation, branded unknown-route fallback, recovery, real waiting B, Later, offline Refresh, duplicate click, retained second-tab draft, null-waiting Refresh, scoped cleanup. Native installed/device UI unavailable in headless Chromium.');
  } finally {await browser.close();await new Promise<void>(r=>server.close(()=>r()));rmSync(root,{recursive:true,force:true});}
});
