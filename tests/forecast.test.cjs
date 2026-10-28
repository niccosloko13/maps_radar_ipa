const test=require('node:test'),assert=require('node:assert/strict');
require('../app/ui/forecast.js');
test('forecast uses coarse coordinates and labels its source',async()=>{
 const original=globalThis.fetch;
 let captured;
 globalThis.fetch=async url=>{captured=url;return {ok:true,json:async()=>({current:{time:'2026-10-28T20:00',temperature_2m:21,precipitation:0,weather_code:2,wind_speed_10m:12},hourly:{time:['2026-10-28T20:00'],precipitation_probability:[55],temperature_2m:[21],precipitation:[0.2]}})}};
 try{const result=await globalThis.RelasForecast.forecast(-23.672983,-46.546788);assert.equal(result.source,'Open-Meteo');assert.equal(result.hours[0].probability,55);assert.match(captured,/latitude=-23\.67/);assert.match(captured,/longitude=-46\.55/);assert.doesNotMatch(captured,/23\.6729/)}
 finally{globalThis.fetch=original}
});
test('forecast rejects coordinates outside São Paulo region',async()=>{
 await assert.rejects(globalThis.RelasForecast.forecast(40,-73),/fora da cobertura/);
});
