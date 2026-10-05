import {test} from '@e2e-dev/web';
import {expect} from 'e2e';
import {chromium} from 'playwright';
const base=process.env.E2E_BASE_URL || 'http://127.0.0.1:8765';
test('shared navigation and compact catalog opening',async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:375,height:844}});
 try{
  const routes=['/','/repository-structure/','/how-files-work-together/','/task-lifecycle/','/mdaai-1/','/mdaai-2/','/templates/'];
  for(const route of routes){
   await page.goto(base+route);
   expect(await page.locator('#docs-nav a[href="/templates/"]').count()).toBe(1);
   const current=await page.locator('#docs-nav a[aria-current="page"]').evaluateAll(es=>es.map(e=>e.getAttribute('href')));
   expect(current).toEqual([route]);
  }
  expect(await page.locator('h1').textContent()).toBe('Templates');
  expect(await page.locator('.article>.lede').textContent()).toBe('Choose a template to apply the MDAAI protocol. Configure its governance files for your project; agents and execution tools are separate layers.');
  expect(await page.locator('section#choose').count()).toBe(0);
  expect(await page.locator('#catalog h2').textContent()).toContain('Browse templates');
  expect(await page.locator('#catalog>p').allTextContents()).not.toContain('Two template families, different ways to organize governed work. Inspect the entry point and files before adopting either one.');
  expect(await page.locator('#docs-nav .nav-group').allTextContents()).not.toContain('Templates');
  expect(await page.locator('#choose-template').count()).toBe(1);
  const ids=await page.locator('.article section[id]').evaluateAll(es=>es.map(e=>e.id));
  const options=await page.locator('#section-jump option').evaluateAll(es=>es.map(e=>(e as HTMLOptionElement).value));
  expect(options).toEqual(ids);expect(options).not.toContain('choose-template');
  expect(await page.locator('#section-jump').inputValue()).toBe('catalog');
  const first=await page.locator('.template-card').first().boundingBox();
  const pane=await page.locator('#main').boundingBox();
  expect(first).not.toBeNull();expect(pane).not.toBeNull();
  expect(first!.y).toBeLessThan(844);expect(first!.y+first!.height).toBeGreaterThan(pane!.y);
  await page.goto(base+'/templates/#choose-template');
  await page.waitForFunction(()=>document.querySelector('#section-jump')?.value==='catalog');
  expect(await page.locator('#section-jump').inputValue()).toBe('catalog');
  await page.locator('#section-jump').selectOption('source-versions');
  await page.waitForFunction(()=>location.hash==='#source-versions' && document.querySelector('#section-jump')?.value==='source-versions');
  await page.locator('#main').evaluate((e:any)=>{e.scrollTop=0});
  await page.waitForFunction(()=>document.querySelector('#section-jump')?.value==='catalog');
 }finally{await browser.close();}
});
for(const width of [320,375,768,1440]) for(const theme of ['light','dark']) {
 test(`protocol catalog ${width}px ${theme}`, async()=>{
  const browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width,height:900}});
  await context.addInitScript(t=>localStorage.setItem('onion-theme',t),theme);
  const page=await context.newPage();
  try {
   await page.goto(base+'/templates/');
   await page.evaluate(()=>document.fonts.ready);
   expect(await page.locator('.template-card:visible').count()).toBe(2);
   expect(await page.locator('#template-status').getAttribute('role')).toBe('status');
   expect(await page.locator('#template-status').getAttribute('aria-live')).toBe('polite');
   expect(await page.locator('#template-search').getAttribute('aria-controls')).toBe('template-grid');
   expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)).toBe(false);
   expect(await page.evaluate(()=>document.documentElement.dataset.theme)).toBe(theme);
   if(width===1440){
    const layout=await page.evaluate(()=>{let m=document.querySelector('#main')!.getBoundingClientRect(),a=document.querySelector('.article')!.getBoundingClientRect();return {right:a.right,mainRight:m.right,width:a.width,mainWidth:m.width,aside:getComputedStyle(document.querySelector('aside')!).display,toc:document.querySelectorAll('.toc,.right-toc').length};});
    expect(layout.right).toBe(layout.mainRight);expect(layout.width).toBe(layout.mainWidth);expect(layout.aside).toBe('block');expect(layout.toc).toBe(0);
   }
   const search=page.locator('#template-search');
   await search.focus();await page.keyboard.type('first-generation');
   expect(await page.locator('.template-card:visible').count()).toBe(1);
   expect(await page.locator('#template-status').textContent()).toBe('1 template match');
   await search.fill('MDAAI 2.0');await page.waitForFunction(()=>document.querySelector('#template-status')?.textContent==='1 template match');expect(await page.locator('.template-card:visible').count()).toBe(1);
   await search.fill('no-such-template-zzzz');expect(await page.locator('.template-card:visible').count()).toBe(0);
   expect(await page.locator('#template-empty').isVisible()).toBe(true);
   expect(await page.locator('#template-status').textContent()).toBe('0 templates match');
   await page.keyboard.press('Escape');
   expect(await search.inputValue()).toBe('');expect(await page.locator('.template-card:visible').count()).toBe(2);
   expect(await page.locator('#template-empty').isVisible()).toBe(false);
   expect(await page.locator('#template-status').textContent()).toBe('2 templates');
   const links=await page.locator('.template-actions a,.catalog-contribute a').evaluateAll(es=>es.map(e=>(e as HTMLAnchorElement).href));
   expect(links.length).toBe(6);
   expect(links[0]).toBe('https://github.com/Eris-Margeta/mdaai-template-1');expect(links[2]).toBe('https://github.com/Eris-Margeta/mdaai-template-2');
   for(const n of [1,3]) expect(/^https:\/\/github\.com\/Eris-Margeta\/mdaai-templates\/blob\/[a-f0-9]{40}\/templates\/mdaai-[12]\/AGENTS\.md$/.test(links[n])).toBe(true);
   expect(links[4]).toBe('https://github.com/Eris-Margeta/mdaai-templates/blob/main/CONTRIBUTING.md');expect(links[5]).toBe('https://github.com/Eris-Margeta/mdaai-templates/pulls');
   expect(await page.locator('[class*=cart],[class*=pricing],[class*=category]').count()).toBe(0);
  }finally{await context.close();await browser.close();}
 });
}
test('protocol-first metadata: seven unique titles and literal directory schema',async()=>{
 const browser=await chromium.launch();const page=await browser.newPage();
 try{
  const titles=[];
  for(const route of ['/','/repository-structure/','/how-files-work-together/','/task-lifecycle/','/mdaai-1/','/mdaai-2/','/templates/']){
   await page.goto(base+route);const title=await page.title();titles.push(title);
   const data=await page.locator('script[type="application/ld+json"]').evaluateAll(es=>es.map(e=>JSON.parse(e.textContent||'{}')));
   const text=JSON.stringify(data);expect(text.includes('SoftwareApplication')).toBe(false);
   if(route==='/') expect((title.match(/MDAAI/g)||[]).length).toBe(1);
   if(route==='/templates/'){
    const nodes=data.flatMap(x=>x['@graph']||[x]);
    expect(nodes.filter(x=>x['@type']==='CollectionPage').length).toBe(1);
    const list=nodes.find(x=>x['@type']==='ItemList');expect(list.itemListElement.length).toBe(2);
    expect(text.includes('mdaai-template-1')).toBe(true);expect(text.includes('mdaai-template-2')).toBe(true);
   }
  }
  expect(new Set(titles).size).toBe(7);
 }finally{await browser.close();}
});
