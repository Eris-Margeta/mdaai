import { test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { chromium } from 'playwright';

test('served origin: real worker scope, cached reading, offline fallback and recovery',async()=>{
  const base=process.env.E2E_BASE_URL || 'http://127.0.0.1:8765';
  const browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:375,height:844}});
  const page=await context.newPage();
  try{
    await page.goto(base+'/');
    await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
    await page.reload();
    await page.goto(base+'/repository-structure/');
    await page.waitForFunction(async()=>{const c=(await caches.keys()).find(x=>x.startsWith('mdaai-public-'));return !!c && !!(await(await caches.open(c)).match('/repository-structure/')) && !!(await(await caches.open(c)).match('/assets/publication.css'));});
    const scope=await page.evaluate(async()=>({scope:(await navigator.serviceWorker.getRegistration())?.scope,script:navigator.serviceWorker.controller?.scriptURL}));
    expect(scope.scope).toBe(base+'/');expect(scope.script).toBe(base+'/service-worker.js');
    const response=await context.request.get(base+'/service-worker.js');
    expect(response.status()).toBe(200);expect(response.headers()['content-type']).toContain('javascript');expect(response.headers()['cache-control']).toContain('no-cache');expect(response.headers()['x-content-type-options']).toBe('nosniff');
    await context.setOffline(true);
    await page.reload();
    expect(await page.title()).toBe('Repository structure | MDAAI');
    expect(await page.evaluate(()=>getComputedStyle(document.querySelector('#main')!).overflowY)).toBe('auto');
    expect(await page.evaluate(()=>scrollY)).toBe(0);
    await page.goto(base+'/never-saved-public-page/');
    expect(await page.locator('h1').textContent()).toBe('MDAAI is offline');
    await context.setOffline(false);
    await page.goto(base+'/');
    expect(await page.locator('h1').textContent()).toBe('MDAAI');
  }finally{await context.close();await browser.close();}
});
