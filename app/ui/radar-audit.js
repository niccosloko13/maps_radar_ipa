/* Read-only radar provenance audit for the currently loaded viewport. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.RelasRadarAudit=factory()})(globalThis,()=>{
 'use strict';
 const kinds=new Set(['fixed','signal_radar','red_light','mobile']);
 const days=(v,now)=>{if(!v)return null;const n=Date.parse(v);return Number.isFinite(n)?(now-n)/86400000:null};
 function analyze(features,now=Date.now()){
  const out={scope:'viewport',total:0,official:0,confirmed:0,community:0,other:0,withSpeed:0,withDirection:0,withDate:0,stale:0,unknownDate:0,invalidCoordinates:0,possibleDuplicates:0,byType:{},bySource:{}};
  const seen=new Set();
  for(const f of features||[]){
   const p=f?.properties||{};if(!kinds.has(p.kind))continue;
   out.total++;out.byType[p.kind]=(out.byType[p.kind]||0)+1;
   const source=String(p.source||'não informada').slice(0,80);out.bySource[source]=(out.bySource[source]||0)+1;
   if(p.trust==='official')out.official++;else if(p.trust==='confirmed')out.confirmed++;else if(p.trust==='community')out.community++;else out.other++;
   if(Number(p.speed_limit)>0&&Number(p.speed_limit)<=140)out.withSpeed++;
   if(Number(p.direction_type)>0&&Number.isFinite(Number(p.direction)))out.withDirection++;
   const age=days(p.source_date||p.last_seen||p.updated_at||p.imported_at,now);
   if(age===null||age<0)out.unknownDate++;else{out.withDate++;if(age>180)out.stale++}
   const coords=f.geometry?.coordinates;
   if(!Array.isArray(coords)||!Number.isFinite(coords[0])||!Number.isFinite(coords[1])||coords[0]<-55||coords[0]>-43||coords[1]<-27||coords[1]>-18){out.invalidCoordinates++;continue}
   const key=[p.kind,Math.round(coords[0]*10000),Math.round(coords[1]*10000)].join(':');
   if(seen.has(key))out.possibleDuplicates++;else seen.add(key);
  }
  return out;
 }
 return {analyze};
});
