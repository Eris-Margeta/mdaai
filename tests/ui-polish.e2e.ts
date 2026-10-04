import { test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { chromium } from 'playwright';

// Pinned TesterArmy browser API, no agents/models or clipboard permissions.
const routes = ['/', '/repository-structure/', '/how-files-work-together/', '/task-lifecycle/', '/mdaai-1/', '/mdaai-2/', '/templates/'];
const themes = ['light', 'dark'];
async function settle(browser:any) {
  await browser.evaluate(async () => {
    await document.fonts.ready;
    if (document.readyState !== 'complete') await new Promise<void>(resolve => window.addEventListener('load', () => resolve(), {once:true}));
    await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
  });
}
async function until(browser:any, predicate:string) {
  for (let i=0;i<50;i++) {
    if (await browser.evaluate(predicate)) return;
    await new Promise(resolve => setTimeout(resolve,40));
  }
  expect(await browser.evaluate(predicate)).toBe(true);
}
async function open(app:any,browser:any,route:string,width:number,theme:string) {
  await browser.setViewport({width,height:844});
  await browser.addInitScript(`localStorage.setItem('onion-theme', ${JSON.stringify(theme)})`);
  await app.open(route);
  await settle(browser);
}

for (const route of routes) for (const width of [320,375,1440]) for (const theme of themes) {
  test(`UI polish ${route} ${width}px ${theme}`, {tags:['ui-polish']}, async ({app,browser}) => {
    await open(app,browser,route,width,theme);
    const state = await browser.evaluate(() => {
      const gh=document.querySelector('.github-repo') as HTMLAnchorElement;
      const gr=gh.getBoundingClientRect(),gs=getComputedStyle(gh);
      const main=document.querySelector('#main') as HTMLElement;
      // Select semantic titles, not h2 textContent (which now includes controls).
      const headings=Array.from(main.querySelectorAll('h2,h3')).filter(h =>
        h.querySelector('.heading-anchor') || h.id || h.parentElement?.matches('section[id]'));
      return {
        theme:document.documentElement.dataset.theme,
        gh:{text:gh.textContent?.trim(),svg:!!gh.querySelector('svg'),height:gr.height,width:gr.width,visible:gs.display!=='none' && gs.visibility!=='hidden',href:gh.href},
        isolation:getComputedStyle(document.querySelector('.docs-layout')!).isolation,
        overflow:document.documentElement.scrollWidth>innerWidth+1,
        headings:headings.map(h => {
          const a=h.querySelector('a.heading-anchor') as HTMLAnchorElement;
          const b=h.querySelector('button.heading-copy') as HTMLButtonElement;
          const s=h.querySelector('.heading-copy-status') as HTMLElement;
          const title=Array.from(h.children).find(e => e.tagName==='SPAN' && !e.classList.contains('heading-copy-status'));
          const id=a?.getAttribute('href')?.split('#').pop();
          return {title:title?.textContent?.trim(),anchor:a?.textContent?.trim(),href:a?.getAttribute('href'),target:!!id && !!document.getElementById(decodeURIComponent(id)),siblings:!!a && !!b && a.parentElement===h && b.parentElement===h && !a.contains(b),label:b?.getAttribute('aria-label'),type:b?.type,status:!!s,live:s?.getAttribute('aria-live'),empty:s?.textContent?.trim()==='',hidden:!!s && (s.hidden || getComputedStyle(s).display==='none' || getComputedStyle(s).visibility==='hidden' || (s.getBoundingClientRect().width<=1 && s.getBoundingClientRect().height<=1)),buttons:h.querySelectorAll('.heading-copy').length};
        }),
        arrows:Array.from(main.querySelectorAll('.direction-icon')).map(e => ({span:e.tagName==='SPAN',text:e.textContent?.trim(),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height})),
        bareFlow:Array.from(main.querySelectorAll('.flow-row')).some(e => Array.from(e.childNodes).some(n => n.nodeType===Node.TEXT_NODE && /[→↓]/.test(n.textContent||''))),
        flow:Array.from(main.querySelectorAll('.flow-row .direction-icon')).map(e => { const m=new DOMMatrix(getComputedStyle(e).transform); return {a:m.a,b:m.b}; })
      };
    });
    expect(state.theme).toBe(theme);
    expect(state.gh.text).toBe('GH'); expect(state.gh.svg).toBe(true); expect(state.gh.visible).toBe(true);
    expect(state.gh.href).toBe('https://github.com/Eris-Margeta/mdaai');
    expect(state.gh.height).toBeGreaterThanOrEqual(44); expect(state.gh.width).toBeLessThanOrEqual(100);
    expect(state.isolation).toBe('isolate'); expect(state.overflow).toBe(false);
    expect(state.headings.length).toBeGreaterThan(0);
    for (const h of state.headings) {
      expect(!!h.title).toBe(true); expect(h.anchor).toBe('#'); expect(h.href?.startsWith('#')).toBe(true);
      expect(h.target).toBe(true); expect(h.siblings).toBe(true); expect(h.buttons).toBe(1);
      expect(h.label).toBe(`Copy link to ${h.title}`); expect(h.type).toBe('button');
      expect(h.status).toBe(true); expect(h.live).toBe('polite'); expect(h.empty).toBe(true); expect(h.hidden).toBe(true);
    }
    expect(state.bareFlow).toBe(false);
    for (const arrow of state.arrows) { expect(arrow.span).toBe(true); expect(!!arrow.text).toBe(true); expect(arrow.width).toBeGreaterThan(0); expect(arrow.height).toBeGreaterThan(0); }
    if (route==='/how-files-work-together/') {
      expect(state.flow.length).toBeGreaterThan(0);
      for (const m of state.flow) { expect(Math.abs(m.a-(width===1440?1:0))).toBeLessThanOrEqual(.01); expect(Math.abs(m.b-(width===1440?0:1))).toBeLessThanOrEqual(.01); }
    }
  });
}

for (const route of routes) for (const reject of [false,true]) {
  test(`heading copy ${reject?'rejection':'success'} ${route}`, {tags:['ui-polish','clipboard']}, async ({app,browser}) => {
    await open(app,browser,route+'?ui-polish=1',375,'light');
    const expected=await browser.evaluate((fail:boolean) => {
      const h=document.querySelector('#main .heading-copy')!.parentElement!;
      const a=h.querySelector('.heading-anchor') as HTMLAnchorElement;
      const canonical=new URL((document.querySelector('link[rel="canonical"]') as HTMLLinkElement).href);
      canonical.search=''; canonical.hash=a.getAttribute('href')!;
      (window as any).__polishCopies=[];
      Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async (text:string) => { (window as any).__polishCopies.push(text); if(fail) throw new Error('deterministic clipboard rejection'); }}});
      // Force legacy fallback to fail too; never report success after rejection.
      Object.defineProperty(document,'execCommand',{configurable:true,value:() => false});
      history.replaceState(null,'',location.pathname+location.search+'#ui-polish-unrelated');
      return canonical.href;
    },reject);
    await browser.locator('#main .heading-copy').first().focus();
    const before=await browser.evaluate(() => ({href:location.href,y:(document.querySelector('#main') as HTMLElement).scrollTop}));
    await browser.keyboard.press('Enter');
    await until(browser,'() => !!document.querySelector("#main .heading-copy-status").textContent.trim()');
    const after=await browser.evaluate(() => {
      const s=document.querySelector('#main .heading-copy-status') as HTMLElement;
      return {copies:(window as any).__polishCopies,text:s.textContent||'',hidden:s.hidden,href:location.href,y:(document.querySelector('#main') as HTMLElement).scrollTop,live:s.getAttribute('aria-live')};
    });
    expect(after.copies).toEqual([expected]); expect(after.href).toBe(before.href); expect(after.y).toBe(before.y);
    expect(after.live).toBe('polite'); expect(after.hidden).toBe(false);
    if(reject) { expect(/unavailable|failed|could not|couldn't|unable/i.test(after.text)).toBe(true); expect(after.text).toContain(expected); expect(/manual|select|copy this|copy the|copy link/i.test(after.text)).toBe(true); expect(/copied/i.test(after.text)).toBe(false); }
    else expect(/copied/i.test(after.text)).toBe(true);
  });
}

for (const route of routes) for (const width of [320,375]) for (const theme of themes) {
  test(`drawer bounds dismissal ${route} ${width}px ${theme}`, {tags:['ui-polish','drawer']}, async ({app,browser}) => {
    await open(app,browser,route,width,theme);
    await browser.evaluate(() => { const m=document.querySelector('#main') as HTMLElement; m.scrollTop=Math.min(240,m.scrollHeight-m.clientHeight); });
    await settle(browser);
    const y=await browser.evaluate(() => (document.querySelector('#main') as HTMLElement).scrollTop);
    for (const dismissal of ['Escape','backdrop','resize']) {
      await browser.locator('.menu').tap();
      await until(browser,'() => document.querySelector(".menu").getAttribute("aria-expanded") === "true"');
      const bounds=await browser.evaluate(() => {
        const r=(s:string)=>{const e=document.querySelector(s)!;const b=e.getBoundingClientRect();return {top:b.top,bottom:b.bottom,left:b.left,right:b.right,width:b.width,height:b.height};};
        const b=document.querySelector('.nav-backdrop') as HTMLElement;
        return {layout:r('.docs-layout'),bar:r('.section-bar'),nav:r('#docs-nav'),backdrop:r('.nav-backdrop'),inert:(document.querySelector('#main') as HTMLElement).inert,hit:document.elementFromPoint(innerWidth-2,(b.getBoundingClientRect().top+b.getBoundingClientRect().bottom)/2)?.classList.contains('nav-backdrop')};
      });
      expect(bounds.inert).toBe(true); expect(bounds.hit).toBe(true);
      expect(bounds.nav.top).toBeGreaterThanOrEqual(bounds.bar.bottom-1);
      for (const b of [bounds.nav,bounds.backdrop]) {
        expect(b.width).toBeGreaterThan(0); expect(b.height).toBeGreaterThan(0);
        expect(b.top).toBeGreaterThanOrEqual(bounds.layout.top-1); expect(b.bottom).toBeLessThanOrEqual(bounds.layout.bottom+1);
        expect(b.left).toBeGreaterThanOrEqual(bounds.layout.left-1); expect(b.right).toBeLessThanOrEqual(bounds.layout.right+1);
      }
      if(dismissal==='Escape') await browser.keyboard.press('Escape');
      if(dismissal==='backdrop') await browser.locator('.nav-backdrop').tap({position:{x:bounds.backdrop.width-2,y:bounds.backdrop.height/2}});
      if(dismissal==='resize') await browser.setViewport({width:1440,height:844});
      await until(browser,'() => document.querySelector(".menu").getAttribute("aria-expanded") === "false" && !document.querySelector("#main").inert && !document.body.classList.contains("nav-open")');
      if(dismissal!=='resize') expect(await browser.evaluate(() => document.activeElement?.classList.contains('menu'))).toBe(true);
      expect(await browser.evaluate(() => (document.querySelector('#main') as HTMLElement).scrollTop)).toBe(y);
      expect(await browser.evaluate(() => scrollY)).toBe(0);
      if(dismissal==='resize') { await browser.setViewport({width,height:844}); await settle(browser); expect(await browser.evaluate(() => document.querySelector('.menu')?.getAttribute('aria-expanded'))).toBe('false'); }
    }
  });
}


for (const touch of [false,true]) test(`heading discoverability ${touch?'touch':'hover and keyboard'}`, {tags:['ui-polish']}, async()=>{
  const browser=await chromium.launch();
  const context=await browser.newContext({viewport:{width:touch?320:1440,height:844},hasTouch:touch,isMobile:touch});
  const page=await context.newPage();
  try {
    await page.goto((process.env.E2E_BASE_URL||'http://127.0.0.1:8765')+'/how-files-work-together/');
    await page.evaluate(()=>document.fonts.ready);
    const h=page.locator('.anchorable-heading').first();
    const copy=h.locator('.heading-copy'); const anchor=h.locator('.heading-anchor');
    if(!touch) {
      await page.mouse.move(0,0);
      expect(await copy.evaluate(e=>getComputedStyle(e).opacity)).toBe('0');
      await h.locator('.heading-title').hover();
      expect(await copy.evaluate(e=>getComputedStyle(e).opacity)).toBe('1');
      await page.mouse.move(0,0); await anchor.focus();
      expect(await copy.evaluate(e=>getComputedStyle(e).opacity)).toBe('1');
      await page.keyboard.press('Tab');
      expect(await copy.evaluate(e=>document.activeElement===e)).toBe(true);
      expect(await copy.evaluate(e=>getComputedStyle(e).outlineStyle)).not.toBe('none');
    }else{
      expect(await copy.evaluate(e=>getComputedStyle(e).opacity)).toBe('1');
      expect((await copy.boundingBox())!.width).toBeGreaterThanOrEqual(44);
      expect((await copy.boundingBox())!.height).toBeGreaterThanOrEqual(44);
      await page.locator('.menu').tap();
      expect(await page.locator('.nav-backdrop').evaluate(e=>getComputedStyle(e).backgroundColor)).toBe('rgba(0, 0, 0, 0.58)');
      expect(await page.locator('.section-bar').evaluate(e=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.left+5,r.top+5));})).toBe(true);
      await page.keyboard.press('Escape');
    }
  }finally {await context.close();await browser.close();}
});

test('heading clipboard timeout and retry preserve scrolled pane', {tags:['ui-polish','clipboard']}, async({app,browser})=>{
  await open(app,browser,'/how-files-work-together/?transient=1',375,'dark');
  await browser.locator('.heading-copy').last().focus();
  const before=await browser.evaluate(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:()=>new Promise(()=>{})}});return {y:document.querySelector('#main').scrollTop,href:location.href};});
  await browser.keyboard.press('Enter');
  await until(browser,'()=>!!document.querySelector(".heading-copy-status:not([hidden])")');
  const failure=await browser.evaluate(()=>{const n=document.querySelector('.heading-copy-status:not([hidden])');return {text:n.textContent,disabled:n.parentElement.querySelector('button').disabled,y:document.querySelector('#main').scrollTop,href:location.href};});
  expect(failure.text).toContain('Copy unavailable');expect(failure.disabled).toBe(false);expect(failure.y).toBe(before.y);expect(failure.href).toBe(before.href);
  await browser.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{}}}));
  await browser.keyboard.press('Enter');
  await until(browser,'()=>document.querySelector(".heading-copy-status:not([hidden])").textContent === "Copied link."');
  expect(await browser.evaluate(()=>document.querySelector('#main').scrollTop)).toBe(before.y);
});
