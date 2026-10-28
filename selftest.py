from pathlib import Path
import tempfile, json, io, zipfile, time
import server

FIXTURE='''<html><form><input type="hidden" name="__VIEWSTATE" value="x"><select name="ctl00$Main$ddlSP"><option>Selecione</option><option value="31">SP 031</option></select><table><tr><th>SP</th><th>Rodovia</th><th>Km Inicial</th><th>Sentido</th><th>Latitude</th><th>Longitude</th><th>Tipo Radar</th><th>Número DER</th><th>Velocidade Regulamentada</th><th>Horário</th><th>Em Operação</th></tr><tr><td>SP 031</td><td>Índio Tibiriçá</td><td>056,003</td><td>Leste</td><td>-23,5501</td><td>-46,6301</td><td>Fixo</td><td>DER-123</td><td>60 / 60 km/h</td><td>24h</td><td>Sim</td></tr></table></form></html>'''
KML='''<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>SP-031</name><ExtendedData><Data name="Rodovia"><value>SP-031</value></Data><Data name="Km Inicial"><value>60,000</value></Data><Data name="Km Final"><value>70,000</value></Data><Data name="Latitude Inicial"><value>-23.5000</value></Data><Data name="Longitude Inicial"><value>-46.5000</value></Data><Data name="Latitude Final"><value>-23.6000</value></Data><Data name="Longitude Final"><value>-46.4000</value></Data></ExtendedData><LineString><coordinates>-46.5000,-23.5000,0 -46.4500,-23.5500,0 -46.4000,-23.6000,0</coordinates></LineString></Placemark></Document></kml>'''

def ck(c,m):
    if not c: raise AssertionError(m)
def kmz():
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('doc.kml',KML)
    return b.getvalue()
def mkitem(rid,lon,lat,direction):
    return {'id':rid,'source':'test','external_id':rid,'name':rid,'latitude':lat,'longitude':lon,'speed_limit':60,'speed_text':'60','direction':direction,'status':'active','confidence':99,'municipality':'Teste','state':'SP','road':'Rua Teste','km':None,'radar_type':'radar_fixo','der_number':None,'serial_number':None,'schedule':None,'study_url':None,'source_url':'test','source_date':'2026-10-23','position_quality':'exact_official','inmetro_registration':None,'lanes':None,'local_code':None,'quality_grade':'A'}

def main():
    p=server.parse(FIXTURE);ck(server.road_select(p),'DER selector');r=server.parse_radars(p,'x')[0];ck(r['position_quality']=='exact_official','DER direct grade source')
    segs=server.parse_road_kmz(kmz());rr=dict(r);rr.update({'road':'SP-031','km':'65,000','latitude':None,'longitude':None});ck(server.georef_one(rr,segs),'DER linear reference')
    d,t=server.point_seg_distance_m((-46.45,-23.55),(-46.50,-23.50),(-46.40,-23.60));ck(d<5 and 0.45<t<0.55,'projeção de ponto na rota')
    payload=json.loads(server.SANTO_ANDRE_SNAPSHOT.read_text(encoding='utf-8'));ck(len(payload['items'])>=70,'Santo André snapshot count');sa=payload['items'][0];ck(sa['position_quality']=='exact_official' and sa['quality_grade']=='A' and sa['inmetro_registration'],'Santo André grade A fields')
    # TTL helpers must expire negative cache instead of freezing forever.
    ck(server._cache_entry_items({'ts':time.time(),'items':[1]},10)==[1],'cache TTL positivo')
    ck(server._cache_entry_items({'ts':time.time()-20,'items':[1]},10) is None,'cache TTL expira')

    old_db,old_data,old_geo,old_bumps=server.DB_PATH,server.DATA_DIR,server.GEOCODE_CACHE,server.BUMPS_CACHE
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);server.DATA_DIR=td/'persistent';server.DB_PATH=server.DATA_DIR/'radar.db';server.GEOCODE_CACHE=server.DATA_DIR/'geocode_cache.json';server.BUMPS_CACHE=server.DATA_DIR/'bumps_cache.json'
        server.init_db();server.ensure_v18_tables();ck(server.DB_PATH.exists(),'banco persistente criado/migrado')
        res=server.seed_santo_andre();ck(res['count']>=70,'seed Santo André');pg=server.seed_praia_grande(False);ck(pg['count']==10,'seed Praia Grande oficial');sa2=server.seed_santos(False);ck(sa2['count']>=28,'seed Santos oficial')
        c=server.db();c.execute("update radars set latitude=-24.005,longitude=-46.412,position_quality='test_preserve' where id='pg_official_01'");c.commit();c.close();server.seed_praia_grande(False);c=server.db();r0=c.execute("select latitude,longitude from radars where id='pg_official_01'").fetchone();c.close();ck(r0['latitude']==-24.005 and r0['longitude']==-46.412,'seed não pode apagar coordenada já resolvida')
        # Direction guard: eastbound route must not alert a westbound-only radar.
        c=server.db();seen=server.now();server.upsert(c,mkitem('east',-46.495,-23.5000,'Leste'),seen);server.upsert(c,mkitem('west',-46.495,-23.5000,'Oeste'),seen);c.commit();c.close();server.refresh_physical_ids()
        alerts=server.route_alerts([(-46.50,-23.50),(-46.49,-23.50)])
        ids={a['id'] for a in alerts};ck('east' in ids,'radar no sentido da rota deve entrar');ck('west' not in ids,'radar no sentido oposto não pode alertar')

        server.seed_signal_networks();sn=server.signal_network_state();ck(len(sn)>=3 and any(x['mode']=='adaptive' for x in sn),'redes semafóricas catalogadas')
        rt=server.radar_type_stats();ck('radar_semaforo' in rt and 'lombada_eletronica' in rt,'classificação de fiscalização por tipo')
        c=server.db();obj={'id':'test_signal','source':'osm_road_objects','external_id':'1','object_type':'traffic_signal','name':'Semáforo teste','latitude':-23.9,'longitude':-46.3,'municipality':'Santos','state':'SP','status':'mapped','confidence':60,'official':0,'speed_limit':None,'direction':None,'timing_mode':'unknown','cycle_seconds':None,'green_seconds':None,'red_seconds':None,'adaptive':0,'timing_source':None,'source_url':'test','source_date':'2026'};server._upsert_road_object(c,obj,server.now());c.commit();c.close();ck(server.road_object_stats()['traffic_signal']['mapped']==1,'objeto semafórico no banco')
        st=server.get_stats();ck(st['exact_a']>=70 and st['abc']>=70 and st['inventory']>=110 and st['physical']>0,'stats + physical IDs')
        diag=server.stability_diagnostics();ck(diag['db']['persistent'] and 'geocode' in diag['caches'] and 'bumps' in diag['caches'],'diagnóstico de estabilidade')
        server.checkpoint_db();ck(not Path(str(server.DB_PATH)+'-wal').exists() or Path(str(server.DB_PATH)+'-wal').stat().st_size==0,'WAL checkpoint')
        # Admin Operations v1.5 persistence tables and hardcoded credentials.
        c=server.db();tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()};c.close()
        ck({'municipality_sources','source_gaps','city_scan_jobs','source_attempts','municipality_profiles','radar_validations','manual_entries'}.issubset(tables),'Admin Operations tables')
        ck(server.ADMIN_USER=='admin' and not server.AUTH.configuration_errors(),'admin configured locally')
        ck(server._prepare_city_batch(['Santo André','Santo André'])==['Santo André'],'batch limita e deduplica cidades')
        server._queue_update('Santos','objects','osm_road_objects','Importar objetos viários descobertos · Santos',{'traffic_signal':12,'physical_bump':3});server._oplog('test-op','Teste de observabilidade',stage='teste',municipality='Santos')
        q=server.update_queue_state('pending');ck(any(x['source_id']=='osm_road_objects' and x['municipality']=='Santos' for x in q),'fila de atualização persistente')
        lg=server.operation_logs_state(0,20,'test-op');ck(lg and lg[-1]['message']=='Teste de observabilidade','log operacional filtrável')
        stq=server.queue_state_updates(['antt_sp','der_sp']);ck(len(stq['queued'])==2,'atualizações estaduais entram na fila, não executam direto')
        # Varredura discovery-only deve produzir fila e log sem publicar dados automaticamente.
        old_probe,old_conn,old_scout,old_osm=server._probe_backbones,server._known_connector_probe,server._official_open_data_scout,server.discover_osm_summary_city
        try:
            server._probe_backbones=lambda city:[]
            def fake_conn(city,op):
                server._queue_update(city,'radars','fake_city',f'Atualizar radares oficiais · {city}',{'count':9});server._oplog(op,'Fonte fake acessível',level='success',stage='fonte municipal',municipality=city,source_id='fake_city');return {'source_id':'fake_city','name':'Fonte fake','status':'available','items':9,'mapped':9,'queued':True}
            def fake_osm(city,op):
                server._queue_update(city,'objects','osm_road_objects',f'Importar objetos viários descobertos · {city}',{'traffic_signal':21,'physical_bump':4});server._oplog(op,'21 semáforos e 4 lombadas descobertos',level='success',stage='OSM',municipality=city);return {'source_id':'osm_road_objects','name':'OSM','status':'candidate','items':25,'mapped':25,'queued':True}
            server._known_connector_probe=fake_conn;server._official_open_data_scout=lambda city:[];server.discover_osm_summary_city=fake_osm
            rr=server.discover_city_intelligence('Cidade Teste',True,'scan-flow-test');qq=server.update_queue_state('pending');
            ck(rr['status']=='ready_to_update' and any(x['municipality']=='Cidade Teste' and x['category']=='radars' for x in qq) and any(x['municipality']=='Cidade Teste' and x['category']=='objects' for x in qq),'varredura gera propostas de radar + objetos')
        finally:
            server._probe_backbones,server._known_connector_probe,server._official_open_data_scout,server.discover_osm_summary_city=old_probe,old_conn,old_scout,old_osm

    server.DB_PATH,server.DATA_DIR,server.GEOCODE_CACHE,server.BUMPS_CACHE=old_db,old_data,old_geo,old_bumps


    # Route distance unit guard: Valhalla OSRM-format may expose meters even with kilometre costing units.
    old_bumps,old_alerts=server.osm_bumps_for_route,server.route_alerts
    server.osm_bumps_for_route=lambda coords:([],'test');server.route_alerts=lambda coords:[]
    coords=[[-46.407,-24.012],[-46.316,-23.960]]
    ck(5000<server._finish_route({'distance':11000,'duration':1800},coords,[],'Valhalla demo 1')['distance_m']<30000,'distância Valhalla em metros')
    ck(5000<server._finish_route({'distance':11,'duration':1800},coords,[],'Valhalla demo 1')['distance_m']<30000,'distância Valhalla em km')
    server.osm_bumps_for_route,server.route_alerts=old_bumps,old_alerts

    for f in ['app/index.html','app/app.js','app/styles.css','app/manifest.json','app/sw.js','app/boot.js','app/admin.html','app/admin.css','app/admin.js']:ck((server.ROOT/f).exists(),f)
    app=(server.ROOT/'app/app.js').read_text(encoding='utf-8');idx=(server.ROOT/'app/index.html').read_text(encoding='utf-8');boot=(server.ROOT/'app/boot.js').read_text(encoding='utf-8');sw=(server.ROOT/'app/sw.js').read_text(encoding='utf-8');srv=(server.ROOT/'server.py').read_text(encoding='utf-8')
    ck('function project(' in app and 'async function reroute(' in app,'proje??o e rec?lculo de navega??o')
    ck('id="destination"' in app and '/api/autocomplete' in app,'busca de destino conectada')
    ck('turnDistance' in idx and 'instruction' in idx,'pr?xima manobra')
    ck('/api/diagnostics' in srv and 'physical_radar_id' in srv,'backend legado preservado')
    ck('CLEAR_CACHE' in sw and 'v413' in sw and 'v=413' in idx and 'v=413' in boot,'cache versionado')
    ck('5.24.0' in boot and server.CA_BUNDLE.exists(),'runtime local e TLS')
    ck('CERT_NONE' not in srv and '_create_unverified_context' not in srv and '--insecure' not in srv,'TLS verificado')
    ck('SOURCE_REGISTRY' in srv and 'sync_antt_sp' in srv and '/api/admin/login' in srv and '/api/admin/dashboard' in srv,'Admin Engine + fontes estaduais'); admin=(server.ROOT/'app/admin.html').read_text(encoding='utf-8'); ck('Relas Command' in admin and 'Alimentar base' in admin and 'Varredura' in admin and 'Semáforos' in admin and 'Atualizar cidade' in admin,'painel Relas operacional'); ck('ensure_v18_tables' in srv and 'operation_logs' in srv and 'update_queue' in srv and 'apply_update_decisions' in srv and 'queue_state_updates' in srv,'observabilidade + fila de atualização'); ck('discover_city_intelligence' in srv and 'start_city_batch_v17' in srv and 'start_target_city_discovery' in srv,'varredura discovery-only + atualização por cidade'); ck('sync_osm_objects_city' in srv and 'road_objects' in srv and 'signal_networks' in srv,'State Intelligence backend'); ck('_manual_radar' in srv and '_manual_signal' in srv and 'start_target_city_discovery' in srv,'alimentação manual + atualização por cidade'); ck('relas-icons' in app and 'data-layer' in app and 'clusterProperties' in app,'SVG layers and clusters'); ck(hasattr(server,'CITY_BATCH_LOCK'),'CITY_BATCH_LOCK definido');ck(hasattr(server,'_overpass_request') and len(server.OVERPASS_ENDPOINTS)>=2,'Overpass POST com fallback');ck(hasattr(server,'discover_official_signals_city') and hasattr(server,'_sync_official_signal_wfs'),'conectores WFS oficiais de semáforos');ck('geosampa_signals' in Path('server.py').read_text(encoding='utf-8') and 'santos_signals_wfs' in Path('server.py').read_text(encoding='utf-8'),'GeoSampa e SIGSantos registrados');
    print('SELFTEST OK: Relas v1.8.2 + batch lock + Overpass fallback + WFS oficial de semáforos + fila + Navigation Core')
if __name__=='__main__':main()
