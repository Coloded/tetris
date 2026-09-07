import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Execute the actual UI handlers with a small DOM and controllable transport.
// No real Telegram accounts or production database are used.
function fixture(){
 const elements=new Map(),events={},requests=[],queue=[];
 function el(id){if(!elements.has(id))elements.set(id,{value:'',checked:false,disabled:false,hidden:false,textContent:'',open:false,classList:{add(){},remove(){},toggle(){}},setAttribute(){},replaceChildren(){},getContext(){return {}},showModal(){this.open=true},close(){this.open=false},append(){},querySelector(){return null}});return elements.get(id);}
 const context=vm.createContext({accountDeletion:()=>({open(){}}),console,URL,AbortSignal,Intl,performance,location:{href:'https://example.test/'},navigator:{language:'en'},localStorage:{getItem(){return 'en'}},window:{addEventListener(name,fn){events[name]=fn}},document:{getElementById:el,createElement:()=>el(Symbol()),querySelectorAll:()=>[],documentElement:{},body:{classList:{add(){},remove(){}}},addEventListener(name,fn){events[name]=fn},hidden:false},setInterval(){},setTimeout(){},clearTimeout(){},fetch:async(url,options)=>{requests.push({path:new URL(url).pathname,body:options.body});const fn=queue.shift();assert.ok(fn,'unexpected request');return fn();}});
 let source=readFileSync(new URL('../public/app.js',import.meta.url),'utf8').replace(/^import .*\n/,'').replace(/boot\(\);\s*$/,'');
 vm.runInContext(source,context);
 const board=(hidden=false,version=0,code='RU',can_change=true)=>({privacy:{hidden,version},country:{code,can_change,top:[],me:null},top:[],me:{score:0,rank:1,name:'Tester'}});
 function set(data){context.data=data;vm.runInContext("token='test';rankData=data;renderRank();",context);}
 const ok=data=>()=>({ok:true,json:async()=>data});
 const fail=()=>{throw new TypeError('Network unavailable');};
 set(board());
 return {el,queue,requests,events,board,set,ok,fail,run:s=>vm.runInContext(s,context)};
}

test('switch remains confirmed until acknowledgement, both on and off',async()=>{
 const f=fixture();let resolve;
 f.queue.push(()=>new Promise(r=>resolve=r));
 f.el('quiet-mode').checked=true;const saving=f.el('quiet-mode').onchange();
 assert.equal(f.el('quiet-mode').checked,false);assert.equal(f.el('quiet-mode').disabled,true);
 resolve(f.ok(f.board(true,1))());await saving;
 assert.equal(f.el('quiet-mode').checked,true);assert.equal(f.el('quiet-mode').disabled,false);
 f.queue.push(f.ok(f.board(false,2)));f.el('quiet-mode').checked=false;await f.el('quiet-mode').onchange();
 assert.equal(f.el('quiet-mode').checked,false);assert.equal(f.el('quiet-mode').disabled,false);
});

test('lost request and failed read preserve old state with persistent offline warning',async()=>{
 const f=fixture();f.set(f.board(true,1));f.queue.push(f.fail,f.fail);
 f.el('quiet-mode').checked=false;await f.el('quiet-mode').onchange();
 assert.equal(f.el('quiet-mode').checked,true);assert.equal(f.el('quiet-mode').disabled,true);
 assert.equal(f.el('settings-status').hidden,false);assert.match(f.el('settings-message').textContent,/No connection/);
 f.queue.push(f.ok(f.board(true,1)));await f.el('settings-retry').onclick();
 assert.equal(f.el('quiet-mode').checked,true);assert.equal(f.el('quiet-mode').disabled,false);assert.equal(f.el('settings-status').hidden,true);
});

test('lost acknowledgement reconciles actual committed privacy without resending',async()=>{
 const f=fixture();f.queue.push(f.fail,f.ok(f.board(true,1)));
 f.el('quiet-mode').checked=true;await f.el('quiet-mode').onchange();
 assert.equal(f.el('quiet-mode').checked,true);assert.equal(f.el('quiet-mode').disabled,false);
 assert.deepEqual(f.requests.map(r=>r.path),['/api/privacy','/api/leaderboard']);
});

test('country failure does not claim saved or consume local change; reconnect reads database',async()=>{
 const f=fixture();f.el('country-select').value='DE';f.el('country-dialog').open=true;f.run('renderRank()');
 f.queue.push(f.fail,f.fail);await f.el('save-country').onclick();
 assert.equal(f.run('rankData.country.code'),'RU');assert.equal(f.run('rankData.country.can_change'),true);
 assert.equal(f.el('country-dialog').open,true);assert.equal(f.el('save-country').disabled,true);
 f.queue.push(f.ok(f.board(false,1,'DE',false)));await f.events.online();
 assert.equal(f.run('rankData.country.code'),'DE');assert.equal(f.el('save-country').disabled,true);
 assert.equal(f.requests.filter(r=>r.path==='/api/country').length,1);
});

test('country committed but acknowledgement lost is read back and confirmed',async()=>{
 const f=fixture();f.el('country-select').value='DE';f.el('country-dialog').open=true;f.run('renderRank()');
 f.queue.push(f.fail,f.ok(f.board(false,1,'DE',false)));await f.el('save-country').onclick();
 assert.equal(f.run('rankData.country.code'),'DE');assert.equal(f.el('country-dialog').open,false);
});

test('out of order snapshots cannot revert confirmed country or privacy',()=>{
 const f=fixture();f.set(f.board(true,3,'DE',false));f.run("acceptRank({privacy:{hidden:false,version:2},country:{code:'RU',can_change:true}})");
 assert.equal(f.run('rankData.privacy.hidden'),true);assert.equal(f.run('rankData.country.code'),'DE');
});

test('opening top always fetches, offline event warns and reconnect fetches again',async()=>{
 const f=fixture();f.queue.push(f.ok(f.board(true,1)));f.el('rank-tab').onclick();await f.run('refreshPromise');
 assert.equal(f.el('quiet-mode').checked,true);f.events.offline();assert.match(f.el('settings-message').textContent,/No connection/);
 f.queue.push(f.ok(f.board(false,2)));await f.events.online();assert.equal(f.el('quiet-mode').checked,false);
 assert.equal(f.requests.length,2);
});
