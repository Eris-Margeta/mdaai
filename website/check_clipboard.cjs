'use strict';
// Execute the actual app handler with an unavailable permission response.
// DOM/permission doubles are necessary here; this is not OS clipboard evidence.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/assets/app.js', 'utf8');
async function check(mode) {
  const nodes = new Map();
  const element = () => ({dataset:{},setAttribute(){},addEventListener(){},classList:{remove(){},contains(){return false;}},focus(){},remove(){},select(){},style:{},contains(){return false;},querySelectorAll(){return [];},getBoundingClientRect(){return {top:0};},scrollTo(){}});
  const status = {textContent:''};
  const code = {textContent:'safe website example\nsecond line'};
  const block = {querySelector: s => s === 'code' ? code : status};
  let handler, fallbackCalls = 0;
  const button = {...element(),textContent:'Copy',closest:()=>block,addEventListener:(_,f)=>{handler=f;}};
  const document = {
    fonts:{ready:Promise.resolve()},documentElement:element(),body:{...element(),append(){}},
    querySelector:s=>{if(!nodes.has(s))nodes.set(s,element());return nodes.get(s);},
    getElementById:s=>{if(!nodes.has(s))nodes.set(s,element());return nodes.get(s);},
    querySelectorAll:s=>s === '.copy' ? [button] : [],
    addEventListener(){},createElement:element,
    execCommand:()=>{fallbackCalls++;return false;}
  };
  const navigator = mode === 'absent' ? {} : {clipboard:{writeText:()=>mode === 'pending' ? new Promise(()=>{}) : Promise.reject(new Error('permission denied'))}};
  vm.runInNewContext(source,{document,navigator,window:{addEventListener(){}},location:{hash:""},localStorage:{getItem(){return null;}},setTimeout,clearTimeout});
  const outcome = await Promise.race([handler().then(()=> 'settled'),new Promise(r=>setTimeout(()=>r('hung'),2200))]);
  assert.equal(outcome,'settled',mode + ': copy handler must settle within a bounded interval');
  assert.equal(fallbackCalls,1,mode + ': unavailable async API must try fallback once');
  assert.equal(status.textContent,'Copy unavailable. Select the code and copy manually.');
  assert.equal(button.textContent,'Copy');
  console.log(mode + ': bounded failure, no fabricated success');
}
(async()=>{for(const mode of ['pending','rejected','absent'])await check(mode);})().catch(e=>{console.error(e);process.exitCode=1;});
