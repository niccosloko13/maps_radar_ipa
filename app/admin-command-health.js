/* Command read-only health summary; never claim live sync based on a green UI dot. */
(()=>{'use strict';
 const $=id=>document.getElementById(id);
 const set=(id,value,state)=>{const el=$(id);if(!el)return;el.textContent=String(value);if(state)el.dataset.state=state};
 async function check(){
  set('commandHealthStamp','Verificando API e banco...');
  try{
   const res=await fetch('/api/health',{cache:'no-store',credentials:'same-origin'});
   const j=await res.json();
   set('commandAppStatus',j.app==='ok'?'Operacional':'Indisponível',j.app==='ok'?'ok':'error');
   set('commandDbStatus',j.database==='ok'?'Conectado':'Indisponível',j.database==='ok'?'ok':'error');
   set('commandRadars',j.counts?.radars??'—');
   set('commandObjects',j.counts?.road_objects??'—');
   const date=j.time?new Date(j.time):new Date();
   set('commandHealthStamp','Última consulta: '+(Number.isFinite(date.getTime())?date.toLocaleString('pt-BR'):'horário desconhecido')+' · fonte: API /api/health');
   if(!res.ok)set('commandHealthStamp','Resposta HTTP '+res.status+' · saúde incompleta');
  }catch{
   set('commandAppStatus','Não verificado','error');set('commandDbStatus','Não verificado','error');set('commandRadars','—');set('commandObjects','—');
   set('commandHealthStamp','Consulta indisponível. Não é possível confirmar o estado agora.');
  }
 }
 function boot(){
  $('commandCheckHealth')?.addEventListener('click',check);
  document.querySelectorAll('[data-command-tab]').forEach(b=>b.addEventListener('click',()=>document.querySelector('nav button[data-tab="'+b.dataset.commandTab+'"]')?.click()));
  check();
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)check()});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
