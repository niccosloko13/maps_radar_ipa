// Relas road-test runtime: versioned shell and local MapLibre fallback.
(() => {
  const VERSION = '5.24.0';
  const cssSources = [
    '/vendor/maplibre-gl.css?v=5240',
    `https://unpkg.com/maplibre-gl@${VERSION}/dist/maplibre-gl.css`,
    `https://cdn.jsdelivr.net/npm/maplibre-gl@${VERSION}/dist/maplibre-gl.css`
  ];
  const jsSources = [
    '/vendor/maplibre-gl.js?v=5240',
    `https://unpkg.com/maplibre-gl@${VERSION}/dist/maplibre-gl.js`,
    `https://cdn.jsdelivr.net/npm/maplibre-gl@${VERSION}/dist/maplibre-gl.js`
  ];
  function loadCss(i=0){
    if(i>=cssSources.length) return;
    const l=document.createElement('link'); l.rel='stylesheet'; l.href=cssSources[i];
    l.onerror=()=>{l.remove();loadCss(i+1)}; document.head.appendChild(l);
  }
  function loadScript(i=0){
    if(window.maplibregl) return Promise.resolve();
    if(i>=jsSources.length) return Promise.reject(new Error('MapLibre indisponÃ­vel nas fontes local e CDN'));
    return new Promise((resolve,reject)=>{
      const s=document.createElement('script'); s.src=jsSources[i]; s.async=false;
      s.onload=()=> window.maplibregl ? resolve() : reject(new Error('MapLibre carregou sem expor maplibregl'));
      s.onerror=()=>{s.remove(); loadScript(i+1).then(resolve,reject)};
      document.head.appendChild(s);
    }).catch(()=>loadScript(i+1));
  }
  function loadLocationModules(){const names=['location-parameters','geometry','baseline-engine','fix-quality','location-state-machine','motion-filter','heading-engine','candidate-corridor','route-matcher','confidence-engine','telemetry','metrics-engine','location-engine','replay-engine','debug-view'];return names.reduce((promise,name)=>promise.then(()=>new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='/location/'+name+'.js?v=413';script.onload=resolve;script.onerror=()=>reject(Error('Location module unavailable: '+name));document.head.append(script)})),Promise.resolve()).catch(()=>{window.relasLocationLoadError=true;console.warn('Relas location modules unavailable; baseline active')})}
  function loadUi(){return ['map-ui','weather-layer','../navigation/source-contracts','../navigation/intelligence','../navigation/road-runtime','../navigation/phase-b'].reduce((p,name)=>p.then(()=>new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='/ui/'+name+'.js?v=413';s.onload=resolve;s.onerror=()=>reject(Error('Interface indisponível; recarregue a página'));document.head.append(s)})),Promise.resolve())}
  function loadApp(){
    const s=document.createElement('script'); s.src='/app.js?v=413'; document.body.appendChild(s);
  }
  function fatal(err){
    document.body.innerHTML='<main style="min-height:100dvh;background:#f4f7f8;color:#203643;display:grid;place-items:center;font-family:system-ui;padding:28px"><div style="max-width:430px;text-align:center"><h2>Não foi possível abrir o mapa</h2><p>Confira sua conexão e tente novamente.</p><button style="padding:14px 24px;border:0;border-radius:14px;background:#176f78;color:white;min-height:48px" onclick="location.reload()">Tentar novamente</button></div></main>';
  }

  loadCss();
  loadScript().then(()=>new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='/navigation-core.js?v=413';script.onload=resolve;script.onerror=()=>reject(Error('Não foi possível carregar a navegação'));document.head.append(script)})).then(loadLocationModules).then(loadUi).then(loadApp).catch(fatal);
  if('serviceWorker' in navigator&&window.isSecureContext){
    let controlled=Boolean(navigator.serviceWorker.controller),refreshing=false;
    navigator.serviceWorker.addEventListener('controllerchange',()=>{if(controlled&&!refreshing){if(window.relas?.state.driving){window.relas.state.pendingUpdate=true;return}refreshing=true;location.reload()}controlled=true});
    window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).then(reg=>reg.update()).catch(error=>console.warn('Cache indisponível:',error.message)));
  }
})();
