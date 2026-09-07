export function accountDeletion({api,t,beforeOpen,onClose,onDeleted},doc=document){
 const el=id=>doc.getElementById(id),dialog=el('account-dialog'),yes=el('delete-yes'),no=el('delete-no'),arena=el('delete-arena');
 let stage=0,jumps=0,busy=false;
 function close(){if(busy)return;dialog.close();onClose();}
 function escape(){
  if(stage!==1||jumps>=3||busy)return false;
  // Three separate bands guarantee a different position, within the dialog.
  const width=Math.max(0,arena.clientWidth-yes.offsetWidth);
  const band=[0.05,0.7,0.3][jumps];
  yes.style.left=`${Math.min(width,width*(band+Math.random()*0.2))}px`;
  yes.style.top=`${56+jumps*42+Math.random()*12}px`;
  jumps++;el('delete-error').textContent=jumps===3?t('delete-ready'):`${t('delete-jumps')} ${jumps}/3`;
  return true;
 }
 yes.onpointerenter=e=>{if(e.pointerType==='mouse')escape();};
 // Touch and keyboard activations get the same three escapes, then confirmation.
 yes.onclick=async()=>{
  if(busy||escape())return;
  if(stage===1){stage=2;el('account-title').textContent=t('delete-final');el('delete-error').textContent='';yes.style.left='';yes.style.top='';arena.classList.remove('escaping');no.focus();return;}
  if(stage!==2)return;
  busy=true;yes.disabled=true;no.disabled=true;el('account-close').disabled=true;
  el('delete-error').textContent=t('settings-pending');
  try{const result=await api('account/delete',{confirmed:true});if(result.deleted!==true)throw new Error('Unconfirmed');dialog.close();onDeleted();}
  catch{el('delete-error').textContent=t('delete-unknown');}
  finally{busy=false;yes.disabled=false;no.disabled=false;el('account-close').disabled=false;}
 };
 el('delete-account').onclick=()=>{stage=1;jumps=0;el('delete-account').hidden=true;arena.hidden=false;arena.classList.add('escaping');el('account-title').textContent=t('delete-question');yes.style.left='';yes.style.top='';no.focus();};
 no.onclick=close;el('account-close').onclick=close;
 dialog.oncancel=e=>{e.preventDefault();close();};
 return {open:async()=>{if(!await beforeOpen())return;stage=0;jumps=0;el('account-title').textContent=t('account-title');el('account-copy').textContent=t('delete-copy');el('delete-account').textContent=t('delete-account');el('delete-account').hidden=false;arena.hidden=true;arena.classList.remove('escaping');yes.textContent=t('yes');no.textContent=t('no');el('account-close').textContent=t('close');el('delete-error').textContent='';dialog.showModal();}};
}
