import {test} from 'node:test';
import assert from 'node:assert/strict';
import {accountDeletion} from '../public/account.js';
function setup(){
 const nodes=new Map();const get=id=>{if(!nodes.has(id))nodes.set(id,{style:{},clientWidth:300,offsetWidth:80,classList:{add(){},remove(){}},focus(){},showModal(){this.open=true},close(){this.open=false}});return nodes.get(id);};
 let calls=0,deleted=0,fail=false,closed=0;
 const flow=accountDeletion({t:k=>k,beforeOpen:async()=>true,onClose:()=>closed++,onDeleted:()=>deleted++,api:async(path,body)=>{calls++;assert.equal(path,'account/delete');assert.deepEqual(body,{confirmed:true});if(fail)throw new Error('offline');return {deleted:true};}},{getElementById:get});
 return {get,flow,calls:()=>calls,deleted:()=>deleted,closed:()=>closed,setFail:v=>fail=v};
}
test('three mouse escapes then a separate final confirmation before deletion',async()=>{
 const f=setup();await f.flow.open();f.get('delete-account').onclick();const yes=f.get('delete-yes');
 const positions=[];for(let i=0;i<3;i++){yes.onpointerenter({pointerType:'mouse'});positions.push(yes.style.top);}
 assert.equal(new Set(positions).size,3);const last=yes.style.top;yes.onpointerenter({pointerType:'mouse'});assert.equal(yes.style.top,last);
 await yes.onclick();assert.equal(f.calls(),0);assert.equal(f.get('account-title').textContent,'delete-final');
 await yes.onclick();assert.equal(f.calls(),1);assert.equal(f.deleted(),1);
});
test('touch or keyboard escape three times and No cancels with zero requests',async()=>{
 const f=setup();await f.flow.open();f.get('delete-account').onclick();
 for(let i=0;i<3;i++)await f.get('delete-yes').onclick();
 assert.equal(f.calls(),0);await f.get('delete-yes').onclick();f.get('delete-no').onclick();assert.equal(f.calls(),0);assert.equal(f.closed(),1);
});
test('connection failure keeps final confirmation open and allows safe retry',async()=>{
 const f=setup();await f.flow.open();f.get('delete-account').onclick();for(let i=0;i<4;i++)await f.get('delete-yes').onclick();
 f.setFail(true);await f.get('delete-yes').onclick();assert.equal(f.deleted(),0);assert.equal(f.get('account-dialog').open,true);assert.equal(f.get('delete-error').textContent,'delete-unknown');
 f.setFail(false);await f.get('delete-yes').onclick();assert.equal(f.deleted(),1);
});
