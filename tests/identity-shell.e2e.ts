import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

async function until(browser:any, fn:string) {
  for(let i=0;i<50;i++){if(await browser.evaluate(fn))return;await new Promise(r=>setTimeout(r,40));}
  const result=await browser.evaluate(fn);
  if(!result) console.log('Failed predicate',fn,await browser.evaluate(()=>{let m=document.querySelector('#main') as HTMLElement;return {y:m?.scrollTop,sh:m?.scrollHeight,ch:m?.clientHeight,active:document.activeElement?.id,ready:document.readyState,root:scrollY};}));
  expect(result).toBe(true);
}
for(const width of [320,375,768,1440]) test(`identity theme, keyboard and dynamic viewport ${width}`,async({app,browser})=>{
  await browser.setViewport({width,height:844});
  await app.open('/');
  await until(browser,'() => !!document.querySelector("#pwa-controls")');
  for(const theme of ['light','dark']) {
    await browser.evaluate((t:string)=>{localStorage.setItem('onion-theme',t);document.documentElement.dataset.theme=t;},theme);
    const pair=await browser.evaluate(()=>{const a=document.querySelector('.tejl-mark')!;return [...a.querySelectorAll('img')].map(i=>({alt:i.alt,display:getComputedStyle(i).display,src:i.getAttribute('src')}));});
    expect(pair.filter((i:any)=>i.display!=='none').length).toBe(1);
    expect(pair.find((i:any)=>i.display!=='none')!.src).toContain(theme==='light'?'off-black':'off-white');
    expect(pair.every((i:any)=>i.alt==='')).toBe(true);
    expect(await browser.evaluate(()=>document.querySelector('.tejl-mark')?.getAttribute('aria-label'))).toBe('TEJL — tejl.hr');
    await browser.evaluate(()=>{const m=document.querySelector('#main') as HTMLElement;m.scrollTop=m.scrollHeight;});
    await app.screenshot(`footer-${width}-${theme}`);
  }
  await browser.evaluate(()=>{const m=document.querySelector('#main') as HTMLElement;m.scrollTop=0;});
  await browser.locator('.skip').focus();
  await browser.keyboard.press('Enter');
  expect(await browser.evaluate(()=>document.activeElement?.id)).toBe('main');
  await browser.keyboard.press('End');
  await until(browser,'() => {let m=document.querySelector("#main");return m.scrollTop+m.clientHeight>=m.scrollHeight-2 && scrollY===0}');
  await browser.keyboard.press('Home');
  await until(browser,'() => document.querySelector("#main").scrollTop === 0 && scrollY===0');
  await browser.keyboard.press('Space');
  await until(browser,'() => document.querySelector("#main").scrollTop > 0 && scrollY===0');
  await browser.setViewport({width,height:620});
  const fits=await browser.evaluate(()=>{
    const m=document.querySelector('#main') as HTMLElement,b=document.querySelector('.section-bar') as HTMLElement;
    const option=document.createElement('option');option.textContent='A deliberately very long section label '.repeat(10);option.value='long';document.querySelector('#section-jump')!.append(option);
    const nav=document.querySelector('#docs-nav a')!;nav.textContent='A deliberately long navigation label '.repeat(10);
    return {root:document.documentElement.scrollWidth,viewport:innerWidth,main:m.clientHeight,bottom:m.getBoundingClientRect().bottom,top:m.getBoundingClientRect().top,bar:b.getBoundingClientRect().bottom,body:scrollY};
  });
  expect(fits.root).toBeLessThanOrEqual(fits.viewport+1);expect(fits.main).toBeGreaterThan(0);expect(fits.bottom).toBeLessThanOrEqual(621);expect(fits.top).toBeGreaterThanOrEqual(fits.bar-1);expect(fits.body).toBe(0);
  if(width<=768){
    await browser.locator('.menu').focus();await browser.keyboard.press('Enter');
    expect(await browser.evaluate(()=>document.querySelector('.menu')?.getAttribute('aria-expanded'))).toBe('true');
    const nav=await browser.evaluate(()=>{const n=document.querySelector('#docs-nav') as HTMLElement;return {client:n.clientWidth,scroll:n.scrollWidth};});
    expect(nav.scroll).toBeLessThanOrEqual(nav.client+1);
    await browser.keyboard.press('Escape');
    expect(await browser.evaluate(()=>document.activeElement?.classList.contains('menu'))).toBe(true);
  }
});
