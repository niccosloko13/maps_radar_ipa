const test=require('node:test'),assert=require('node:assert/strict');const {analyze}=require('../app/ui/radar-audit.js');
const point=(kind,lon,lat,props={})=>({type:'Feature',geometry:{type:'Point',coordinates:[lon,lat]},properties:{kind,...props}});
test('counts only radar types and distinguishes declared evidence',()=>{
 const x=analyze([point('fixed',-46.55,-23.7,{trust:'official',speed_limit:60,direction_type:1,direction:90,source:'der_sp',source_date:'2026-10-20'}),point('signal',-46.56,-23.7)],Date.parse('2026-10-28T00:00:00Z'));
 assert.equal(x.total,1);assert.equal(x.official,1);assert.equal(x.withSpeed,1);assert.equal(x.withDirection,1);assert.equal(x.withDate,1);assert.equal(x.stale,0);
});
test('does not treat an absent verification date as recent',()=>{
 const x=analyze([point('mobile',-46.55,-23.7,{source:'community',trust:'community'})]);
 assert.equal(x.unknownDate,1);assert.equal(x.withDate,0);assert.equal(x.community,1);
});
test('flags aging dates and potential collocated duplicate records, not certified duplicates',()=>{
 const x=analyze([point('fixed',-46.55001,-23.70001,{source_date:'2025-01-01'}),point('fixed',-46.55002,-23.70002,{source_date:'2025-01-02'})],Date.parse('2026-10-28T00:00:00Z'));
 assert.equal(x.stale,2);assert.equal(x.possibleDuplicates,1);
});
test('flags invalid coordinates without discarding inventory entries',()=>{
 const x=analyze([point('fixed',0,0),point('red_light',-46.5,-23.8)]);
 assert.equal(x.total,2);assert.equal(x.invalidCoordinates,1);
});
