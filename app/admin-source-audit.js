/* RELAS read-only source and geospatial audit. Authenticated admin routes only. */
(()=>{'use strict';
const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
async function get(path){const res=await fetch(path,{cache:'no-store',credentials:'same-origin'});if(!res.ok)throw Error('HTTP '+res.status);return res.json()}
function timestamp(v){if(!v)return null;const n=new Date(v);return Number.isFinite(n.getTime())?n:null}
function age(v){const date=timestamp(v);if(!date)return 'não informado';const days=Math.floor((Date.now()-date.getTime())/86400000);return days>=0?days+' dias':'data futura/inválida'}
async function audit(){
 const panel=$('relasSourcesAudit'),geo=$('relasGeoAudit');if(!panel||!geo)return;panel.textContent='Carregando fontes verificáveis...';
 try{
  const [sources,inventory]=await Promise.all([get('/api/admin/sources'),get('/api/admin/inventory')]);
  const rows=Array.isArray(sources.items)?sources.items:[];
  panel.innerHTML='<div class="source-audit-table"><table><thead><tr><th>Fonte</th><th>Status</th><th>Última tentativa</th><th>Último sucesso</th><th>Mapeados</th><th>Municípios</th></tr></thead><tbody>'+rows.map(x=>{const sync=x.sync||{},cnt=x.counts||{};const ok=sync.status==='ok';const last=sync.finished_at||sync.started_at;return '<tr><td>'+esc(x.name||x.source_id)+'</td><td>'+esc(sync.status||'Sem sincronização registrada')+'</td><td>'+esc(age(last))+'</td><td>'+esc(ok?age(sync.finished_at||sync.started_at):'Não confirmado no registro')+'</td><td>'+esc(cnt.mapped??sync.mapped??0)+'</td><td>'+esc(cnt.municipalities??0)+'</td></tr>'}).join('')+'</tbody></table></div><p class="command-caveat">Último sucesso indica a execução do coletor, não a data de calibração ou operação física do radar. Sem histórico persistente, sucessos anteriores não são inferidos.</p>';
  const radars=inventory.radars||[],invalid=radars.filter(r=>!Number.isFinite(Number(r.latitude))||!Number.isFinite(Number(r.longitude))||r.latitude==null||r.longitude==null),missingSpeed=radars.filter(r=>!(Number(r.speed_limit)>0)),missingDirection=radars.filter(r=>r.direction==null||String(r.direction).trim()==='');
  const sample=radars.filter(r=>r.latitude!=null&&r.longitude!=null).slice(0,35);
  geo.innerHTML='<h3>Auditoria geográfica do inventário exibido</h3><p>Radares carregados: '+radars.length+' · Sem coordenada: '+invalid.length+' · Sem limite: '+missingSpeed.length+' · Sem direção: '+missingDirection.length+'</p><p class="command-caveat">Esta lista é limitada pela API a 500 registros. Não é uma auditoria estadual exaustiva.</p><div class="source-audit-table"><table><thead><tr><th>Radar</th><th>Município</th><th>Limite</th><th>Sentido</th><th>Origem</th><th>Localização</th></tr></thead><tbody>'+sample.map(r=>{let lat=Number(r.latitude),lon=Number(r.longitude);let url='https://www.openstreetmap.org/?mlat='+encodeURIComponent(lat)+'&mlon='+encodeURIComponent(lon)+'#map=18/'+encodeURIComponent(lat)+'/'+encodeURIComponent(lon);return '<tr><td>'+esc(r.name)+'</td><td>'+esc(r.municipality)+'</td><td>'+esc(r.speed_limit??'Não informado')+'</td><td>'+esc(r.direction??'Não informado')+'</td><td>'+esc(r.source??'Não informada')+'</td><td><a target="_blank" rel="noopener noreferrer" href="'+url+'">Conferir ponto</a></td></tr>'}).join('')+'</tbody></table></div>';
 }catch(e){panel.textContent='Auditoria indisponível: '+e.message;geo.textContent='Nenhuma alteração foi feita no banco.'}
}
function init(){ $('relasVerifySources')?.addEventListener('click',audit);document.querySelector('nav button[data-tab="quality"]')?.addEventListener('click',audit)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();