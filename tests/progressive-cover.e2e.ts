import { test } from '@e2e-dev/web';
import { expect } from 'e2e';
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const inventory = JSON.parse(readFileSync('website/assets/cover/inventory.json', 'utf8'));
const base = process.env.E2E_BASE_URL || 'http://127.0.0.1:8765';
// Parse marker segments and skip entropy stuffing/restart bytes, not a byte-count heuristic.
function jpeg(data: Buffer) {
  let i=2, width=0, height=0, sof=0, scans=0;
  expect(data.readUInt16BE(0)).toBe(0xffd8);
  while(i<data.length) {
    if(data[i++]!==0xff) continue;
    while(data[i]===0xff) i++;
    const marker=data[i++];
    if(marker===0 || (marker>=0xd0 && marker<=0xd7)) continue;
    if(marker===0xd9) break;
    const length=data.readUInt16BE(i);
    if(marker===0xc2 || marker===0xc0) {sof=marker;height=data.readUInt16BE(i+3);width=data.readUInt16BE(i+5);}
    if(marker===0xda) scans++;
    i+=length;
  }
  return {width,height,sof,scans};
}

test('cover inventory preserves master and progressive encoded dimensions', {tags:['progressive-cover']}, async()=>{
  const master=readFileSync('website/'+inventory.master.path);
  expect(createHash('sha256').update(master).digest('hex')).toBe(inventory.master.sha256);
  for(const asset of inventory.assets) {
    const bytes=readFileSync('website/'+asset.path), parsed=jpeg(bytes);
    expect(createHash('sha256').update(bytes).digest('hex')).toBe(asset.sha256);
    expect(bytes.length).toBe(asset.bytes);expect(parsed.sof).toBe(0xc2);
    expect(parsed.scans).toBeGreaterThan(1);expect(parsed.width).toBe(asset.width);expect(parsed.height).toBe(asset.height);
  }
});

for(const width of [320,375,1440]) for(const dpr of [1,2,3]) {
  test(`cold throttled eager progressive cover ${width}px DPR${dpr}`, {tags:['progressive-cover']}, async()=>{
    const browser=await chromium.launch();
    const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:dpr,serviceWorkers:'block'});
    const page=await context.newPage();
    const cdp=await context.newCDPSession(page);
    const requests:any[]=[];const priorities=new Map<string,string>();
    let release!:()=>void;
    const gate=new Promise<void>(resolve=>release=resolve);
    await page.route('**/assets/cover/*.jpg',async route=>{await gate;await route.continue();});
    await cdp.send('Network.enable');await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});
    await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:100,downloadThroughput:200000,uploadThroughput:100000});
    cdp.on('Network.requestWillBeSent',event=>{
      if(event.type==='Image') {requests.push(event);priorities.set(event.requestId,event.request.initialPriority);}
    });
    cdp.on('Network.resourceChangedPriority',event=>priorities.set(event.requestId,event.newPriority));
    await page.addInitScript(()=>{
      (window as any).__coverCLS=0;
      new PerformanceObserver(list=>{for(const entry of list.getEntries() as any[]) {
        if(!entry.hadRecentInput && entry.sources?.some((s:any)=>s.node?.matches?.('.documentation-cover, .documentation-cover *') || s.node?.closest?.('.documentation-cover'))) (window as any).__coverCLS+=entry.value;
      }}).observe({type:'layout-shift',buffered:true});
    });
    try {
      const documentResponse=await page.goto(base+'/',{waitUntil:'domcontentloaded'});
      const initial=await documentResponse!.text();
      const tag=initial.match(/<img\b[^>]*srcset="[^"]*assets\/cover\/[^>]*>/)?.[0] || '';
      expect(tag.includes('loading="eager"')).toBe(true);expect(tag.includes('fetchpriority="high"')).toBe(true);
      const image=page.locator('.documentation-cover img');
      const before=await image.evaluate((e:HTMLImageElement)=>({complete:e.complete,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,loading:e.loading,priority:e.fetchPriority,attrs:[e.getAttribute('width'),e.getAttribute('height')],sizes:e.sizes}));
      // Linux's classic scrollbar reserves 15px; macOS reserves 12px.
      // Derive the bounded mobile box from its real grid content width, not OS pixels.
      const expectedWidth=width===1440?352:await page.locator('.homepage-intro').evaluate(e=>Math.min(272,e.clientWidth));
      expect(before.complete).toBe(false);expect(before.width).toBe(expectedWidth);
      expect(Math.abs(before.height-(width===1440?440:expectedWidth*1.3))).toBeLessThan(0.02);
      expect(before.attrs).toEqual(['1000','1300']);expect(before.loading).toBe('eager');expect(before.priority).toBe('high');expect(before.sizes).toBe(inventory.sizes);
      release();
      await image.evaluate((e:HTMLImageElement)=>e.decode());
      await page.evaluate(()=>new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve()))));
      const after=await image.evaluate((e:HTMLImageElement)=>({src:e.currentSrc,naturalWidth:e.naturalWidth,naturalHeight:e.naturalHeight,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,cls:(window as any).__coverCLS}));
      expect(after.width).toBe(before.width);expect(after.height).toBe(before.height);expect(after.cls).toBe(0);
      const selected=inventory.assets.find((a:any)=>after.src.endsWith('/'+a.path));
      expect(!!selected).toBe(true);
      // Selection is allowed to reflect Chromium's throttled-network intervention.
      // The descriptor density, not device DPR, corrects naturalWidth/naturalHeight.
      // naturalWidth follows the advertised sizes slot, not the painted box.
      // At 320px Linux's gutter makes that box 3px narrower without layout drift.
      const slotWidth=width<=1000?Math.min(272,width-48):Math.min(352,width*0.45945946-142.891892);
      const density=selected.width/slotWidth;
      expect(Math.abs(after.naturalWidth-selected.width/density)).toBeLessThanOrEqual(1);
      expect(Math.abs(after.naturalHeight-selected.height/density)).toBeLessThanOrEqual(1);
      const fetched=requests.filter(e=>/assets\/(cover\/|brand\/mdaai-guardian-cover)/.test(e.request.url));
      expect(fetched.length).toBe(1);expect(fetched[0].request.url).toBe(after.src);
      expect(['High','VeryHigh'].includes(priorities.get(fetched[0].requestId)!)).toBe(true);
      const bytes=await (await context.request.get(after.src)).body(), encoded=jpeg(bytes);
      expect(encoded.width).toBe(selected.width);expect(encoded.height).toBe(selected.height);expect(encoded.sof).toBe(0xc2);expect(encoded.scans).toBeGreaterThan(1);
      expect(createHash('sha256').update(bytes).digest('hex')).toBe(selected.sha256);
      console.log(JSON.stringify({width,dpr,currentSrc:after.src,encodedWidth:encoded.width,naturalWidth:after.naturalWidth,box:{width:after.width,height:after.height},imageCLS:after.cls,priority:priorities.get(fetched[0].requestId)}));
    } finally {release();await context.close();await browser.close();}
  });
}
