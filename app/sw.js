const CACHE='relas-v414-map-hierarchy';
const LOCATION=['location-parameters','geometry','baseline-engine','fix-quality','location-state-machine','motion-filter','heading-engine','candidate-corridor','route-matcher','confidence-engine','telemetry','metrics-engine','location-engine','replay-engine','debug-view'].map(name=>'/location/'+name+'.js?v=414');
const SHELL=['/navigation/phase-b.js?v=414','/navigation/phase-b.css?v=414',...LOCATION,'/navigation/source-contracts.js?v=414','/navigation/intelligence.js?v=414','/navigation/road-runtime.js?v=414','/navigation/road-mode.css?v=414','/ui/map-ui.js?v=414','/ui/weather-layer.js?v=414','/ui/map-ui.css?v=414','/','/navigation/drive-v4.css?v=414','/styles.css?v=414','/boot.js?v=414','/navigation-core.js?v=414','/app.js?v=414','/icon.svg','/manifest.json','/vendor/maplibre-gl.js?v=5240','/vendor/maplibre-gl.css?v=5240',...['road-state-normal','road-state-selected','road-state-critical','road-state-stale','landslide','erosion','fire','gale','fixed','signal_radar','red_light','mobile','police','bump','toll','signal','prf-post','pm-road-base','police-base','inspection-base','der-base','concessionaire-base','sau','weigh-station','guincho','mechanical-support','fog','closure','animal','object','flood','slippery','user','electronic-bump','other','works','accident','rain','stopped','congestion','user-chevron'].map(kind=>'/icons/'+kind+'.svg?v=414')];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('relas-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()))});
self.addEventListener('message',event=>{if(event.data?.type==='CLEAR_CACHE')event.waitUntil(caches.delete(CACHE))});
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==location.origin||url.pathname.startsWith('/api/')||url.pathname.startsWith('/admin'))return;
 // Network first for HTML/bootstrap: never pin a navigation to an old release.
 // API/auth responses and external map tiles are never cached by this worker.
 const bootstrap=event.request.mode==='navigate'||['/boot.js','/sw.js','/navigation-core.js'].includes(url.pathname);
 if(bootstrap){event.respondWith(fetch(event.request,{cache:'no-cache'}).then(response=>{if(response.ok&&url.pathname!=='/sw.js'){const copy=response.clone();event.waitUntil(caches.open(CACHE).then(cache=>cache.put(event.request,copy)))}return response}).catch(()=>caches.match(event.request).then(hit=>hit||Response.error())));return}
 if(!SHELL.includes(url.pathname+url.search))return;
 event.respondWith(caches.open(CACHE).then(async cache=>{const cached=await cache.match(event.request);if(cached)return cached;const response=await fetch(event.request);if(response.ok)await cache.put(event.request,response.clone());return response}));
});
