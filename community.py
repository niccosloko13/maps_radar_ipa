"""Local SP ingestion and indexed map read model. Original inventory is never modified."""
import csv, hashlib, json, math, time
from functools import lru_cache
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
TYPES={1:'fixed',2:'signal_radar',3:'red_light',5:'mobile',7:'police',8:'bump',14:'toll'}
LABELS={'fixed':'Radar fixo','signal_radar':'Radar + avanço de sinal','red_light':'Câmera de avanço','mobile':'Fiscalização reportada','police':'Fiscalização','bump':'Lombada','toll':'Pedágio','signal':'Semáforo','other':'Objeto viário'}
def now():return datetime.now(timezone.utc).isoformat()
# Observational reports are short-lived; fixed infrastructure needs separate review.
REPORT_TTL_SECONDS={'mobile':1200,'police':1200,'accident':3600,'stopped':1200,'obstacle':1800,'flood':3600,'closure':7200,'works':7200,'congestion':1800,'animal':1200,'pothole':7200,'broken_signal':3600,'fixed':3600,'bump':3600,'other':1800}
def report_ttl(kind):return REPORT_TTL_SECONDS.get(kind,1800)

@contextmanager
def transaction(s):
 """SQLite's connection context commits but does not close: release viewport handles."""
 connection=s.db()
 try:
  with connection:yield connection
 finally:connection.close()

def init(s):
 if __import__('db').backend()=='sqlite':
  from db.sqlite_schema import initialize_community
  return initialize_community(s)
class Municipalities:
 def __init__(self,root):
  names={str(x['id']):x['nome'] for x in json.loads((root/'data/sp-municipality-names.json').read_text(encoding='utf8'))};self.grid={}
  for f in json.loads((root/'data/sp-municipalities.geojson').read_text(encoding='utf8'))['features']:
   g=f['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
   for rings in polys:
    xs=[p[0] for p in rings[0]];ys=[p[1] for p in rings[0]];box=(min(xs),min(ys),max(xs),max(ys));entry=(box,rings,names[f['properties']['codarea']])
    for x in range(math.floor(box[0]*10),math.floor(box[2]*10)+1):
     for y in range(math.floor(box[1]*10),math.floor(box[3]*10)+1):self.grid.setdefault((x,y),[]).append(entry)
 @staticmethod
 def ring(x,y,r):
  inside=False
  for a,b in zip(r,r[1:]+r[:1]):
   if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
  return inside
 def city(self,x,y):
  for b,r,n in self.grid.get((math.floor(x*10),math.floor(y*10)),[]):
   if b[0]<=x<=b[2] and b[1]<=y<=b[3] and self.ring(x,y,r[0]) and not any(self.ring(x,y,h) for h in r[1:]):return n
  return None
@lru_cache(maxsize=2)
def boundaries(root):return Municipalities(Path(root))
def dist(a,b):return math.hypot((a[0]-b[0])*111320*math.cos(math.radians(a[1])),(a[1]-b[1])*110540)
def legacy(s,bbox=None):
 with transaction(s) as c:
  out=[]
  for table in ['radars','road_objects']:
   for row in c.execute("SELECT * FROM "+table+" WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND status NOT IN ('inactive','removed','hidden','retired')"+(' AND longitude BETWEEN ? AND ? AND latitude BETWEEN ? AND ?' if bbox else ''),[bbox[0],bbox[2],bbox[1],bbox[3]] if bbox else []):
    r=dict(row);v=r.get('radar_type',r.get('object_type',''));kind={'radar_semaforo':'signal_radar','lombada_eletronica':'bump','traffic_signal':'signal','physical_bump':'bump'}.get(v,'fixed' if table=='radars' else 'other')
    official=(table=='radars' and not any(x in r['source'].lower() for x in ['osm','community'])) or r.get('official')==1
    r.update(kind=kind,trust='official' if official else 'community',source_type='official' if official else 'community',hidden=0);out.append(r)
 return out
def s_direction(v):
 try:return float(v)%360
 except (TypeError,ValueError):return {'norte':0,'leste':90,'sul':180,'oeste':270}.get(str(v or '').lower())
def reconcile(c,r,official):
 candidates=[o for o in official if o['kind']==r['kind'] and abs(o['longitude']-r['longitude'])<.001 and abs(o['latitude']-r['latitude'])<.001 and dist((r['longitude'],r['latitude']),(o['longitude'],o['latitude']))<=45]
 candidates=[o for o in candidates if not(r.get('direction_type')==1 and s_direction(o.get('direction')) is not None and not direction_matches(r,s_direction(o.get('direction'))))]
 if candidates:
  o=min(candidates,key=lambda o:dist((r['longitude'],r['latitude']),(o['longitude'],o['latitude'])))
  conflict=bool(o.get('speed_limit') and r.get('speed_limit') and o['speed_limit']!=r['speed_limit'])
  return ('conflict' if conflict else 'confirmed'),o['id']
 near=c.execute('SELECT id,direction,speed_limit,imported_at,longitude,latitude FROM map_points WHERE kind=? AND longitude BETWEEN ? AND ? AND latitude BETWEEN ? AND ? AND source_type="community" AND id!=?',(r['kind'],r['longitude']-.00018,r['longitude']+.00018,r['latitude']-.00018,r['latitude']+.00018,r['id'])).fetchall()
 for o in near:
  if (o['imported_at'] or '',o['id']) >= (r.get('imported_at') or now(),r['id']):continue
  if dist((r['longitude'],r['latitude']),(o['longitude'],o['latitude']))>20:continue
  if o['direction'] is not None and r['direction'] is not None and abs((o['direction']-r['direction']+180)%360-180)>60:continue
  return 'duplicate',o['id']
 return 'community',None
def import_file(s,path=None):
 init(s);geo=boundaries(str(s.ROOT))
 if path is None:
  matches=[]
  for p in sorted(s.ROOT.glob('*.txt')):
   if p.open(encoding='utf-8-sig').readline().strip()=='X,Y,TYPE,SPEED,DirType,Direction':matches.append(p)
  if len(matches)!=1:raise ValueError('Esperado exatamente um TXT com cabeçalho X,Y,TYPE,SPEED,DirType,Direction')
  path=matches[0]
 path=Path(path);digest=hashlib.sha256(path.read_bytes()).hexdigest();batch='community-'+digest[:20]
 official=[r for r in legacy(s) if r['trust']=='official'];stats=dict(rows=0,invalid=0,outside_sp=0,duplicates=0,imported=0,by_type={},by_municipality={},reconciled=0,conflicts=0)
 with transaction(s) as c:
  previous=c.execute('SELECT summary_json FROM community_batches WHERE batch_id=?',(batch,)).fetchone()
  if previous:return dict(json.loads(previous[0]),cached=True)
  with path.open(encoding='utf-8-sig',newline='') as stream:
   reader=csv.DictReader(stream)
   if reader.fieldnames!=['X','Y','TYPE','SPEED','DirType','Direction']:raise ValueError('Cabeçalho inválido')
   for raw in reader:
    stats['rows']+=1
    try:
     x,y=float(raw['X']),float(raw['Y']);typ=int(raw['TYPE']);sp=int(raw['SPEED']);dt=int(raw['DirType']);dr=float(raw['Direction'])
     if not all(map(math.isfinite,[x,y,dr])) or not(-180<=x<=180 and -90<=y<=90 and 0<=sp<=200 and 0<=dr<=360 and dt in [0,1,2]) or typ not in TYPES:raise ValueError()
    except (ValueError,TypeError):stats['invalid']+=1;continue
    city=geo.city(x,y)
    if not city:stats['outside_sp']+=1;continue
    rid='community-'+hashlib.sha256(f'{x:.6f},{y:.6f},{typ},{sp},{dt},{dr}'.encode()).hexdigest()[:24]
    if c.execute('SELECT 1 FROM map_points WHERE id=?',(rid,)).fetchone():stats['duplicates']+=1;continue
    r=dict(id=rid,longitude=x,latitude=y,kind=TYPES[typ],speed_limit=sp or None,direction=dr,direction_type=dt,original_type=typ,source='community_speedcam',source_type='community',ingested_by='local_import',imported_at=now(),batch_id=batch,municipality=city,updated_at=now(),raw_json=json.dumps(raw))
    r['trust'],r['linked_id']=reconcile(c,r,official)
    c.execute('INSERT INTO map_points('+','.join(r)+') VALUES('+','.join('?' for _ in r)+')',list(r.values()))
    stats['imported']+=1;stats['by_type'][str(typ)]=stats['by_type'].get(str(typ),0)+1;stats['by_municipality'][city]=stats['by_municipality'].get(city,0)+1
    stats['reconciled']+=r['trust']=='confirmed';stats['conflicts']+=r['trust']=='conflict';stats['duplicates']+=r['trust']=='duplicate'
  stats.update(batch_id=batch,sha256=digest,filename=path.name)
  c.execute('INSERT INTO community_batches VALUES(?,?,?,?,?)',(batch,now(),path.name,digest,json.dumps(stats,ensure_ascii=False)))
 return stats
def features(s,q,admin=False):
 watermark=now()
 bbox=[float(x) for x in q.get('bbox',['-53.2,-25.4,-44,-19.7'])[0].split(',')]
 if len(bbox)!=4 or not all(map(math.isfinite,bbox)) or not(-180<=bbox[0]<bbox[2]<=180 and -90<=bbox[1]<bbox[3]<=90):raise ValueError('bbox inválido')
 types=q.get('types',[''])[0].split(',');where=['longitude BETWEEN ? AND ?','latitude BETWEEN ? AND ?'];args=[bbox[0],bbox[2],bbox[1],bbox[3]]
 if not admin:where+=['hidden=0',"trust!='duplicate'",'(expires_at IS NULL OR expires_at>?)'];args.append(time.time())
 for key in ['municipality','kind','speed_limit','source','trust']:
  if q.get(key,[''])[0]:where.append(key+'=?');args.append(q[key][0])
 if q.get('direction',[''])[0]=='1':where.append('direction_type IN (1,2)')
 if q.get('since',[''])[0]:where.append('updated_at>=?');args.append(q['since'][0])
 if types!=['']:where.append('kind IN ('+','.join('?' for _ in types)+')');args+=types
 with transaction(s) as c:rows=[dict(r) for r in c.execute('SELECT * FROM map_points WHERE '+' AND '.join(where)+' ORDER BY updated_at DESC LIMIT 25000',args)]
 if not admin:
  for r in legacy(s,bbox):
   if bbox[0]<=r['longitude']<=bbox[2] and bbox[1]<=r['latitude']<=bbox[3] and (types==[''] or r['kind'] in types):rows.append(r)
  linked={r['linked_id'] for r in rows if r.get('linked_id') and r['trust']=='confirmed'}
  for r in rows:
   if r['id'] in linked:r['trust']='confirmed'
  rows=[r for r in rows if not(r.get('linked_id') and r['trust']=='confirmed')]
 removed=[]
 if not admin:
  with transaction(s) as c:removed=[r[0] for r in c.execute("SELECT id FROM map_points WHERE longitude BETWEEN ? AND ? AND latitude BETWEEN ? AND ? AND (hidden=1 OR trust='duplicate' OR (trust='confirmed' AND linked_id IS NOT NULL) OR expires_at<=?)",[bbox[0],bbox[2],bbox[1],bbox[3],time.time()])]
 return {'type':'FeatureCollection','removed_ids':removed,'features':[{'type':'Feature','geometry':{'type':'Point','coordinates':[r['longitude'],r['latitude']]},'properties':{k:v for k,v in r.items() if k not in ['raw_json','current_hash']}} for r in rows],'updated_at':watermark}
def summary(s,q):
 fc=features(s,q,True);rows=[f['properties'] for f in fc['features']];cities={};counts={};trust={}
 for r in rows:
  city=cities.setdefault(r['municipality'],{});city[r['kind']]=city.get(r['kind'],0)+1;counts[r['kind']]=counts.get(r['kind'],0)+1;trust[r['trust']]=trust.get(r['trust'],0)+1
 with transaction(s) as c:batches=[dict(r) for r in c.execute('SELECT * FROM community_batches')]
 return dict(total=len(rows),by_type=counts,by_municipality=cities,trust=trust,batches=batches,items=rows[:500],truncated=len(rows)>500)
def direction_matches(r,bearing,tolerance=55):
 if r.get('direction_type') not in [1,2] or r.get('direction') is None:return True
 delta=abs((float(r['direction'])-bearing+180)%360-180)
 return delta<=tolerance or (r['direction_type']==2 and abs(delta-180)<=tolerance)
def route_points(s,coords,tolerance=55):
 if len(coords)<2 or len(coords)>20000:raise ValueError('Rota inválida')
 xs=[p[0] for p in coords];ys=[p[1] for p in coords];bbox=f'{min(xs)-.001},{min(ys)-.001},{max(xs)+.001},{max(ys)+.001}'
 rows=features(s,{'bbox':[bbox]})['features'];segments=[];cum=0
 for a,b in zip(coords,coords[1:]):
  length=dist(a,b);segments.append((a,b,cum,length));cum+=length
 grid={}
 for segment_index,seg in enumerate(segments):
  a,b,_,_=seg
  for x in range(math.floor((min(a[0],b[0])-.0007)*100),math.floor((max(a[0],b[0])+.0007)*100)+1):
   for y in range(math.floor((min(a[1],b[1])-.0007)*100),math.floor((max(a[1],b[1])+.0007)*100)+1):grid.setdefault((x,y),[]).append((*seg,segment_index))
 out=[]
 for f in rows:
  r=f['properties'];pt=f['geometry']['coordinates'];best=None
  if r.get('direction_type') is None and r.get('direction') is not None:
   hd=s._direction_bearing(r['direction'])
   if hd is not None:r=dict(r,direction=hd,direction_type=1)
  for a,b,start,length,segment_index in grid.get((math.floor(pt[0]*100),math.floor(pt[1]*100)),[]):
   if not(min(a[0],b[0])-.0007<=pt[0]<=max(a[0],b[0])+.0007 and min(a[1],b[1])-.0007<=pt[1]<=max(a[1],b[1])+.0007):continue
   d,t=s.point_seg_distance_m(pt,a,b)
   if d<=35 and direction_matches(r,s.bearing_deg(a,b),tolerance) and (best is None or d<best[0]):best=(d,start+t*length,segment_index,s.bearing_deg(a,b))
  if best:out.append(dict(r,along_m=round(best[1]),distance_from_route_m=round(best[0],2),segment_index=best[2],road_bearing=best[3],route_evidence='geometry_corridor',title=r.get('name') if r.get('source')=='public_report' else LABELS.get(r['kind'],'Alerta'),type=r['kind']))
 return sorted(out,key=lambda r:r['along_m'])
def post(s,handler,path,data):
 if path=='/api/map/route-alerts':return {'alerts':route_points(s,data.get('coordinates',[]),max(10,min(90,float(data.get('tolerance',55)))))}
 if path=='/api/map/report':
  kind=data.get('kind');allowed=['animal','closure','mobile','police','accident','stopped','obstacle','works','congestion','flood','pothole','broken_signal','fixed','bump','other']
  if kind not in allowed:raise ValueError('Tipo inválido')
  x,y=float(data['longitude']),float(data['latitude'])
  if not math.isfinite(x+y):raise ValueError('Coordenada inválida')
  city=boundaries(str(s.ROOT)).city(x,y)
  if not city:raise ValueError('Reporte disponível somente em SP')
  stamp=now();rid='report-'+hashlib.sha256(f'{handler.client_address[0]}:{x:.4f}:{y:.4f}:{kind}:{int(time.time()/300)}'.encode()).hexdigest()[:24]
  with transaction(s) as c:c.execute('INSERT INTO map_points(id,longitude,latitude,kind,source,source_type,ingested_by,imported_at,municipality,trust,updated_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',(rid,x,y,kind if kind in LABELS else 'other','public_report','recent','public_report',stamp,city,'recent',stamp,time.time()+report_ttl(kind)))
  with transaction(s) as c:c.execute('UPDATE map_points SET name=?,report_kind=?,raw_json=? WHERE id=?',(kind,kind,json.dumps(data),rid))
  return {'ok':True,'id':rid}
 if path=='/api/map/feedback':
  if data.get('action') not in ['confirm','problem','removed','incorrect']:raise ValueError('Ação inválida')
  with transaction(s) as c:c.execute('INSERT INTO map_feedback(point_id,action,created_at) VALUES(?,?,?)',(str(data.get('id',''))[:100],data['action'],now()))
  return {'ok':True,'message':'Contribuição recebida para revisão'}
 if path=='/api/admin/community/import':return import_file(s)
 if path=='/api/admin/community/bulk':
  ids=data.get('ids',[]);action=data.get('action');actions={'approve':"hidden=0",'hide':'hidden=1','conflict':"trust='conflict'"}
  if not ids or len(ids)>1000 or action not in [*actions,'reconcile']:raise ValueError('Seleção/ação inválida')
  with transaction(s) as c:
   if action=='reconcile':
    official=[r for r in legacy(s) if r['trust']=='official']
    for rid in ids:
     row=c.execute('SELECT * FROM map_points WHERE id=?',(rid,)).fetchone()
     if row:
      trust,link=reconcile(c,dict(row),official);c.execute('UPDATE map_points SET trust=?,linked_id=?,updated_at=? WHERE id=?',(trust,link,now(),rid))
   else:c.execute('UPDATE map_points SET '+actions[action]+',updated_at=? WHERE id IN ('+','.join('?' for _ in ids)+')',[now(),*ids])
   c.execute('INSERT INTO map_audit(created_at,action,ids_json) VALUES(?,?,?)',(now(),action,json.dumps(ids)))
  return {'ok':True,'selected':len(ids)}
 raise ValueError('Endpoint desconhecido')


def bootstrap_public_data(s):
 """Reproducible public seeds; never bundle a user's database or rewrite inventory."""
 snapshot=s.ROOT/'data/geosampa_signals_snapshot.json';imported=0
 if snapshot.exists():
  data=json.loads(snapshot.read_text(encoding='utf8'));stamp=now()
  with transaction(s) as c:
   existing={(round(r[0],7),round(r[1],7)) for r in c.execute("SELECT longitude,latitude FROM road_objects WHERE source='geosampa_signals' AND longitude IS NOT NULL AND latitude IS NOT NULL")}
   for lon,lat in data['points']:
    key=(round(lon,7),round(lat,7))
    if key in existing or not(-47.3<lon<-46 and -24.2<lat<-23.1):continue
    ext=hashlib.sha256(f'{lon:.7f},{lat:.7f}'.encode()).hexdigest()[:20]
    item=dict(id='geosampa_signals:'+ext,source='geosampa_signals',external_id=ext,object_type='traffic_signal',name=data['title'],latitude=lat,longitude=lon,municipality='São Paulo',state='SP',status='active',confidence=96,official=1,timing_mode='unknown',adaptive=0,source_url=data['source_url'],source_date=data['captured_at'],ingested_by='public_snapshot',ingestion_batch='geosampa-2026-10-24')
    s._upsert_road_object(c,item,stamp);existing.add(key);imported+=1
 result={'official_signals_inserted':imported}
 with transaction(s) as c:has_batch=c.execute('SELECT 1 FROM community_batches LIMIT 1').fetchone() is not None
 if not has_batch and (s.ROOT/'pesquisaradar.txt').exists():result['community']=import_file(s,s.ROOT/'pesquisaradar.txt')
 return result
