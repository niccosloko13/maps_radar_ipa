/* RELAS public forecast adapter. No fictitious live data; do not confuse forecast with official warnings. */
(function(root){
'use strict';
const cache=new Map();
async function forecast(lat,lon){
 const a=Number(lat),b=Number(lon);
 if(!Number.isFinite(a)||!Number.isFinite(b)||a< -34||a> -18||b< -55||b> -43)throw Error('Localização fora da cobertura');
 const key=a.toFixed(2)+','+b.toFixed(2),old=cache.get(key);
 if(old&&Date.now()-old.time<600000)return old.data;
 const url='https://api.open-meteo.com/v1/forecast?latitude='+encodeURIComponent(a.toFixed(2))+'&longitude='+encodeURIComponent(b.toFixed(2))+'&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&hourly=precipitation_probability,temperature_2m,precipitation&forecast_hours=6&timezone=America%2FSao_Paulo';
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),9000);
 try{
 const response=await fetch(url,{signal:controller.signal,cache:'no-store'});
 if(!response.ok)throw Error('Serviço de previsão indisponível');
 const data=await response.json();
 if(!data.current||!Array.isArray(data.hourly?.time))throw Error('Resposta meteorológica incompleta');
 const output={source:'Open-Meteo',updatedAt:data.current.time,temperature:Number(data.current.temperature_2m),precipitation:Number(data.current.precipitation),code:Number(data.current.weather_code),wind:Number(data.current.wind_speed_10m),hours:data.hourly.time.map((time,i)=>({time,probability:data.hourly.precipitation_probability?.[i],temperature:data.hourly.temperature_2m?.[i],precipitation:data.hourly.precipitation?.[i]})).slice(0,6)};
 cache.set(key,{time:Date.now(),data:output});return output;
 }finally{clearTimeout(timeout)}
}
root.RelasForecast={forecast};
})(globalThis);
