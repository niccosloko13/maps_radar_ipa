// Connected Playwright function: GPS, route HUD, follow and safe fallbacks.
async (page) => {
 const result={errors:[],gps:{},driveViewports:[]},check=(ok,message)=>{if(!ok)throw Error(message)};
 page.on('pageerror',e=>result.errors.push(e.message));
 await page.context().grantPermissions(['geolocation'],{origin:'http://127.0.0.1:8815'});
 await page.context().setGeolocation({latitude:-23.69,longitude:-46.55,accuracy:8});
 await page.setViewportSize({width:390,height:844});
 await page.goto('http://127.0.0.1:8815/?v=232');
 await page.waitForLoadState('networkidle');
 await page.waitForFunction(()=>window.relas?.state.position&&relas.map.getSource('relas-route-alerts'));
 result.gps.start=await page.evaluate(()=>({watch:relas.state.watch!==null,indicator:document.querySelector('#gpsIndicator').textContent}));
 // Actual autocomplete and external routing provider; origin is a fixed test coordinate.
 result.search=await page.evaluate(async()=>{const r=await fetch('/api/autocomplete?q='+encodeURIComponent('São Bernardo do Campo')+'&lat=-23.69&lon=-46.55');const j=await r.json();return {status:r.status,results:j.items.length,label:j.items[0]?.label}});
 check(result.search.status===200&&result.search.results>0,'Autocomplete unavailable');
 const actual=await page.evaluate(async()=>{const r=await fetch('/api/route?flat=-23.69&flon=-46.55&tlat=-23.68&tlon=-46.54'),j=await r.json();if(!r.ok||j.error)throw Error(j.error||'Route failed');await relas.setRoute(j);return {provider:j.provider,distance:j.distance_m,steps:j.steps.length,alerts:j.alerts.length,engine:j.alerts_engine}});
 result.route=actual;check(actual.distance>500&&actual.steps>0&&actual.engine==='relas-map-v2','Invalid real route');
 await page.evaluate(()=>{relas.startDrive(false);stopTracking();relas.state.lastFix=null;relas.receivePosition({timestamp:Date.now(),coords:{longitude:-46.55,latitude:-23.69,accuracy:8,speed:12,heading:270}})});
 await page.waitForTimeout(900);
 result.gps.moving=await page.evaluate(async()=>({properties:(await relas.map.getSource('relas-position').getData()).properties,layer:relas.map.queryRenderedFeatures({layers:['relas-user-heading']}).length,speed:document.querySelector('#speed').textContent}));
 check(result.gps.moving.properties.moving&&result.gps.moving.layer>0,'Moving chevron did not render');
 await page.mouse.move(170,410);await page.mouse.down();await page.mouse.move(255,470,{steps:8});await page.mouse.up();await page.waitForFunction(()=>!relas.map.isMoving());
 const dragged=await page.evaluate(()=>{const center=relas.map.getCenter().toArray();updateDrive(relas.state.position,12,270);return {follow:relas.state.follow,recenter:!document.querySelector('#recenter').hidden,center}});
 await page.waitForTimeout(900);const after=await page.evaluate(()=>relas.map.getCenter().toArray());
 result.follow={...dragged,stayed:Math.hypot(after[0]-dragged.center[0],after[1]-dragged.center[1])<.0000001};check(!dragged.follow&&dragged.recenter&&result.follow.stayed,'Drag did not suspend follow '+JSON.stringify({dragged,after}));
 await page.locator('#recenter').click();check(await page.evaluate(()=>relas.state.follow),'Recenter did not restore follow');
 result.gps.stopped=await page.evaluate(async()=>{relas.state.lastFix=null;relas.receivePosition({timestamp:Date.now(),coords:{longitude:-46.55,latitude:-23.69,accuracy:8,speed:0,heading:null}});return(await relas.map.getSource('relas-position').getData()).properties});check(!result.gps.stopped.moving,'Stopped marker should be a dot');
 result.gps.badAccuracy=await page.evaluate(()=>{const before=relas.state.position.slice();relas.receivePosition({timestamp:Date.now(),coords:{longitude:-46.4,latitude:-23.5,accuracy:250,speed:12,heading:90}});return{unchanged:JSON.stringify(before)===JSON.stringify(relas.state.position),status:document.querySelector('#gpsIndicator').textContent}});check(result.gps.badAccuracy.unchanged,'Bad GPS fix moved the map');
 // Controlled straight route through an actual undirected community radar.
 await page.evaluate(async()=>{const all=await(await fetch('/api/map/features?bbox=-53.2,-25.4,-44,-19.7&types=fixed')).json(),f=all.features.find(f=>f.properties.direction_type===0),p=f.geometry.coordinates;window.testAlong=RelasNavigation.geoDistance([p[0]-.018,p[1]],p);window.testRadar={...f.properties,title:'Radar fixo',speed_limit:60,direction_type:0,along_m:testAlong};window.testPoint=p;await relas.setRoute({geometry:{type:'LineString',coordinates:[[p[0]-.018,p[1]],[p[0]+.018,p[1]]]},distance_m:3600,duration_s:240,steps:[{instruction:'Siga pela avenida',distance:3600}],alerts:[],alerts_engine:'relas-map-v2',provider:'controlled-test'});relas.state.alerts=[testRadar];relas.state.cameraPosition=null;relas.state.simulation=true;relas.state.follow=true;});
 result.intensities={};
 for(const [distance,expected] of [[1000,'discreet'],[450,'attention'],[200,'highlight'],[70,'strong']]){
  const state=await page.evaluate(distance=>{const lon=testPoint[0]-.018+(testAlong-distance)/(111320*Math.cos(testPoint[1]*Math.PI/180));updateDrive([lon,testPoint[1]],10,90);return{intensity:document.querySelector('#nextAlert').dataset.intensity,text:document.querySelector('#alertDistance').textContent}},distance);
  result.intensities[distance]=state;check(state.intensity===expected,'Wrong alert intensity '+distance);
 }
 result.overspeed=await page.evaluate(()=>{const lon=testPoint[0]-.018+(testAlong-200)/(111320*Math.cos(testPoint[1]*Math.PI/180));updateDrive([lon,testPoint[1]],20,90);return document.querySelector('#nextAlert').dataset.overspeed==='true'});check(result.overspeed,'Speed contrast did not activate');
 await page.waitForTimeout(850);await page.screenshot({path:'artifacts/road-test-review/alert.png'});
 result.direction=await page.evaluate(()=>{relas.state.alerts=[{...testRadar,direction_type:1,direction:270}];const lon=testPoint[0]-.018+(testAlong-200)/(111320*Math.cos(testPoint[1]*Math.PI/180));updateDrive([lon,testPoint[1]],10,90);const hidden=document.querySelector('#nextAlert').hidden;relas.state.alerts=[testRadar];relas.state.cameraPosition=null;updateDrive([lon,testPoint[1]],10,90);return{oppositeSuppressed:hidden,unknownVisible:!document.querySelector('#nextAlert').hidden}});check(result.direction.oppositeSuppressed&&result.direction.unknownVisible,'Direction guard failed');
 for(const viewport of [{width:375,height:812},{width:390,height:844},{width:430,height:932},{width:412,height:915}]){
  await page.setViewportSize(viewport);await page.waitForTimeout(200);const metrics=await page.evaluate(()=>{const small=[...document.querySelectorAll('#drive button,#reportBtn,#recenter')].filter(b=>b.getClientRects().length).filter(b=>{const r=b.getBoundingClientRect();return r.width<44||r.height<44}).map(b=>b.id);const man=document.querySelector('.maneuver').getBoundingClientRect(),alert=document.querySelector('.alert').getBoundingClientRect(),bottom=document.querySelector('.drive-bottom').getBoundingClientRect();return{small,overflow:document.documentElement.scrollWidth>innerWidth,hudFits:man.left>=0&&man.right<=innerWidth&&bottom.left>=0&&bottom.right<=innerWidth,alertBelowManeuver:document.body.classList.contains('radar-first')?man.top>=alert.bottom:alert.top>=man.bottom}});
  check(!metrics.overflow&&metrics.hudFits&&metrics.alertBelowManeuver&&metrics.small.length===0,'Driver mobile layout failed '+JSON.stringify(metrics));result.driveViewports.push({...viewport,...metrics});if(viewport.width===390)await page.screenshot({path:'artifacts/road-test-review/mobile-driver.png'});
 }
 await page.locator('.eta').click();result.routeSummary=await page.locator('#sheetContent').innerText();await page.locator('#closeSheet').click();
 // Submission body is intercepted: never insert a synthetic road incident in production data.
 let reportBody=null;await page.route('**/api/map/report',async route=>{reportBody=route.request().postDataJSON();await route.fulfill({status:200,contentType:'application/json',body:'{"ok":true,"id":"smoke-only"}'})});
 await page.locator('#reportBtn').click();result.reportOptions=await page.locator('[data-report]').count();await page.locator('[data-report="mobile"]').click();await page.waitForSelector('#sheet:not([open])',{state:'attached'});result.report={bodyPresent:!!reportBody,kind:reportBody?.kind,coordinatesValid:Number.isFinite(reportBody?.longitude)&&Number.isFinite(reportBody?.latitude)};check(result.reportOptions===15&&result.report.coordinatesValid,'Report flow failed');await page.unroute('**/api/map/report');
 result.updateSafety=await page.evaluate(()=>{navigator.serviceWorker.dispatchEvent(new Event('controllerchange'));return{pending:relas.state.pendingUpdate===true,stillDriving:relas.state.driving}});check(result.updateSafety.pending&&result.updateSafety.stillDriving,'Update interrupted driving');await page.locator('#exitDrive').click();await page.waitForLoadState('networkidle');
 // Explicitly missing and denied GPS: product must remain usable, not crash.
 for(const mode of ['missing','denied']){
  const fallback=await page.context().newPage();await fallback.addInitScript(mode=>{if(mode==='missing')Object.defineProperty(navigator,'geolocation',{value:undefined,configurable:true});else Object.defineProperty(navigator,'geolocation',{value:{watchPosition:(ok,fail)=>{setTimeout(()=>fail({code:1}),0);return 1},clearWatch:()=>{},getCurrentPosition:(ok,fail)=>fail({code:1})},configurable:true})},mode);
  await fallback.goto('http://127.0.0.1:8815/?v=232&gps-test='+mode);await fallback.waitForFunction(()=>window.relas?.state.gpsState==='error');const text=await fallback.locator('#gpsIndicator').innerText();check(text.includes(mode==='missing'?'indisponível':'negada'),'Wrong GPS fallback '+text);result.gps[mode]=text;await fallback.close();
 }
 result.sw=await page.evaluate(async()=>({controller:navigator.serviceWorker.controller?.scriptURL,caches:await caches.keys()}));check(result.sw.caches.includes('relas-v233-road-test'),'Wrong app cache');check(result.errors.length===0,'JS errors '+result.errors.join(';'));
 return result;
}
