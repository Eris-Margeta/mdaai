import {test} from '@e2e-dev/web';
import {expect} from 'e2e';
import {chromium} from 'playwright';
const base=process.env.E2E_BASE_URL || 'http://127.0.0.1:8765';
for(const width of [375,1440]) for(const theme of ['light','dark']) {
 test(`paper downloads and scholarly metadata ${width}px ${theme}`,async()=>{
  const browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width,height:900}});
  await context.addInitScript(t=>localStorage.setItem('onion-theme',t),theme);
  const page=await context.newPage();
  try {
   const pdfRequests:string[]=[];page.on('request',r=>{if(r.url().endsWith('.pdf'))pdfRequests.push(r.url());});
   await page.goto(base+'/');
   expect(await page.locator('html').getAttribute('data-theme')).toBe(theme);
   expect(await page.locator('#paper a[download]').count()).toBe(1);
   const sections=await page.locator('.article section').evaluateAll(es=>es.map(e=>e.id));
   expect(sections[0]).toBe('paper');
   expect(pdfRequests).toEqual([]);
   await page.locator('#paper a[href="/paper/"]').click();
   expect(new URL(page.url()).pathname).toBe('/paper/');
   expect(await page.locator('#docs-nav a[aria-current="page"]').getAttribute('href')).toBe('/paper/');
   expect(await page.locator('h1').textContent()).toBe('MDAAI: A Protocol for Governing AI-Assisted Development');
   const graph=JSON.parse((await page.locator('script[type="application/ld+json"]').textContent())!);
   const article=graph['@graph'].find((n:any)=>n['@type']==='ScholarlyArticle');
   expect(article.encoding.length).toBe(1);
   expect(await page.locator('#downloads a[download]').count()).toBe(1);
   expect(await page.locator('a[href$="mdaai-paper-clean.pdf"]').count()).toBe(0);
   expect((await context.request.get(base+'/assets/paper/mdaai-paper-clean.pdf')).status()).toBe(404);
   expect(article.author.name).toBe('Eris Margeta Kurdali');
   expect(article.abstract).toBe(await page.locator('#abstract>p').textContent());
   expect(await page.locator('meta[name="citation_pdf_url"]').getAttribute('content')).toBe('https://www.mdaai.internet.technology/assets/paper/mdaai-paper-soft.pdf');
   const link=page.locator('#downloads a[download]').first();await link.focus();
   expect(await link.evaluate(e=>e===document.activeElement)).toBe(true);
   const downloadEvent=page.waitForEvent('download');await page.keyboard.press('Enter');
   const download=await downloadEvent;expect(download.suggestedFilename()).toBe('mdaai-paper-soft.pdf');await download.cancel();
   await page.locator('#section-jump').selectOption('abstract');
   await page.waitForFunction(()=>location.hash==='#abstract' && document.querySelector<HTMLSelectElement>('#section-jump')?.value==='abstract');
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  } finally {await context.close();await browser.close();}
 });
}
