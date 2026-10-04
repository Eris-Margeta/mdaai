import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

const routes = ['/', '/repository-structure/', '/how-files-work-together/', '/task-lifecycle/', '/mdaai-1/', '/mdaai-2/', '/templates/'];
const widths = [320, 360, 375, 390, 414, 768, 1024, 1440];
async function settle(browser: any) {
  await browser.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
}
async function eventually(browser: any, fn: string) {
  for (let i = 0; i < 40; i++) {
    if (await browser.evaluate(fn)) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  expect(await browser.evaluate(fn)).toBe(true);
}
async function geometry(browser: any) {
  return browser.evaluate(() => {
    const main = document.querySelector('#main') as HTMLElement;
    const header = document.querySelector('.header') as HTMLElement;
    const bar = document.querySelector('.section-bar') as HTMLElement;
    const rect = (e: HTMLElement) => { const r = e.getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,client:e.clientWidth,scroll:e.scrollWidth}; };
    const doc = document.documentElement;
    return {viewport: innerWidth, document: {client:doc.clientWidth,scroll:doc.scrollWidth}, main:rect(main), header:rect(header), subnav:bar ? rect(bar) : null, mainOverflow:getComputedStyle(main).overflowY, mainHeight:main.clientHeight, mainScrollHeight:main.scrollHeight, bodyY:scrollY};
  });
}
function fits(g: any) {
  expect(g.document.scroll).toBeLessThanOrEqual(g.document.client + 1);
  for (const key of ['main', 'header', 'subnav']) {
    expect(g[key]).not.toBeNull();
    expect(g[key].left).toBeGreaterThanOrEqual(-1);
    expect(g[key].right).toBeLessThanOrEqual(g.viewport + 1);
    expect(g[key].scroll).toBeLessThanOrEqual(g[key].client + 1);
  }
  expect(['auto', 'scroll']).toContain(g.mainOverflow);
  expect(g.main.top).toBeGreaterThanOrEqual(Math.max(g.header.bottom,g.subnav.bottom)-1);
}

for (const route of routes) for (const width of widths) for (const theme of ['light','dark']) {
  test(`shell ${route} ${width}px ${theme}`, {tags:['matrix']}, async ({app,browser}) => {
    await browser.setViewport({width,height:844});
    await browser.addInitScript(`localStorage.setItem('onion-theme', '${theme}')`);
    await app.open(route);
    await settle(browser);
    expect(await browser.evaluate(() => document.documentElement.dataset.theme)).toBe(theme);
    fits(await geometry(browser));
    if (route==='/' && (width===320 || width===1440)) await app.screenshot(`hero-${width}-${theme}`);
    const bars = await geometry(browser);
    await browser.evaluate(() => { const m=document.querySelector('#main') as HTMLElement; m.scrollTop=m.scrollHeight; });
    await settle(browser);
    const after = await geometry(browser);
    expect(after.bodyY).toBe(0);
    expect(after.header.top).toBe(bars.header.top);
    expect(after.subnav.top).toBe(bars.subnav.top);
    expect(after.main.top).toBe(bars.main.top);
    expect(await browser.evaluate(() => { const m=document.querySelector('#main') as HTMLElement; const f=m.querySelector('footer'); return !!f && f.getBoundingClientRect().bottom <= m.getBoundingClientRect().bottom+1; })).toBe(true);
    const menuVisible = await browser.evaluate(() => { const e=document.querySelector('.menu') as HTMLElement; return e.getBoundingClientRect().width>0; });
    if (menuVisible) {
      await browser.locator('.menu').tap();
      expect(await browser.evaluate(() => document.querySelector('.menu')?.getAttribute('aria-expanded'))).toBe('true');
      fits(await geometry(browser));
      await browser.keyboard.press('Escape');
      expect(await browser.evaluate(() => document.querySelector('.menu')?.getAttribute('aria-expanded'))).toBe('false');
    }
    if (route==='/' && (width===320 || width===1440)) await app.screenshot(`shell-${width}-${theme}`);
  });
}

for (const route of routes) for (const width of [375,1440]) {
  test(`jump spy history keyboard ${route} ${width}`, {tags:['navigation']}, async ({app,browser}) => {
    await browser.setViewport({width,height:844});
    await app.open(route);
    const ids = await browser.evaluate(() => Array.from(document.querySelectorAll('#main section[id]')).map(e=>e.id));
    expect(ids.length).toBeGreaterThan(1);
    for (const i of [0, Math.floor(ids.length/2), ids.length-1]) {
      const id=ids[i];
      await browser.locator('#section-jump').selectOption({value:id});
      await eventually(browser, `() => location.hash === ${JSON.stringify('#'+id)} && document.querySelector('#section-jump').value === ${JSON.stringify(id)}`);
      expect(await browser.evaluate(() => scrollY)).toBe(0);
      expect(await browser.evaluate((id:string) => { const m=document.querySelector('#main')!; const s=document.getElementById(id)!; const mr=m.getBoundingClientRect(),sr=s.getBoundingClientRect(); return sr.bottom>mr.top && sr.top<mr.bottom; },id)).toBe(true);
    }
    await browser.back();
    await eventually(browser, `() => location.hash === ${JSON.stringify('#'+ids[Math.floor(ids.length/2)])}`);
    await browser.forward();
    await eventually(browser, `() => location.hash === ${JSON.stringify('#'+ids[ids.length-1])}`);
    await app.open(route+'#'+ids[Math.floor(ids.length/2)]);
    await eventually(browser, `() => document.querySelector('#section-jump').value === ${JSON.stringify(ids[Math.floor(ids.length/2)])}`);
    for (const position of ['top','middle','bottom']) {
      await browser.evaluate((p:string) => {const m=document.querySelector('#main') as HTMLElement; m.scrollTop=p==='top'?0:p==='middle'?(m.scrollHeight-m.clientHeight)/2:m.scrollHeight;},position);
      await eventually(browser, `() => { const m=document.querySelector('#main'); const ss=[...m.querySelectorAll('section[id]')]; const top=m.getBoundingClientRect().top; let expected=ss[0].id; for (const s of ss) if(s.getBoundingClientRect().top<=top+100) expected=s.id; if(m.scrollTop+m.clientHeight>=m.scrollHeight-2) expected=ss.at(-1).id; return document.querySelector('#section-jump').value===expected; }`);
    }
    await browser.evaluate(() => {const m=document.querySelector('#main') as HTMLElement;m.scrollTop=0;m.focus();});
    await browser.keyboard.press('PageDown');
    await eventually(browser,'() => document.querySelector("#main").scrollTop > 0 && scrollY === 0');
    await app.screenshot('keyboard-scrolled');
  });
}

for (const width of [320,375,768,1440]) test(`search theme focus ${width}`, {tags:['interaction']}, async ({app,browser}) => {
  await browser.setViewport({width,height:844});
  await app.open('/');
  const initial=await browser.evaluate(()=>document.documentElement.dataset.theme);
  await browser.locator('.theme').tap();
  expect(await browser.evaluate(()=>document.documentElement.dataset.theme)).not.toBe(initial);
  await browser.reload();
  expect(await browser.evaluate(()=>document.documentElement.dataset.theme)).not.toBe(initial);
  await browser.locator('.search-open').tap();
  expect(await browser.evaluate(()=>document.activeElement?.id)).toBe('search-input');
  await browser.locator('#search-input').fill('TASKS');
  await eventually(browser,'() => document.querySelectorAll("#search-results a").length > 0');
  await browser.keyboard.press('ArrowDown');
  expect(await browser.evaluate(()=>document.activeElement?.classList.contains('search-result'))).toBe(true);
  await app.screenshot(`search-${width}`);
  await browser.keyboard.press('Escape');
  expect(await browser.evaluate(()=>(document.querySelector('#search-dialog') as HTMLDialogElement).open)).toBe(false);
  expect(await browser.evaluate(()=>document.activeElement?.classList.contains('search-open'))).toBe(true);
  await browser.keyboard.press('Control+k');
  expect(await browser.evaluate(()=>(document.querySelector('#search-dialog') as HTMLDialogElement).open)).toBe(true);
  await browser.locator('#search-input').fill('TASKS');
  await eventually(browser,'() => document.querySelectorAll("#search-results a").length > 0');
  const destination = await browser.evaluate(() => (document.querySelector('#search-results a') as HTMLAnchorElement).href);
  await browser.keyboard.press('Enter');
  await browser.waitForURL(destination);
  await expect(browser.locator('#main')).toBeVisible();
  expect(await browser.evaluate(() => !!location.hash && !(document.querySelector('#search-dialog') as HTMLDialogElement).open)).toBe(true);
});
