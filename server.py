from __future__ import annotations

import hashlib, html, io, json, math, os, re, shutil, sqlite3, sys, threading, time, urllib.parse, urllib.request, urllib.error, webbrowser, zipfile, socket, ssl, subprocess, csv, secrets
from datetime import datetime, timezone
from runtime_config import load_environment, hosted, environment
load_environment()
import db as database
import runtime_jobs
from admin_auth import AdminAuth
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT=Path(__file__).resolve().parent
APP_DIR=ROOT/'app'; BUNDLED_DATA_DIR=ROOT/'data'
def _default_user_data_dir():
    env=os.environ.get('RADAR_DATA_DIR')
    if env:return Path(env).expanduser().resolve()
    local=os.environ.get('LOCALAPPDATA')
    if local:return Path(local)/'RadarSP'/'data'
    return ROOT/'user-data'
USER_DATA_DIR=_default_user_data_dir(); DATA_DIR=USER_DATA_DIR
BUNDLED_DB_PATH=BUNDLED_DATA_DIR/'radar.db'; DB_PATH=DATA_DIR/'radar.db'
PORT=int(os.environ.get('RADAR_PORT','8815'))
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/155 Safari/537.36 Relas/1.8.2'
# A Carta de Serviços do DER aponta PesquisaRadar.aspx como o serviço de consulta.
DER_SEARCH_URL='https://www.der.sp.gov.br/WebSite/MalhaRodoviaria/PesquisaRadar.aspx'
DER_SEARCH_ALT='https://dersp.der.sp.gov.br/WebSite/MalhaRodoviaria/PesquisaRadar.aspx'
DER_LANDING='https://dersp.der.sp.gov.br/WebSite/MalhaRodoviaria/LocalizacaoRadar.aspx'
DER_NEWS='https://dersp.der.sp.gov.br/WebSite/Comunicacao/SalaImprensa.aspx'
CET_URL='https://www.cetsp.com.br/consultas/fiscalizacao-eletronica-do-transito.aspx'
SANTO_ANDRE_URL='https://portais.santoandre.sp.gov.br/observatoriomob/fiscalizacao-eletronica-de-transito-radares/'
SANTO_ANDRE_SNAPSHOT=BUNDLED_DATA_DIR/'santo_andre_official_2026.json'
INMETRO_URL='https://www.gov.br/inmetro/pt-br/acesso-a-informacao/perguntas-frequentes/metrologia-legal/medidor-de-velocidade-radar/como-saber-se-determinado-radar-esta-verificado'
DER_ROAD_KMZ_URL='https://dersp.der.sp.gov.br/WebSite/Arquivos/DadosAbertos/MalhaRodoviariaEstadual/MalhaRodoviariaEstadual/Sistema%20Rodovi%C3%A1rio%20Estadual.kmz'
ROAD_CACHE=DATA_DIR/'der_road_network.json'
VENDOR_DIR=APP_DIR/'vendor'
MAPLIBRE_JS=VENDOR_DIR/'maplibre-gl.js'
MAPLIBRE_CSS=VENDOR_DIR/'maplibre-gl.css'
# v5 usa bundle UMD autocontido: ideal para servidor local/LAN sem bundler ESM.
MAPLIBRE_VERSION='5.24.0'
MAPLIBRE_JS_URLS=[
 f'https://unpkg.com/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.js',
 f'https://cdn.jsdelivr.net/npm/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.js',
]
MAPLIBRE_CSS_URLS=[
 f'https://unpkg.com/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.css',
 f'https://cdn.jsdelivr.net/npm/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.css',
]
SOURCES=[
 {'id':'santo_andre','name':'Santo André · Oficial A','scope':'Santo André · ABC','kind':'coordenadas oficiais diretas + velocidade + registro INMETRO','url':SANTO_ANDRE_URL,'sync':True},
 {'id':'der_sp','name':'DER-SP','scope':'Rodovias estaduais não concedidas de São Paulo','kind':'consulta oficial + comunicados de ativação','url':DER_SEARCH_URL,'sync':True},
 {'id':'cet_sp','name':'CET São Paulo','scope':'São Paulo capital','kind':'fiscalização eletrônica urbana · ativo/desativado','url':CET_URL,'sync':False},
 {'id':'praia_grande','name':'Praia Grande · oficial','scope':'Baixada Santista','kind':'radares fixos + lombadas eletrônicas','url':'https://www.praiagrande.sp.gov.br/cartaservicos/Servicos/consultaCS.asp','sync':True},
 {'id':'santos','name':'CET Santos · oficial','scope':'Santos · Baixada Santista','kind':'radares ativos + velocidade + série + ID CET','url':'https://cetsantos.com.br/radares-2/','sync':True},
 {'id':'inmetro','name':'INMETRO / PSIE','scope':'Validação metrológica','kind':'aferição e situação do equipamento','url':INMETRO_URL,'sync':False},
]

AUTH=AdminAuth(USER_DATA_DIR)
ADMIN_USER=AUTH.username

CITY_SCAN_LOCK=database.WriteLock()
CITY_BATCH_LOCK=database.WriteLock()
OVERPASS_ENDPOINTS=['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter','https://overpass.private.coffee/api/interpreter']
GEOSAMPA_WFS='https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs'
SANTOS_WFS='https://egov.santos.sp.gov.br/geoserver/ows'
SBCGEO_URL='https://geo.saobernardo.sp.gov.br/'
ASSISTANT_ACTOR='ChatGPT/OpenAI'
ASSISTANT_SIGNAL_BATCH='chatgpt-openai-semaforos-baixada-sbc-2026-10-23-v1'
ASSISTANT_SIGNAL_CITIES=['Bertioga','Cubatão','Guarujá','Itanhaém','Mongaguá','Peruíbe','Praia Grande','Santos','São Vicente','São Bernardo do Campo']
ASSISTANT_OFFICIAL_SIGNAL_SEEDS=[
 {'municipality':'São Vicente','name':'Avenida Presidente Wilson x Rua Visconde do Rio Branco','source_id':'saovicente_pref_2026','source_url':'https://www.saovicente.sp.gov.br/informacao/sao-vicente-instala-semaforos-para-pedestres-na-avenida-presidente-wilson','source_date':'2026-07-20'},
 {'municipality':'São Vicente','name':'Avenida Presidente Wilson x Rua Mem de Sá','source_id':'saovicente_pref_2026','source_url':'https://www.saovicente.sp.gov.br/informacao/sao-vicente-instala-semaforos-para-pedestres-na-avenida-presidente-wilson','source_date':'2026-07-20'},
 {'municipality':'São Vicente','name':'Avenida Presidente Wilson x Largo Tomé de Souza','source_id':'saovicente_pref_2026','source_url':'https://www.saovicente.sp.gov.br/informacao/sao-vicente-instala-semaforos-para-pedestres-na-avenida-presidente-wilson','source_date':'2026-07-20'},
 {'municipality':'São Vicente','name':'Avenida Presidente Wilson x Rua Pero Corrêa','source_id':'saovicente_pref_2026','source_url':'https://www.saovicente.sp.gov.br/informacao/sao-vicente-instala-semaforos-para-pedestres-na-avenida-presidente-wilson','source_date':'2026-07-20'},
 {'municipality':'Itanhaém','name':'Avenida José Batista Campos x Rua Emídio de Souza','source_id':'itanhaem_pref_2023','source_url':'https://www2.itanhaem.sp.gov.br/2023/04/20/nao-e-radar-lombadas-eletronicas-educativas-sao-instaladas/','source_date':'2023-04-20'},
 {'municipality':'Itanhaém','name':'Avenida Jaime de Castro x Avenida Alberto Simões','source_id':'itanhaem_pref_2023','source_url':'https://www2.itanhaem.sp.gov.br/2023/04/20/nao-e-radar-lombadas-eletronicas-educativas-sao-instaladas/','source_date':'2023-04-20'},
 {'municipality':'Itanhaém','name':'Rua João Mariano Ferreira x Rua Rui Barbosa','source_id':'itanhaem_pref_2023','source_url':'https://www2.itanhaem.sp.gov.br/2023/04/20/nao-e-radar-lombadas-eletronicas-educativas-sao-instaladas/','source_date':'2023-04-20'},
]

ANTT_DATASET_ID='79d287f4-f5ca-4385-a17c-f61f53831f17'
ANTT_CKAN_API=f'https://dados.antt.gov.br/api/3/action/package_show?id={ANTT_DATASET_ID}'
ANTT_SP_URL='https://dados.antt.gov.br/dataset/radar'
IBGE_SP_MUNICIPIOS='https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios'
SOURCE_REGISTRY=[
 {'id':'der_sp','name':'DER-SP','scope':'Estado de São Paulo','coverage':'rodovias estaduais não concedidas','mode':'connector','priority':100,'url':DER_SEARCH_URL,'official':True},
 {'id':'antt_sp','name':'ANTT Dados Abertos','scope':'Estado de São Paulo','coverage':'rodovias federais concedidas','mode':'csv','priority':95,'url':ANTT_SP_URL,'official':True},
 {'id':'cet_sp','name':'CET São Paulo','scope':'São Paulo capital','coverage':'fiscalização eletrônica urbana ativa/desativada','mode':'connector-planned','priority':100,'url':CET_URL,'official':True},
 {'id':'santo_andre','name':'Prefeitura de Santo André','scope':'Santo André','coverage':'radares urbanos com coordenada oficial','mode':'snapshot','priority':100,'url':SANTO_ANDRE_URL,'official':True},
 {'id':'santos','name':'CET Santos','scope':'Santos','coverage':'radares ativos + velocidade + série','mode':'connector','priority':100,'url':'https://cetsantos.com.br/radares-2/','official':True},
 {'id':'praia_grande','name':'Prefeitura de Praia Grande','scope':'Praia Grande','coverage':'radares + lombadas eletrônicas','mode':'connector','priority':100,'url':'https://www.praiagrande.sp.gov.br/cartaservicos/Servicos/consultaCS.asp','official':True},
 {'id':'sao_caetano','name':'Prefeitura de São Caetano do Sul','scope':'São Caetano do Sul','coverage':'fiscalização eletrônica municipal','mode':'discovery','priority':85,'url':'https://www.saocaetanodosul.sp.gov.br/','official':True},
 {'id':'campinas','name':'EMDEC Campinas','scope':'Campinas','coverage':'154 pontos de fiscalização eletrônica em 2026','mode':'discovery','priority':90,'url':'https://www.emdec.com.br/radares','official':True},
 {'id':'sao_bernardo','name':'Prefeitura de São Bernardo do Campo','scope':'São Bernardo do Campo','coverage':'radares e estudos técnicos municipais','mode':'discovery','priority':92,'url':'https://www.saobernardo.sp.gov.br/radares','official':True},
 {'id':'artesp','name':'ARTESP Dados Abertos','scope':'Estado de São Paulo','coverage':'rodovias estaduais concedidas / equipamentos','mode':'discovery','priority':90,'url':'https://dadosabertos.artesp.sp.gov.br/','official':True},
 {'id':'inmetro','name':'INMETRO / PSIE','scope':'Brasil','coverage':'verificação metrológica / histórico','mode':'enrichment','priority':100,'url':INMETRO_URL,'official':True},
 {'id':'geosampa_signals','name':'GeoSampa · Cruzamentos Semaforizados','scope':'São Paulo capital','coverage':'semáforos oficiais via WFS','mode':'wfs-official','priority':100,'url':GEOSAMPA_WFS,'official':True},
 {'id':'santos_signals_wfs','name':'SIGSantos · Semáforos','scope':'Santos','coverage':'semáforos oficiais via GeoServer/WFS','mode':'wfs-official','priority':100,'url':SANTOS_WFS,'official':True},
 {'id':'sbcgeo','name':'SBCGEO · São Bernardo do Campo','scope':'São Bernardo do Campo','coverage':'dados geoespaciais municipais públicos; semáforos complementados por OSM enquanto camada específica é validada','mode':'official-geoportal','priority':96,'url':SBCGEO_URL,'official':True},
 {'id':'saovicente_pref_2026','name':'Prefeitura de São Vicente · semáforos de pedestres 2026','scope':'São Vicente','coverage':'cruzamentos publicados pela SEMOB em julho de 2026','mode':'official-address-seed','priority':95,'url':'https://www.saovicente.sp.gov.br/informacao/sao-vicente-instala-semaforos-para-pedestres-na-avenida-presidente-wilson','official':True},
 {'id':'itanhaem_pref_2023','name':'Prefeitura de Itanhaém · sinalização semafórica','scope':'Itanhaém','coverage':'cruzamentos semaforizados publicados pela Prefeitura','mode':'official-address-seed','priority':90,'url':'https://www2.itanhaem.sp.gov.br/2023/04/20/nao-e-radar-lombadas-eletronicas-educativas-sao-instaladas/','official':True},
 {'id':'osm_road_objects','name':'OpenStreetMap · objetos viários','scope':'Municípios de São Paulo','coverage':'semáforos, lombadas físicas e câmeras como camada comunitária de descoberta','mode':'community-discovery','priority':55,'url':'https://www.openstreetmap.org/','official':False},
 {'id':'artesp_ccm','name':'ARTESP CCM','scope':'Rodovias concedidas do Estado de São Paulo','coverage':'ocorrências, intervenções e tempos de percurso em tempo real','mode':'live-enrichment','priority':90,'url':'https://ccm.artesp.sp.gov.br/','official':True},
 {'id':'antt_volume_radar','name':'ANTT · volume por radar','scope':'Rodovias federais concedidas em SP','coverage':'volume, sentido, velocidade e tipo de veículo por radar','mode':'traffic-enrichment','priority':88,'url':'https://dados.antt.gov.br/dataset/volume-radar','official':True},
]
# Páginas oficiais já verificadas na pesquisa. Usadas apenas como fallback de inventário;
# a busca principal continua sendo a consulta de radares, que pode trazer coordenadas exatas.
DER_BULLETIN_IDS=[1913,1909,1903,1927,1944,1886,1878,1895,1876,1865]
LOCK=threading.Lock()
DB_WRITE_LOCK=database.WriteLock()
DEPENDENCY_STATE={'valhalla':{'status':'unknown','last_ok':None,'last_error':None},'osrm':{'status':'unknown','last_ok':None,'last_error':None},'geocode':{'status':'unknown','last_ok':None,'last_error':None},'overpass':{'status':'unknown','last_ok':None,'last_error':None}}
CA_BUNDLE=ROOT/'certs'/'cacert.pem'
CURL_BIN=shutil.which('curl.exe') or shutil.which('curl')

def _ssl_context():
    try:
        if CA_BUNDLE.exists():
            return ssl.create_default_context(cafile=str(CA_BUNDLE))
    except Exception:
        pass
    return ssl.create_default_context()

def _curl_request(url,data=None,headers=None,timeout=35,method=None):
    if not CURL_BIN:
        raise RuntimeError('curl não disponível para fallback TLS')
    marker='__RADAR_HTTP_STATUS__:'
    final_marker='__RADAR_FINAL_URL__:'
    cmd=[CURL_BIN,'-L','--silent','--show-error','--fail','--connect-timeout','8','--max-time',str(int(timeout))]
    for k,v in (headers or {}).items():
        cmd += ['-H',f'{k}: {v}']
    if method:
        cmd += ['-X',method]
    if data is not None:
        cmd += ['--data-binary','@-']
    cmd += ['-w',f'\n{marker}%{{http_code}}\n{final_marker}%{{url_effective}}',url]
    r=subprocess.run(cmd,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout+5)
    if r.returncode!=0:
        raise RuntimeError('curl: '+r.stderr.decode('utf-8','replace').strip())
    out=r.stdout
    pos=out.rfind(('\n'+marker).encode())
    if pos<0:
        return out,200,url,'utf-8'
    body=out[:pos]
    tail=out[pos+1:].decode('utf-8','replace')
    status=200;final=url
    for line in tail.splitlines():
        if line.startswith(marker):
            try:status=int(line[len(marker):])
            except:pass
        elif line.startswith(final_marker):final=line[len(final_marker):]
    return body,status,final,'utf-8'

def http_request(url,data=None,headers=None,timeout=35,method=None,attempts=2):
    runtime_jobs.check()
    if hosted():timeout=min(timeout,8);attempts=1
    h=dict(headers or {})
    last=None
    for attempt in range(max(1,attempts)):
        try:
            runtime_jobs.check()
            if runtime_jobs.deadline.get():timeout=max(.1,min(timeout,runtime_jobs.deadline.get()-time.time()))
            req=urllib.request.Request(url,data=data,headers=h,method=method)
            with urllib.request.urlopen(req,timeout=timeout,context=_ssl_context()) as r:
                return r.read(),int(r.status),r.geturl(),r.headers.get_content_charset() or 'utf-8'
        except Exception as e:
            last=e
            msg=f'{type(e).__name__}: {e}'.lower()
            cert_error=isinstance(e,ssl.SSLCertVerificationError) or 'certificate_verify_failed' in msg or 'certificate verify failed' in msg
            # On Windows, Python's OpenSSL trust store can differ from Windows' trust store.
            # curl.exe uses Schannel there, so only certificate-validation failures use this fallback.
            if cert_error:
                try:
                    return _curl_request(url,data=data,headers=h,timeout=timeout,method=method)
                except Exception as ce:
                    last=RuntimeError(f'python_tls={type(e).__name__}: {e}; curl_tls={type(ce).__name__}: {ce}')
            if attempt+1<attempts:time.sleep(min(2.5,.5*(2**attempt)))
    raise last

BAIXADA_SYNC={'running':False,'started_at':None,'finished_at':None,'message':'Aguardando','praia_grande':None,'santos':None,'error':None}
SYNC={'running':False,'started_at':None,'finished_at':None,'message':'Pronto','roads_done':0,'roads_total':0,'records':0,'mapped':0,'derived':0,'error':None,'mode':None}

def now(): return datetime.now(timezone.utc).isoformat()
def lan_ip():
 try:
  s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('8.8.8.8',80));ip=s.getsockname()[0];s.close();return ip
 except Exception:return '127.0.0.1'

def ensure_user_data():
 DATA_DIR.mkdir(parents=True,exist_ok=True)
 # One-time migration from legacy portable versions. New ZIPs intentionally do not ship radar.db.
 if not DB_PATH.exists() and BUNDLED_DB_PATH.exists():
  shutil.copy2(BUNDLED_DB_PATH,DB_PATH)
 for name in ('der_road_network.json','geocode_cache.json','bumps_cache.json'):
  src=BUNDLED_DATA_DIR/name; dst=DATA_DIR/name
  if not dst.exists() and src.exists():
   try:shutil.copy2(src,dst)
   except:pass
 # SQLite owns -wal/-shm lifecycle. Never stat/unlink these files while the server is live:
 # they can legitimately disappear between exists() and stat() under concurrent requests.

def db():
 runtime_jobs.check()
 if database.backend()=='sqlite':ensure_user_data()
 return database.connect(DB_PATH)


def checkpoint_db():
 if database.backend()=='postgres':return True
 try:
  c=db(); database.checkpoint(c); c.commit(); c.close(); return True
 except Exception:return False

def init_db():
 if database.backend()=='sqlite':
  from db.sqlite_schema import initialize
  return initialize(sys.modules[__name__])

def fetch(url,data=None,timeout=35,attempts=3):
 h={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,*/*;q=0.8','Accept-Language':'pt-BR,pt;q=0.9','Cache-Control':'no-cache'}
 if data is not None:h['Content-Type']='application/x-www-form-urlencoded'
 return http_request(url,data=data,headers=h,timeout=timeout,method='POST' if data is not None else 'GET',attempts=attempts)



def ensure_vendor_asset(path, urls):
 if hosted():return {'ok':path.exists(),'bundled':True,'bytes':path.stat().st_size if path.exists() else 0}
 VENDOR_DIR.mkdir(parents=True,exist_ok=True)
 if path.exists() and path.stat().st_size>5000:return {'ok':True,'cached':True,'path':str(path),'bytes':path.stat().st_size}
 errs=[]
 for url in urls:
  try:
   raw,status,final,enc=fetch(url,timeout=25)
   if status==200 and len(raw)>5000:
    path.write_bytes(raw);return {'ok':True,'cached':False,'url':final,'path':str(path),'bytes':len(raw)}
   errs.append(f'{url} -> HTTP {status}, {len(raw)} bytes')
  except Exception as e:errs.append(f'{url} -> {type(e).__name__}: {e}')
 return {'ok':False,'errors':errs,'path':str(path)}

def ensure_maplibre_assets():
 return {'js':ensure_vendor_asset(MAPLIBRE_JS,MAPLIBRE_JS_URLS),'css':ensure_vendor_asset(MAPLIBRE_CSS,MAPLIBRE_CSS_URLS)}

def dec(raw,enc):
 for e in (enc,'utf-8','cp1252','latin-1'):
  try:return raw.decode(e)
  except:pass
 return raw.decode('utf-8','replace')

def clean(s):return re.sub(r'\s+',' ',html.unescape(str(s or ''))).strip()
def nk(s):
 import unicodedata
 x=unicodedata.normalize('NFKD',clean(s)).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]+',' ',x).strip()
def fnum(v):
 s=clean(v).replace('−','-').replace(' ','')
 m=re.search(r'-?\d{1,3}(?:[\.,]\d+)',s)
 if not m:return None
 try:return float(m.group().replace(',','.'))
 except:return None
def speed(v):
 nums=[int(x) for x in re.findall(r'(?<!\d)(\d{2,3})(?!\d)',clean(v))]
 return nums[0] if nums else None

def sha(o):return hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()[:24]
def upsert(c,item,seen):
 rid=item['id']; raw=json.dumps(item,ensure_ascii=False,sort_keys=True); vh=sha(item); old=c.execute('SELECT current_hash FROM radars WHERE id=?',(rid,)).fetchone()
 cols=['source','external_id','name','latitude','longitude','speed_limit','speed_text','direction','status','confidence','municipality','state','road','km','radar_type','der_number','serial_number','schedule','study_url','source_url','source_date','position_quality','inmetro_registration','lanes','local_code','quality_grade']; vals=[item.get(k) for k in cols]
 if old is None:
  c.execute('INSERT INTO radars(id,'+','.join(cols)+',first_seen,last_seen,current_hash,raw_json) VALUES('+','.join(['?']*(1+len(cols)+4))+')',[rid]+vals+[seen,seen,vh,raw]); c.execute('INSERT INTO radar_history(radar_id,source,version_hash,captured_at,raw_json) VALUES(?,?,?,?,?)',(rid,item['source'],vh,seen,raw)); return 'imported'
 if old['current_hash']!=vh:
  c.execute('UPDATE radar_history SET valid_to=? WHERE radar_id=? AND valid_to IS NULL',(seen,rid)); c.execute('INSERT INTO radar_history(radar_id,source,version_hash,captured_at,raw_json) VALUES(?,?,?,?,?)',(rid,item['source'],vh,seen,raw)); c.execute('UPDATE radars SET '+','.join(k+'=?' for k in cols)+',last_seen=?,current_hash=?,raw_json=? WHERE id=?',vals+[seen,vh,raw,rid]); return 'updated'
 c.execute('UPDATE radars SET last_seen=? WHERE id=?',(seen,rid)); return 'unchanged'

class P(HTMLParser):
 def __init__(self):
  super().__init__(); self.hidden={}; self.selects=[]; self.sel=None; self.opt=None; self.ot=[]; self.submits=[]; self.tables=[]; self.tbl=None; self.row=None; self.cell=None; self.ct=[]; self.links=[]; self.text=[]
 def handle_starttag(self,t,a):
  d=dict(a); t=t.lower()
  if t=='input':
   typ=(d.get('type') or '').lower(); n=d.get('name'); v=d.get('value','')
   if typ=='hidden' and n:self.hidden[n]=v
   if typ in ('submit','button') and n:self.submits.append((n,v))
  elif t=='select':self.sel={'name':d.get('name'),'id':d.get('id'),'options':[]};self.selects.append(self.sel)
  elif t=='option' and self.sel is not None:self.opt={'value':d.get('value',''),'text':''};self.ot=[]
  elif t=='table':self.tbl=[];self.tables.append(self.tbl)
  elif t=='tr' and self.tbl is not None:self.row=[];self.tbl.append(self.row)
  elif t in ('td','th') and self.row is not None:self.cell={'text':'','links':[]};self.ct=[];self.links=[]
  elif t=='a' and self.cell is not None and d.get('href'):self.links.append(d['href'])
 def handle_data(self,d):
  self.text.append(d)
  if self.opt is not None:self.ot.append(d)
  if self.cell is not None:self.ct.append(d)
 def handle_endtag(self,t):
  t=t.lower()
  if t=='option' and self.opt is not None:self.opt['text']=clean(' '.join(self.ot));self.sel['options'].append(self.opt);self.opt=None
  elif t in ('td','th') and self.cell is not None:self.cell['text']=clean(' '.join(self.ct));self.cell['links']=list(self.links);self.row.append(self.cell);self.cell=None
  elif t=='tr':self.row=None
  elif t=='table':self.tbl=None
  elif t=='select':self.sel=None

def parse(txt):p=P();p.feed(txt);return p
def road_select(p):
 best=None;bn=0
 for s in p.selects:
  n=sum(bool(re.search(r'\b(?:SP|SPA|SPI)\s*[- ]?\d{2,3}',o['text'],re.I)) for o in s['options'])
  if n>bn:best=s;bn=n
 return best

def _ix(heads,*terms):
 for term in terms:
  nt=nk(term)
  for i,h in enumerate(heads):
   if nt==h or nt in h:return i
 return None

def parse_radars(p,base,hint=''):
 out=[]
 for tbl in p.tables:
  rows=[r for r in tbl if r]
  if len(rows)<2:continue
  # Locate a header row instead of assuming first row is the header.
  hi=None
  for j,r in enumerate(rows[:8]):
   h=[nk(c['text']) for c in r]; joined=' | '.join(h)
   if ('latitude' in joined and 'longitude' in joined) or ('rodovia' in joined and ('velocidade' in joined or 'operacao' in joined)):
    hi=j;break
  if hi is None:continue
  heads=[nk(c['text']) for c in rows[hi]]
  ix={'sp':_ix(heads,'sp','numero sp'),'road':_ix(heads,'rodovia','nome rodovia'),'km':_ix(heads,'km inicial','quilometragem','km'),'dir':_ix(heads,'sentido'),'lat':_ix(heads,'latitude','lat'),'lon':_ix(heads,'longitude','long'),'type':_ix(heads,'tipo radar','tipo'),'der':_ix(heads,'numero der','n der','numero'),'serial':_ix(heads,'serie','serial'),'speed':_ix(heads,'velocidade regulamentada','velocidade'),'time':_ix(heads,'horario'),'status':_ix(heads,'em operacao','situacao','status'),'study':_ix(heads,'estudos','estudo tecnico'),'mun':_ix(heads,'municipio','cidade')}
  for r in rows[hi+1:]:
   vals=[c['text'] for c in r]
   def v(k):
    i=ix[k]; return vals[i] if i is not None and i<len(vals) else ''
   lat=fnum(v('lat'));lon=fnum(v('lon'));code=clean(v('sp')) or hint;km=clean(v('km'));direction=clean(v('dir'));typ=clean(v('type'));der=clean(v('der'))
   # Reject coordinate pairs outside SP/Brazil-ish bounds. This catches table numbers mistaken for lat/lon.
   if lat is not None and not (-25.5 <= lat <= -19.0): lat=None
   if lon is not None and not (-54.5 <= lon <= -44.0): lon=None
   if not any([lat,lon,code,km,der]):continue
   external=der or f'{code}:{km}:{direction}:{typ}:{lat}:{lon}'; rid='der_sp:'+hashlib.sha1(external.encode()).hexdigest()[:18]
   si=ix['study']; study=''
   if si is not None and si<len(r) and r[si]['links']:study=urllib.parse.urljoin(base,r[si]['links'][0])
   stat=nk(v('status')); status='inactive' if any(x in stat for x in ['inativo','desativado','nao','fora de operacao']) else 'active'; spd=clean(v('speed')); rname=clean(v('road')) or code or 'Rodovia estadual'
   out.append({'id':rid,'source':'der_sp','external_id':external,'name':f'{code+" · " if code else ""}{rname}{" · km "+km if km else ""}','latitude':lat,'longitude':lon,'speed_limit':speed(spd),'speed_text':spd or None,'direction':direction or None,'status':status,'confidence':99 if lat is not None and lon is not None else 93,'municipality':clean(v('mun')) or None,'state':'SP','road':code or rname,'km':km or None,'radar_type':typ or None,'der_number':der or None,'serial_number':clean(v('serial')) or None,'schedule':clean(v('time')) or None,'study_url':study or None,'source_url':base,'source_date':None,'position_quality':'exact_official' if lat is not None and lon is not None else 'unmapped_official'})
 return out

def discover_search():
 errs=[]
 for u in (DER_SEARCH_URL,DER_SEARCH_ALT):
  try:
   raw,st,final,enc=fetch(u);txt=dec(raw,enc);p=parse(txt);sel=road_select(p);direct=parse_radars(p,final)
   # A 200 landing/error page is not a valid search page. Require useful controls/table/content.
   useful=bool(sel or direct or re.search(r'Pesquisa\s+de\s+Radares|Locais\s+Fiscalizados',txt,re.I))
   if useful:return {'url':final,'status':st,'html':txt,'parser':p,'select':sel,'direct':direct}
   errs.append(f'{u}: HTTP {st}, página sem estrutura de pesquisa')
  except Exception as e:errs.append(f'{u}: {type(e).__name__}: {e}')
 raise RuntimeError(' | '.join(errs))

def options(sel,mode='sample',road=''):
 if not sel:return []
 out=[]
 for o in sel['options']:
  m=re.search(r'\b(?:SP|SPA|SPI)\s*[- ]?(\d{2,3})',o['text'],re.I)
  if m:out.append((o['value'],f'SP {int(m.group(1)):03d}'))
 seen=set();out=[x for x in out if not (x[0] in seen or seen.add(x[0]))]
 if road:
  n=int(re.sub(r'\D','',road) or 0);return [x for x in out if int(re.sub(r'\D','',x[1]) or 0)==n]
 if mode=='sample':
  wanted={31,55,70,75,148,160,270,280,300,310,330,348};return [x for x in out if int(re.sub(r'\D','',x[1])) in wanted][:12]
 return out

def post(u,p,sel,val,event=False):
 data=dict(p.hidden);data[sel]=val
 if event:data['__EVENTTARGET']=sel;data['__EVENTARGUMENT']=''
 elif p.submits:data[p.submits[0][0]]=p.submits[0][1]
 raw,st,final,enc=fetch(u,urllib.parse.urlencode(data).encode());return dec(raw,enc),st,final

# Parse factual rows from official DER activation bulletins. These rows give road/km/sense/city/speed,
# but not latitude/longitude; therefore they enter inventory only and are never plotted as exact points.
ROW_RE=re.compile(r'\b((?:SP|SPA|SPI)\s*[- ]?\d{2,3}(?:/\d{3})?)\s+0*(\d{1,3}[\.,]\d{3})\s+(Norte/Sul|Sul/Norte|Leste/Oeste|Oeste/Leste|Norte|Sul|Leste|Oeste)\s+(.+?)\s+(\d{2,3})\s*/\s*(\d{2,3})\s*\(?(?:km/h)?\)?',re.I)
ROW_DASH_RE=re.compile(r'\b((?:SP|SPA|SPI)\s*[- ]?\d{2,3}(?:/\d{3})?)\s*-\s*Km\s*0*(\d{1,3}[\.,]\d{3})\s*-\s*Sentido\s+(Norte/Sul|Sul/Norte|Leste/Oeste|Oeste/Leste|Norte|Sul|Leste|Oeste)\s*-\s*(.+?)\s*-\s*(\d{2,3})\s*/\s*(\d{2,3})\s*km/h',re.I)

def bulletin_rows(txt,url,source_date=None):
 p=parse(txt);plain=clean(' '.join(p.text)); out=[]
 matches=list(ROW_RE.finditer(plain))+list(ROW_DASH_RE.finditer(plain))
 for m in matches:
  road=re.sub(r'\s+',' ',m.group(1).upper()).replace('SP ','SP-').replace('SPA ','SPA-').replace('SPI ','SPI-')
  km=m.group(2).replace('.',','); direction=clean(m.group(3)); municipality=clean(m.group(4)).strip(' -;,.'); s1=int(m.group(5));s2=int(m.group(6)); spd=f'{s1} / {s2} km/h'
  external=f'bulletin:{road}:{km}:{direction}:{municipality}';rid='der_sp:'+hashlib.sha1(external.encode()).hexdigest()[:18]
  out.append({'id':rid,'source':'der_sp','external_id':external,'name':f'{road} · km {km} · {municipality}','latitude':None,'longitude':None,'speed_limit':s1,'speed_text':spd,'direction':direction,'status':'active','confidence':94,'municipality':municipality,'state':'SP','road':road,'km':km,'radar_type':'Fixo (ativação oficial)','der_number':None,'serial_number':None,'schedule':None,'study_url':None,'source_url':url,'source_date':source_date,'position_quality':'unmapped_official'})
 # de-dupe
 return list({x['id']:x for x in out}.values())

def sync_bulletins(limit=None):
 ids=DER_BULLETIN_IDS[:limit] if limit else DER_BULLETIN_IDS; items=[]; errors=[]
 for n,i in enumerate(ids,1):
  SYNC['message']=f'Lendo comunicado oficial DER {n}/{len(ids)}…';SYNC['roads_done']=n;SYNC['roads_total']=len(ids)
  url=f'{DER_NEWS}?idNoticia={i}'
  try:
   raw,st,final,enc=fetch(url);txt=dec(raw,enc)
   dm=re.search(r'\b(\d{2}/\d{2}/\d{4})\b',clean(' '.join(parse(txt).text))); sd=dm.group(1) if dm else None
   items.extend(bulletin_rows(txt,final,sd))
  except Exception as e:errors.append(f'{i}:{type(e).__name__}')
 return list({x['id']:x for x in items}.values()),errors


def road_code(value):
 x=clean(value).upper().replace('–','-').replace('—','-')
 m=re.search(r'\b(SPA|SPI|SP)\s*[- ]?\s*(\d{2,3})(?:\s*/\s*(\d{2,3}))?',x)
 if not m:return None
 return f'{m.group(1)}-{int(m.group(2)):03d}'+(f'/{int(m.group(3)):03d}' if m.group(3) else '')

def kmnum(v):
 if v is None:return None
 s=clean(v).replace(' ','').replace(',','.')
 m=re.search(r'-?\d+(?:\.\d+)?',s)
 try:return float(m.group()) if m else None
 except:return None

def hav(a,b):
 lon1,lat1=a;lon2,lat2=b;r=6371000.0
 p1=math.radians(lat1);p2=math.radians(lat2);dp=math.radians(lat2-lat1);dl=math.radians(lon2-lon1)
 h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
 return 2*r*math.asin(min(1,math.sqrt(h)))

def interp_line(coords,frac):
 if not coords:return None
 if len(coords)==1:return coords[0]
 frac=max(0.0,min(1.0,frac));lens=[hav(coords[i-1],coords[i]) for i in range(1,len(coords))];total=sum(lens)
 if total<=0:return coords[0]
 target=total*frac;acc=0
 for i,d in enumerate(lens,1):
  if acc+d>=target:
   f=(target-acc)/d if d else 0;a=coords[i-1];b=coords[i];return [a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f]
  acc+=d
 return coords[-1]

def flatten_desc(desc):
 # KML descriptions often contain HTML tables. Convert cells/lines into a permissive key/value map.
 txt=html.unescape(desc or '')
 cells=re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>',txt,re.I|re.S)
 cells=[clean(re.sub(r'<[^>]+>',' ',x)) for x in cells]
 out={}
 for i in range(0,len(cells)-1,2):
  if cells[i]:out[nk(cells[i])]=cells[i+1]
 plain=clean(re.sub(r'<[^>]+>',' ',txt))
 return out,plain

def fieldpick(fields,*needles):
 for n in needles:
  nn=nk(n)
  for k,v in fields.items():
   kk=nk(k)
   if kk==nn or nn in kk:return v
 return None

def parse_road_kmz(raw):
 z=zipfile.ZipFile(io.BytesIO(raw));names=[n for n in z.namelist() if n.lower().endswith('.kml')]
 if not names:raise RuntimeError('KMZ oficial sem arquivo KML')
 root=ET.fromstring(z.read(names[0]));segs=[]
 for pm in root.iter():
  if not pm.tag.endswith('Placemark'):continue
  fields={};desc='';name=''
  for el in pm.iter():
   tag=el.tag.split('}')[-1]
   if tag=='name' and el.text and not name:name=clean(el.text)
   elif tag=='description' and el.text:desc=el.text
   elif tag in ('Data','SimpleData'):
    key=el.attrib.get('name','');val=''
    if tag=='Data':
     for ch in el:
      if ch.tag.endswith('value') and ch.text:val=clean(ch.text)
    else:val=clean(el.text or '')
    if key:fields[key]=val
  dm,plain=flatten_desc(desc);fields.update({k:v for k,v in dm.items() if k not in fields})
  blob=' '.join([name,plain]+[str(v) for v in fields.values()]);rc=road_code(blob)
  if not rc:continue
  ki=kmnum(fieldpick(fields,'km inicial','km_inicial','kmini','km ini','km de','inicio km'))
  kf=kmnum(fieldpick(fields,'km final','km_final','kmfim','km fim','km ate','fim km'))
  if ki is None or kf is None:
   m=re.search(r'km\s*(?:inicial)?\s*[:=]?\s*(\d+[\.,]\d+).*?km\s*(?:final)?\s*[:=]?\s*(\d+[\.,]\d+)',blob,re.I)
   if m:ki,kf=kmnum(m.group(1)),kmnum(m.group(2))
  coords=[]
  for el in pm.iter():
   if el.tag.endswith('coordinates') and el.text:
    arr=[]
    for tok in re.split(r'\s+',el.text.strip()):
     ps=tok.split(',')
     if len(ps)>=2:
      try:
       lon=float(ps[0]);lat=float(ps[1])
       if -54<lon<-43 and -26<lat<-19:arr.append([lon,lat])
      except:pass
    if len(arr)>=2:coords=arr;break
  if len(coords)<2 or ki is None or kf is None or abs(kf-ki)<1e-6:continue
  # If official endpoint coordinates are present, orient geometry so first point = km inicial.
  sli=kmnum(fieldpick(fields,'latitude inicial','latitudei','lat inicial','lat_i')); slo=kmnum(fieldpick(fields,'longitude inicial','longitudei','long inicial','lon inicial','long_i'))
  slf=kmnum(fieldpick(fields,'latitude final','latitudef','lat final','lat_f')); sof=kmnum(fieldpick(fields,'longitude final','longitudef','long final','lon final','long_f'))
  orientation='geometry_order';cal=False
  if None not in (sli,slo):
   ds=hav(coords[0],[slo,sli]);de=hav(coords[-1],[slo,sli])
   if de<ds:coords=list(reversed(coords))
   cal=True;orientation='official_start_coordinate'
  elif None not in (slf,sof):
   ds=hav(coords[0],[sof,slf]);de=hav(coords[-1],[sof,slf])
   if ds<de:coords=list(reversed(coords))
   cal=True;orientation='official_end_coordinate'
  segs.append({'road':rc,'km_start':ki,'km_end':kf,'coords':coords,'calibrated':cal,'orientation':orientation,'name':name or None})
 return segs

def save_road_cache(segs,source_url=DER_ROAD_KMZ_URL):
 payload={'source_url':source_url,'fetched_at':now(),'segments':segs};_save_json(ROAD_CACHE,payload);return payload

def load_road_cache():
 try:
  p=_load_json(ROAD_CACHE,None);return p if isinstance(p,dict) else None
 except:return None

def ensure_road_network(force=False):
 cache=load_road_cache()
 if cache and cache.get('segments') and not force:return cache
 raw,st,final,enc=fetch(DER_ROAD_KMZ_URL,timeout=90);segs=parse_road_kmz(raw);usable=sum(1 for x in segs if x.get('coords') and x.get('km_start') is not None)
 if not usable:raise RuntimeError('Malha oficial DER baixada, mas nenhum trecho quilometrado pôde ser interpretado')
 payload=save_road_cache(segs,final);c=db();c.execute(database.upsert_statement('INSERT INTO road_network_meta(id,source_url,fetched_at,segments,usable_segments,sha256,error) VALUES(1,?,?,?,?,?,NULL)'),(final,payload['fetched_at'],len(segs),usable,hashlib.sha256(raw).hexdigest()));c.commit();c.close();return payload

def georef_one(r,segs):
 rc=road_code(r.get('road') or r.get('name'));k=kmnum(r.get('km'))
 if not rc or k is None:return None
 cand=[]
 for s in segs:
  if s['road']!=rc:continue
  lo=min(s['km_start'],s['km_end']);hi=max(s['km_start'],s['km_end'])
  if lo-0.03<=k<=hi+0.03:cand.append(s)
 if not cand:return None
 # Prefer the tightest interval and calibrated orientation.
 cand.sort(key=lambda s:(0 if s.get('calibrated') else 1,abs(s['km_end']-s['km_start'])))
 s=cand[0];den=s['km_end']-s['km_start'];frac=(k-s['km_start'])/den if den else 0.5;pt=interp_line(s['coords'],frac)
 if not pt:return None
 quality='derived_official_km' if s.get('calibrated') else 'derived_official_km_geometry_order'
 score=98 if s.get('calibrated') else 93
 return {'longitude':pt[0],'latitude':pt[1],'position_quality':quality,'confidence':max(int(r.get('confidence') or 0),score),'geo_meta':{'road':rc,'km':k,'segment_km_start':s['km_start'],'segment_km_end':s['km_end'],'orientation':s.get('orientation'),'network_source':DER_ROAD_KMZ_URL}}

def georef_inventory(force_network=False):
 network=ensure_road_network(force_network);segs=network['segments'];c=db();rows=c.execute("SELECT id,raw_json FROM radars WHERE state='SP' AND source='der_sp' AND (latitude IS NULL OR longitude IS NULL)").fetchall();mapped=0;missed=0;seen=now()
 for row in rows:
  r=json.loads(row['raw_json']);g=georef_one(r,segs)
  if not g:missed+=1;continue
  r.update({k:v for k,v in g.items() if k!='geo_meta'});r['geo_meta']=g['geo_meta']
  # version the coordinate enrichment exactly like other source changes
  res=upsert(c,r,seen);mapped+=1
 c.commit();total=c.execute("SELECT COUNT(*) FROM radars WHERE state='SP' AND source='der_sp' AND latitude IS NOT NULL AND longitude IS NOT NULL").fetchone()[0];c.close()
 refresh_physical_ids();checkpoint_db();return {'ok':True,'mapped_now':mapped,'mapped_total':total,'unmatched':missed,'network_segments':len(segs),'network_fetched_at':network.get('fetched_at'),'network_source':network.get('source_url')}

def road_network_status():
 cache=load_road_cache();c=db();row=c.execute('SELECT * FROM road_network_meta WHERE id=1').fetchone();c.close();return {'cached':bool(cache and cache.get('segments')),'segments':len(cache.get('segments',[])) if cache else 0,'meta':dict(row) if row else None,'url':DER_ROAD_KMZ_URL}

def seed_santo_andre(force=False):
 if not SANTO_ANDRE_SNAPSHOT.exists():return {'ok':False,'error':'snapshot ausente'}
 payload=json.loads(SANTO_ANDRE_SNAPSHOT.read_text(encoding='utf-8'));items=payload.get('items',[]);seen=now();imp=upd=unch=0
 with DB_WRITE_LOCK:
  c=db()
  try:
   for item in items:
    r=upsert(c,item,seen)
    if r=='imported':imp+=1
    elif r=='updated':upd+=1
    else:unch+=1
   c.execute(database.upsert_statement("INSERT INTO source_syncs(source_id,status,started_at,finished_at,http_status,imported,updated,unchanged,skipped,mapped,roads,source_url,error,diagnostic) VALUES('santo_andre','ok',?,?,?,?,?,?,?,?,?,?,?,?)"),(seen,seen,200,imp,upd,unch,0,len(items),0,SANTO_ANDRE_URL,None,f'snapshot oficial 2026-09; {len(items)}/{payload.get("declared_total_speed_locations",79)} linhas completas com coordenada direta; grade A'))
   c.commit()
  finally:c.close()
 refresh_physical_ids();checkpoint_db();return {'ok':True,'count':len(items),'imported':imp,'updated':upd,'unchanged':unch,'declared_total':payload.get('declared_total_speed_locations',79)}

def do_sync(mode='sample',road=''):
 if not hosted() and not LOCK.acquire(False):return
 c=None; imported=updated=unchanged=skipped=mapped=0;started=now();diag=[];items=[];search_ok=False
 try:
  SYNC.update({'running':True,'started_at':started,'finished_at':None,'message':'Abrindo consulta DER-SP…','roads_done':0,'roads_total':0,'records':0,'mapped':0,'derived':0,'error':None,'mode':mode})
  # 1) Primary: official radar search, which can provide exact coordinates.
  try:
   d=discover_search();search_ok=True;p=d['parser'];sel=d['select'];items.extend(d['direct']);roads=options(sel,mode,road);SYNC['roads_total']=len(roads)
   diag.append(f'consulta=OK HTTP {d["status"]}; seletor={sel["name"] if sel else "nenhum"}; opções={len(sel["options"]) if sel else 0}')
   if sel and roads:
    for i,(val,code) in enumerate(roads,1):
     SYNC['message']=f'Consulta oficial: {code}…';found=[]
     for evt in (False,True):
      try:
       txt,_,fin=post(d['url'],p,sel['name'],val,evt);found=parse_radars(parse(txt),fin,code)
       if found:break
      except Exception:pass
     if found:items.extend(found)
     else:skipped+=1
     SYNC['roads_done']=i;SYNC['records']=len(items);SYNC['mapped']=sum(x.get('latitude') is not None and x.get('longitude') is not None for x in items)
  except Exception as e:
   diag.append(f'consulta=indisponível ({type(e).__name__}: {e})')
  # 2) Fallback/augmentation: official activation bulletins. Real inventory, never fake map coordinates.
  SYNC.update({'message':'Complementando com comunicados oficiais DER…','roads_done':0,'roads_total':0})
  bitems,berrs=sync_bulletins(3 if mode=='sample' else None); items.extend(bitems)
  if berrs:diag.append('comunicados com falha: '+','.join(berrs))
  diag.append(f'comunicados={len(bitems)} registros')
  uniq={x['id']:x for x in items};items=list(uniq.values());seen=now()
  with DB_WRITE_LOCK:
   c=db()
   try:
    for item in items:
     res=upsert(c,item,seen);mapped+=int(item.get('latitude') is not None and item.get('longitude') is not None)
     if res=='imported':imported+=1
     elif res=='updated':updated+=1
     else:unchanged+=1
    c.commit()
   finally:c.close();c=None
  total=imported+updated+unchanged
  if total==0:raise RuntimeError('Nenhum radar oficial foi importado pela consulta nem pelos comunicados DER.')
  # Enrich unmapped official radars using the official DER road network (KMZ), never OSM guessing.
  try:
   SYNC['message']='Georreferenciando por malha oficial DER…'; gr=georef_inventory(False); mapped=gr['mapped_total']; SYNC['derived']=gr['mapped_now']; diag.append(f'malha_oficial={gr["network_segments"]} trechos; georef_novos={gr["mapped_now"]}; sem_correspondencia={gr["unmatched"]}')
  except Exception as ge:
   diag.append(f'georef_malha=indisponível ({type(ge).__name__}: {ge})')
  fin=now();diag.append(f'total={total}; coordenadas_exatas={mapped}')
  status='ok' if mapped else 'partial'; msg=(f'{total} radares oficiais no inventário; {mapped} com coordenadas exatas.' if mapped else f'{total} radares oficiais no inventário. Consulta de coordenadas do DER não respondeu; nenhum ponto aproximado foi inventado.')
  with DB_WRITE_LOCK:
   c=db()
   try:
    c.execute(database.upsert_statement("INSERT INTO source_syncs(source_id,status,started_at,finished_at,http_status,imported,updated,unchanged,skipped,mapped,roads,source_url,error,diagnostic) VALUES('der_sp',?,?,?,?,?,?,?,?,?,?,?,?,?)"),(status,started,fin,200 if search_ok else None,imported,updated,unchanged,skipped,mapped,SYNC['roads_total'],DER_SEARCH_URL,None,' | '.join(diag)));c.commit()
   finally:c.close();c=None
  refresh_physical_ids();checkpoint_db()
  SYNC.update({'running':False,'finished_at':fin,'message':msg,'records':total,'mapped':mapped,'error':None})
 except Exception as e:
  fin=now();err=f'{type(e).__name__}: {e}'
  with DB_WRITE_LOCK:
   ec=db()
   try:
    ec.execute(database.upsert_statement("INSERT INTO source_syncs(source_id,status,started_at,finished_at,error,source_url,diagnostic) VALUES('der_sp','error',?,?,?,?,?)"),(started,fin,err,DER_SEARCH_URL,' | '.join(diag)));ec.commit()
   finally:ec.close()
  SYNC.update({'running':False,'finished_at':fin,'message':'Falha DER-SP','error':err})
 finally:
  try:
   if c:c.close()
  except:pass
  if not hosted():LOCK.release()

def start(mode='sample',road=''):
 if hosted():
  launch(do_sync,(mode,road))
  return {'ok':not bool(SYNC.get('error')),'status':'error' if SYNC.get('error') else 'done','state':dict(SYNC)}
 if not hosted() and SYNC['running']:return {'status':'busy','state':SYNC}
 launch(do_sync,(mode,road));return {'status':'started','state':SYNC}
def _dir_norm(v):
 x=nk(v or '')
 toks=[]
 for key,label in [('norte','n'),('north','n'),('sul','s'),('south','s'),('leste','e'),('este','e'),('east','e'),('oeste','w'),('west','w')]:
  if re.search(r'\b'+key+r'\b',x):toks.append(label)
 return '/'.join(sorted(set(toks))) or None

def refresh_physical_ids():
 with DB_WRITE_LOCK:
  c=db(); rows=[dict(r) for r in c.execute("SELECT id,source,latitude,longitude,speed_limit,direction,serial_number,inmetro_registration,physical_radar_id FROM radars WHERE state='SP'")]
  groups=[]; updates=[]
  for r in rows:
   serial=clean(r.get('serial_number')); inm=clean(r.get('inmetro_registration'))
   if inm:
    pid='equip:'+hashlib.sha1(('inmetro|'+inm).encode()).hexdigest()[:18]
   elif serial and r.get('latitude') is not None and r.get('longitude') is not None:
    pid='equip:'+hashlib.sha1(f"serial|{serial}|{float(r['latitude']):.4f}|{float(r['longitude']):.4f}".encode()).hexdigest()[:18]
   elif serial:
    pid='record:'+hashlib.sha1(f"{r['source']}|{serial}|{r['id']}".encode()).hexdigest()[:18]
   elif r.get('latitude') is not None and r.get('longitude') is not None:
    pt=(float(r['longitude']),float(r['latitude'])); dnorm=_dir_norm(r.get('direction')); pid=None
    for g in groups:
     if g['source']==r['source']: continue
     if r.get('speed_limit') and g.get('speed_limit') and int(r['speed_limit'])!=int(g['speed_limit']): continue
     gd=g.get('direction')
     if dnorm and gd and dnorm!=gd: continue
     if distance_ll(pt,g['pt'])<=12:
      pid=g['pid'];break
    if not pid:
     pid='phys:'+hashlib.sha1(f"{r['id']}|{pt[0]:.6f}|{pt[1]:.6f}".encode()).hexdigest()[:18]
     groups.append({'pid':pid,'pt':pt,'source':r['source'],'speed_limit':r.get('speed_limit'),'direction':dnorm})
   else: pid='record:'+hashlib.sha1(r['id'].encode()).hexdigest()[:18]
   if r.get('physical_radar_id')!=pid: updates.append((pid,r['id']))
  if updates:c.executemany('UPDATE radars SET physical_radar_id=? WHERE id=?',updates);c.commit()
  c.close();return len(updates)

def get_radars(mapped_only=False):
 c=db();q="SELECT raw_json,physical_radar_id FROM radars WHERE state='SP'" + (" AND latitude IS NOT NULL AND longitude IS NOT NULL" if mapped_only else '');rows=c.execute(q).fetchall();c.close();out=[]
 for r in rows:
  x=json.loads(r['raw_json']);x['physical_radar_id']=r['physical_radar_id'];out.append(x)
 return out
def get_stats():
 c=db();a=c.execute("SELECT COUNT(*) FROM radars WHERE state='SP'").fetchone()[0];b=c.execute("SELECT COUNT(*) FROM radars WHERE state='SP' AND latitude IS NOT NULL AND longitude IS NOT NULL").fetchone()[0];d=c.execute("SELECT COUNT(*) FROM radars WHERE state='SP' AND status='active'").fetchone()[0];e=c.execute('SELECT COUNT(*) FROM radar_history').fetchone()[0];aa=c.execute("SELECT COUNT(*) FROM radars WHERE state='SP' AND position_quality='exact_official'").fetchone()[0];abc=c.execute("SELECT COUNT(*) FROM radars WHERE municipality IN ('Santo André','São Bernardo do Campo','São Caetano do Sul','Diadema','Mauá','Ribeirão Pires','Rio Grande da Serra')").fetchone()[0];phys=c.execute("SELECT COUNT(DISTINCT physical_radar_id) FROM radars WHERE state='SP' AND physical_radar_id IS NOT NULL").fetchone()[0];c.close();return {'inventory':a,'mapped':b,'active':d,'versions':e,'exact_a':aa,'abc':abc,'physical':phys}
def get_sources():
 c=db();states={r['source_id']:dict(r) for r in c.execute('SELECT * FROM source_syncs')};c.close();out=[]
 for s in SOURCES:x=dict(s);x['sync_state']=states.get(s['id']);out.append(x)
 return out
def diagnostic():
 result={'search_url':DER_SEARCH_URL,'landing_url':DER_LANDING,'tests':[]}
 for label,u in [('pesquisa',DER_SEARCH_URL),('pesquisa_alt',DER_SEARCH_ALT),('landing',DER_LANDING)]:
  try:
   raw,st,final,enc=fetch(u);txt=dec(raw,enc);p=parse(txt);sel=road_select(p);recs=parse_radars(p,final);result['tests'].append({'name':label,'ok':True,'url':final,'http':st,'size':len(txt),'tables':len(p.tables),'selects':len(p.selects),'road_select':sel['name'] if sel else None,'road_options':len(sel['options']) if sel else 0,'records':len(recs),'title_hint':bool(re.search(r'Radar|Fiscaliza',txt,re.I))})
  except Exception as e:result['tests'].append({'name':label,'ok':False,'error':f'{type(e).__name__}: {e}'})
 # Also prove the fallback path is parseable.
 try:
  b,errs=sync_bulletins(1);result['bulletin_test']={'ok':bool(b),'records':len(b),'errors':errs,'sample':[{k:x.get(k) for k in ('road','km','direction','municipality','speed_text')} for x in b[:3]]}
 except Exception as e:result['bulletin_test']={'ok':False,'error':f'{type(e).__name__}: {e}'}
 result['ok']=any(x.get('records',0)>0 for x in result['tests']) or result.get('bulletin_test',{}).get('ok',False)
 return result

# --- Radar SP v1.2: Navigation Core + Baixada ---------------------------------
PRAIA_GRANDE_URL='https://www.praiagrande.sp.gov.br/cartaservicos/Servicos/consultaCS.asp'
NOMINATIM_URL='https://nominatim.openstreetmap.org/search'
VALHALLA_URL='https://valhalla1.openstreetmap.de/route'
VALHALLA_URL_ALT='https://valhalla.openstreetmap.de/route'
OSRM_URL='https://router.project-osrm.org/route/v1/driving'
OVERPASS_URL=OVERPASS_ENDPOINTS[0]
GEOCODE_CACHE=DATA_DIR/'geocode_cache.json'
BUMPS_CACHE=DATA_DIR/'bumps_cache.json'
GEOCODE_POSITIVE_TTL=30*24*3600
GEOCODE_NOT_FOUND_TTL=12*3600
BUMPS_TTL=7*24*3600

PRAIA_GRANDE_POINTS=[
 {'name':'Av. Ayrton Senna da Silva oposto 382','direction':'PG/SV','speed_limit':60,'radar_type':'radar_fixo','neighborhood':'Sítio do Campo'},
 {'name':'Av. Ayrton Senna da Silva oposto 611','direction':'SV/PG','speed_limit':60,'radar_type':'radar_fixo','neighborhood':'Sítio do Campo'},
 {'name':'Av. Marechal Mallet, altura do nº 928','direction':'Fortaleza de Itaipu/Palácio das Artes','speed_limit':40,'radar_type':'lombada_eletronica','neighborhood':'Canto do Forte'},
 {'name':'Av. Marechal Mallet, altura do nº 1122','direction':'Fortaleza de Itaipu/Palácio das Artes','speed_limit':40,'radar_type':'lombada_eletronica','neighborhood':'Canto do Forte'},
 {'name':'Av. Presidente Kennedy, próximo ao nº 4520','direction':'Aviação/Tupi','speed_limit':40,'radar_type':'lombada_eletronica','neighborhood':'Aviação'},
 {'name':'Av. Presidente Kennedy, altura do nº 6020','direction':'Tupi/Ocian','speed_limit':40,'radar_type':'lombada_eletronica','neighborhood':'Tupi'},
 {'name':'Av. Presidente Kennedy, altura do nº 7954','direction':'Ocian/Mirim','speed_limit':40,'radar_type':'lombada_eletronica','neighborhood':'Ocian'},
 {'name':'Av. Presidente Kennedy, próximo à Prefeitura','direction':'Maracanã/Mirim','speed_limit':40,'radar_type':'lombada_eletronica','neighborhood':'Mirim'},
 {'name':'Av. Ministro Marcos Freire, próximo ao nº 8124','direction':'Anhanguera/Nova Mirim','speed_limit':40,'radar_type':'lombada_eletronica','neighborhood':'Anhanguera'},
 {'name':'Av. Dr. Roberto de Almeida Vinhas, próximo ao nº 20151','direction':'Ocian/Tupi','speed_limit':40,'radar_type':'lombada_eletronica','neighborhood':'Ocian'},
]

SANTOS_URL='https://cetsantos.com.br/radares-2/'
# Relação oficial CET Santos atualmente publicada como ATIVA. Quando um item possui
# dois sentidos/equipamentos no mesmo ponto, preservamos as séries/IDs em texto e um marcador por local.
SANTOS_POINTS=[
 {'name':'Av. Martins Fontes, altura do nº 465, curva da Sancap','speed_limit':50,'serial':'0337 / 0338','local_code':'9038 / 9039','radar_type':'radar_fixo'},
 {'name':'Av. Eng. Civ. Sérgio da Costa Matte, próximo ao Viaduto da Santa','speed_limit':40,'serial':'0340','local_code':'9041','radar_type':'radar_fixo'},
 {'name':'Av. Eng. Civ. Sérgio da Costa Matte, próximo à Rua Manoel Tourinho','speed_limit':40,'serial':'0339','local_code':'9040','radar_type':'radar_fixo'},
 {'name':'Rua Governador Pedro de Toledo x Av. Conselheiro Nébias','speed_limit':50,'serial':'0806','local_code':'9057','radar_type':'radar_semaforo'},
 {'name':'Rua Galeão Carvalhal x Av. Washington Luís','speed_limit':50,'serial':'0807','local_code':'9058','radar_type':'radar_semaforo'},
 {'name':'Av. Jovino de Mello x Rua João Fraccaroli','speed_limit':50,'serial':'0811','local_code':'9063','radar_type':'radar_semaforo'},
 {'name':'Av. Presidente Wilson, nº 185, próximo ao Emissário Submarino','speed_limit':50,'serial':'5100','local_code':'9046','radar_type':'radar_fixo'},
 {'name':'Av. Presidente Wilson, nº 1935, próximo ao Emissário Submarino','speed_limit':50,'serial':'5101','local_code':'9047','radar_type':'radar_fixo'},
 {'name':'Av. Presidente Wilson entre Rua Marcílio Dias e Rua Quintino Bocaiúva','speed_limit':50,'serial':'5104 / 5105','local_code':'9050 / 9051','radar_type':'radar_fixo'},
 {'name':'Av. Vicente de Carvalho, próximo à Rua da Paz','speed_limit':50,'serial':'5102 / 5103','local_code':'9048 / 9049','radar_type':'radar_fixo'},
 {'name':'Av. General Francisco Glycério x Rua Vidal Sion, próximo ao nº 132','speed_limit':50,'serial':'0803','local_code':'9045','radar_type':'radar_fixo'},
 {'name':'Rua Gercino Hugo Caparelli, próximo à Rua Yara Nascimento Santini','speed_limit':40,'serial':'0801','local_code':'9043','radar_type':'radar_fixo'},
 {'name':'Av. Eng. Manuel Ferramenta Jr, próximo ao nº 228','speed_limit':40,'serial':'0800','local_code':'9042','radar_type':'radar_fixo'},
 {'name':'Av. Pref. Dr. Antônio Manoel de Carvalho, descida do Morro Nova Cintra','speed_limit':30,'serial':'0802','local_code':'9044','radar_type':'radar_fixo'},
 {'name':'Av. Dr. Nilo Peçanha x Av. Pref. Dr. Antônio Manoel de Carvalho','speed_limit':40,'serial':'0802','local_code':'9044','radar_type':'radar_fixo'},
 {'name':'Av. Affonso Penna, nº 170/176, proximidades da Praça Palmares','speed_limit':50,'serial':'0815 / 0816','local_code':'9055 / 9056','radar_type':'radar_semaforo'},
 {'name':'Av. Bernardino de Campos x Rua Joaquim Távora','speed_limit':50,'serial':'0804 / 0805','local_code':'9053 / 9052','radar_type':'radar_semaforo'},
 {'name':'Av. Senador Feijó x Av. Rangel Pestana','speed_limit':50,'serial':'0808 / 5108','local_code':'9059 / 9069','radar_type':'radar_semaforo'},
 {'name':'Av. Nossa Senhora de Fátima, nº 400','speed_limit':40,'serial':'0810','local_code':'9060','radar_type':'radar_semaforo'},
 {'name':'Av. Martins Fontes, próximo à Rua Pio XII','speed_limit':50,'serial':'0817 / 0818','local_code':'9061 / 9062','radar_type':'radar_semaforo'},
 {'name':'Av. Eng. Civ. Sérgio da Costa Matte, próximo à Praça Iguatemi Martins','speed_limit':60,'serial':'0813','local_code':'9065','radar_type':'radar_semaforo'},
 {'name':'Av. Bartholomeu de Gusmão x Av. Cel. Joaquim Montenegro','speed_limit':50,'serial':'5109 / 5110','local_code':'9067 / 9068','radar_type':'radar_semaforo'},
 {'name':'Av. Bartholomeu de Gusmão, em frente ao nº 108','speed_limit':50,'serial':'5111 / 5112','local_code':'9072 / 9073','radar_type':'radar_semaforo'},
 {'name':'Av. Dr. Waldemar Leão x Av. Rangel Pestana','speed_limit':50,'serial':'5106 / 5107','local_code':'9070 / 9071','radar_type':'radar_semaforo'},
 {'name':'Av. Francisco Glycério x Av. Senador Pinheiro Machado','speed_limit':50,'serial':'5115 / 5015','local_code':'9074 / 9075','radar_type':'radar_semaforo'},
 {'name':'Acesso ao Viaduto Paulo Gomes Barbosa, entre Av. Martins Fontes e Av. Nossa Senhora de Fátima','speed_limit':40,'serial':'5116','local_code':'9076','radar_type':'radar_fixo'},
 {'name':'Av. Presidente Wilson x Av. Senador Pinheiro Machado','speed_limit':50,'serial':'5113 / 5114','local_code':'9077 / 9078','radar_type':'radar_semaforo'},
 {'name':'Av. Bernardino de Campos x Rua Carvalho de Mendonça','speed_limit':50,'serial':'1385 / 5150','local_code':'9080 / 9081','radar_type':'radar_semaforo'},
 {'name':'Rua Carvalho de Mendonça x Av. Bernardino de Campos','speed_limit':50,'serial':'1384','local_code':'9079','radar_type':'radar_semaforo'},
 {'name':'Rua João Pessoa x Av. Senador Feijó','speed_limit':50,'serial':'0812','local_code':'9083','radar_type':'radar_semaforo'},
 {'name':'Rua Eduardo Alves, próximo ao nº 186','speed_limit':None,'serial':'1343','local_code':'9082','radar_type':'restricao_caminhao'},
]


def _load_json(path, default):
 if hosted():
  with db() as c:
   row=c.execute('SELECT value_json FROM runtime_state WHERE key=?',(path.name,)).fetchone()
   return json.loads(row[0]) if row else default
 try:return json.loads(path.read_text(encoding='utf-8'))
 except:return default

def _save_json(path, obj):
 if hosted():
  with db() as c:c.execute('INSERT INTO runtime_state(key,value_json,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at',(path.name,json.dumps(obj,ensure_ascii=False),now()))
  return
 path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def _geocode_candidates(q):
 q=clean(q)
 # Consulta original + formas normalizadas para endereços oficiais como
 # "oposto 382", "altura do nº 928" e "próximo ao nº 4520".
 variants=[q]
 x=re.sub(r'\b(oposto|altura\s+do\s+n[ºo]?|pr[oó]ximo\s+ao\s+n[ºo]?)\s*', '', q, flags=re.I)
 x=re.sub(r'\bpr[oó]ximo\s+[àa]\s+Prefeitura\b','Prefeitura de Praia Grande',x,flags=re.I)
 if x!=q: variants.append(x)
 # Street-only fallback, still constrained to Praia Grande/SP by caller.
 street=re.sub(r',.*$','',x).strip()
 if street and street not in variants: variants.append(street)
 out=[]
 for v in variants:
  if v and v not in out:out.append(v)
 return out

def _cache_entry_items(entry, ttl):
 if isinstance(entry,list): return None
 if not isinstance(entry,dict): return None
 try: age=time.time()-float(entry.get('ts',0))
 except: return None
 if age>ttl:return None
 return entry.get('items',[])

def geocode_text(q, limit=5, force=False):
 cache=_load_json(GEOCODE_CACHE,{})
 key=clean(q).lower(); entry=cache.get(key)
 if not force and entry is not None:
  status=entry.get('status') if isinstance(entry,dict) else 'legacy'
  ttl=GEOCODE_NOT_FOUND_TTL if status=='not_found' else GEOCODE_POSITIVE_TTL
  items=_cache_entry_items(entry,ttl)
  if items is not None:return items[:limit]
 errors=[]
 for candidate in _geocode_candidates(q):
  for provider in ('nominatim','photon'):
   for attempt in range(2):
    try:
     if provider=='nominatim':
      params=urllib.parse.urlencode({'format':'jsonv2','limit':max(1,min(limit,5)),'countrycodes':'br','q':candidate})
      raw,_,_,_=http_request(NOMINATIM_URL+'?'+params,headers={'User-Agent':UA,'Accept':'application/json','Referer':'http://radarsp.local/'},timeout=12,method='GET',attempts=1);data=json.loads(raw.decode('utf-8'))
      out=[{'lat':float(x['lat']),'lon':float(x['lon']),'display_name':x.get('display_name',''),'type':x.get('type',''),'provider':'nominatim'} for x in data]
     else:
      params=urllib.parse.urlencode({'q':candidate,'limit':max(1,min(limit,5)),'lang':'pt'})
      raw,_,_,_=http_request('https://photon.komoot.io/api/?'+params,headers={'User-Agent':UA,'Accept':'application/json'},timeout=12,method='GET',attempts=1);data=json.loads(raw.decode('utf-8'))
      out=[]
      for f in data.get('features',[]):
       co=(f.get('geometry') or {}).get('coordinates') or []
       if len(co)>=2:
        lon,lat=float(co[0]),float(co[1]);pr=f.get('properties') or {};out.append({'lat':lat,'lon':lon,'display_name':', '.join(str(pr.get(k,'')) for k in ('name','street','city','state') if pr.get(k)),'type':pr.get('type',''),'provider':'photon'})
     out=[x for x in out if -25.5 < x['lat'] < -19.0 and -54.5 < x['lon'] < -44.0]
     if out:
      cache[key]={'status':'ok','ts':time.time(),'items':out};_save_json(GEOCODE_CACHE,cache);DEPENDENCY_STATE['geocode']={'status':'ok','last_ok':now(),'last_error':None};return out[:limit]
     break
    except Exception as e:
     errors.append(provider+':'+type(e).__name__)
     if attempt==0:time.sleep(.4)
 # Empty result after providers responded is cacheable briefly; network errors are not.
 if errors and len(errors)>=4:
  DEPENDENCY_STATE['geocode']={'status':'degraded','last_ok':DEPENDENCY_STATE['geocode'].get('last_ok'),'last_error':';'.join(errors[-4:])}
 else:
  cache[key]={'status':'not_found','ts':time.time(),'items':[]};_save_json(GEOCODE_CACHE,cache)
 return []

def _haversine_m(lat1,lon1,lat2,lon2):
 try:
  p1,p2=math.radians(lat1),math.radians(lat2);dp=math.radians(lat2-lat1);dl=math.radians(lon2-lon1)
  a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
  return 6371000*2*math.atan2(math.sqrt(a),math.sqrt(max(0,1-a)))
 except:return 10**12

def autocomplete_text(q,near_lat=None,near_lon=None,limit=7,submitted=False):
 from navigation_backend import search_address
 q=clean(q)
 if len(q)<3:return []
 # Reuse existing persistent runtime cache in hosted mode, no schema change.
 cache_path=DATA_DIR/'navigation_search_cache.json';cache=_load_json(cache_path,{})
 key=json.dumps(['navigation-v2',q.casefold(),round(near_lat,2) if near_lat is not None and math.isfinite(near_lat) else None,round(near_lon,2) if near_lon is not None and math.isfinite(near_lon) else None,bool(submitted)],ensure_ascii=False)
 entry=cache.get(key)
 if entry and time.time()-entry['at']<(300 if entry['items'] else 30):return entry['items'][:limit]
 items=search_address(q,http_request,UA,near_lat,near_lon,limit,submitted)
 if len(cache)>=128:cache.pop(next(iter(cache)))
 cache[key]={'at':time.time(),'items':items};_save_json(cache_path,cache)
 return items


def _santos_query_variants(name):
 out=[f'{name}, Santos, SP, Brasil']
 x=name
 # Intersections: try forms commonly understood by OSM geocoders.
 if re.search(r'\s+x\s+',x,re.I):
  parts=re.split(r'\s+x\s+',x,maxsplit=1,flags=re.I)
  if len(parts)==2:
   out += [f'{parts[0]}, {parts[1]}, Santos, SP, Brasil',f'{parts[0]} e {parts[1]}, Santos, SP, Brasil']
 # Strip proximity prose while keeping the street/number itself.
 y=re.sub(r',?\s*(pr[oó]ximo|proximidades|entre|descida)\b.*$','',x,flags=re.I).strip(' ,')
 if y and y!=x:out.append(f'{y}, Santos, SP, Brasil')
 # Normalize abbreviations that are common in the official list.
 z=x.replace('Av.','Avenida').replace('R. ','Rua ')
 if z!=x:out.append(f'{z}, Santos, SP, Brasil')
 ded=[]
 for v in out:
  if v not in ded:ded.append(v)
 return ded

def _seed_praia_grande_impl(try_geocode=True):
 c=db(); seen=now(); imported=updated=unchanged=mapped=0; errors=[]
 for i,p in enumerate(PRAIA_GRANDE_POINTS,1):
  rid=f'pg_official_{i:02d}'
  old=c.execute('SELECT latitude,longitude,position_quality,quality_grade FROM radars WHERE id=?',(rid,)).fetchone()
  # CRITICAL: never erase a coordinate already resolved in a previous run.
  lat=old['latitude'] if old and old['latitude'] is not None else None
  lon=old['longitude'] if old and old['longitude'] is not None else None
  provider=None
  if try_geocode and (lat is None or lon is None):
   queries=[
    f"{p['name']}, {p['neighborhood']}, Praia Grande, SP, Brasil",
    f"{p['name']}, Praia Grande, SP, Brasil",
   ]
   try:
    for q in queries:
     hits=geocode_text(q,3)
     if hits:
      # Prefer results explicitly mentioning Praia Grande when available.
      hit=next((h for h in hits if 'praia grande' in h.get('display_name','').lower()),hits[0])
      lat,lon,provider=hit['lat'],hit['lon'],hit.get('provider')
      break
    if lat is None:errors.append(f"{i}:sem_correspondencia")
    time.sleep(.35)
   except Exception as e:errors.append(f"{i}:{type(e).__name__}")
  item={
    'id':rid,'source':'praia_grande','external_id':str(i),'name':p['name'],
    'latitude':lat,'longitude':lon,'speed_limit':p['speed_limit'],'speed_text':str(p['speed_limit']),
    'direction':p['direction'],'status':'active','confidence':94 if lat is not None else 88,'municipality':'Praia Grande',
    'state':'SP','road':p['name'].split(',')[0],'km':None,'radar_type':p['radar_type'],'der_number':None,'serial_number':None,
    'schedule':None,'study_url':None,'source_url':PRAIA_GRANDE_URL,'source_date':'consulta municipal vigente','position_quality':('geocoded_official_address_'+provider if provider else (old['position_quality'] if old and lat is not None else 'official_address_only')),
    'inmetro_registration':None,'lanes':None,'local_code':None,'quality_grade':('B' if lat is not None else 'C'),
    'physical_status':'official_current_listing','neighborhood':p['neighborhood']
   }
  res=upsert(c,item,seen); mapped+=int(lat is not None and lon is not None)
  imported+=res=='imported';updated+=res=='updated';unchanged+=res=='unchanged'
 c.execute(database.upsert_statement("INSERT INTO source_syncs(source_id,status,started_at,finished_at,http_status,imported,updated,unchanged,skipped,mapped,source_url,error,diagnostic) VALUES('praia_grande',?,?,?,?,?,?,?,?,?,?,?,?)"),('ok' if mapped==len(PRAIA_GRANDE_POINTS) else ('partial' if mapped else 'error'),seen,now(),200,imported,updated,unchanged,0,mapped,PRAIA_GRANDE_URL,None,f'{len(PRAIA_GRANDE_POINTS)} pontos oficiais; {mapped} geocodificados; erros={errors}'))
 c.commit();c.close(); return {'count':len(PRAIA_GRANDE_POINTS),'mapped':mapped,'errors':errors}


def _seed_santos_impl(try_geocode=True):
 c=db(); seen=now(); imported=updated=unchanged=mapped=0; errors=[]
 for i,p in enumerate(SANTOS_POINTS,1):
  rid=f'santos_official_{i:02d}'
  old=c.execute('SELECT latitude,longitude,position_quality FROM radars WHERE id=?',(rid,)).fetchone()
  lat=old['latitude'] if old and old['latitude'] is not None else None
  lon=old['longitude'] if old and old['longitude'] is not None else None
  provider=None
  if try_geocode and (lat is None or lon is None):
   try:
    hits=[]
    for qq in _santos_query_variants(p['name']):
     hits=geocode_text(qq,6,force=True)
     hits=[h for h in hits if -24.05 < h['lat'] < -23.85 and -46.50 < h['lon'] < -46.20]
     if hits:break
    if hits:
     hit=next((h for h in hits if 'santos' in h.get('display_name','').lower()),hits[0]);lat,lon,provider=hit['lat'],hit['lon'],hit.get('provider')
    else:errors.append(f'{i}:sem_correspondencia')
    time.sleep(.25)
   except Exception as e:errors.append(f'{i}:{type(e).__name__}')
  item={'id':rid,'source':'santos','external_id':str(i),'name':p['name'],'latitude':lat,'longitude':lon,
   'speed_limit':p.get('speed_limit'),'speed_text':str(p.get('speed_limit')) if p.get('speed_limit') else None,'direction':None,'status':'active','confidence':96 if lat is not None else 91,
   'municipality':'Santos','state':'SP','road':p['name'].split(',')[0],'km':None,'radar_type':p.get('radar_type'),'der_number':None,'serial_number':p.get('serial'),
   'schedule':None,'study_url':None,'source_url':SANTOS_URL,'source_date':'relação CET Santos vigente','position_quality':('geocoded_official_address_'+provider if provider else (old['position_quality'] if old and lat is not None else 'official_address_only')),
   'inmetro_registration':None,'lanes':None,'local_code':p.get('local_code'),'quality_grade':'B' if lat is not None else 'C','physical_status':'official_active_listing'}
  res=upsert(c,item,seen);mapped+=int(lat is not None and lon is not None);imported+=res=='imported';updated+=res=='updated';unchanged+=res=='unchanged'
 c.execute(database.upsert_statement("INSERT INTO source_syncs(source_id,status,started_at,finished_at,http_status,imported,updated,unchanged,skipped,mapped,source_url,error,diagnostic) VALUES('santos',?,?,?,?,?,?,?,?,?,?,?,?)"),('ok' if mapped==len(SANTOS_POINTS) else ('partial' if mapped else 'error'),seen,now(),200,imported,updated,unchanged,0,mapped,SANTOS_URL,None,f'{len(SANTOS_POINTS)} locais oficiais ativos; {mapped} geocodificados; erros={errors}'))
 c.commit();c.close();return {'count':len(SANTOS_POINTS),'mapped':mapped,'errors':errors}

def seed_praia_grande(try_geocode=True):
 with DB_WRITE_LOCK:
  return _seed_praia_grande_impl(try_geocode)

def seed_santos(try_geocode=True):
 with DB_WRITE_LOCK:
  return _seed_santos_impl(try_geocode)

def sync_baixada_background():
 if BAIXADA_SYNC['running']:
  return
 BAIXADA_SYNC.update({'running':True,'started_at':now(),'finished_at':None,'message':'Sincronizando Praia Grande…','praia_grande':None,'santos':None,'error':None})
 try:
  pg=seed_praia_grande(True); BAIXADA_SYNC.update({'praia_grande':pg,'message':'Sincronizando Santos…'})
  st=seed_santos(True); refresh_physical_ids(); checkpoint_db(); BAIXADA_SYNC.update({'santos':st,'message':f"Baixada concluída: {pg.get('mapped',0)} Praia Grande + {st.get('mapped',0)} Santos mapeados."})
 except Exception as e:
  BAIXADA_SYNC.update({'error':f'{type(e).__name__}: {e}','message':'Falha ao sincronizar Baixada'})
 finally:
  BAIXADA_SYNC.update({'running':False,'finished_at':now()})

def _post_json(url,obj,timeout=25,headers=None,attempts=2):
 data=json.dumps(obj,ensure_ascii=False).encode('utf-8'); h={'User-Agent':UA,'Content-Type':'application/json','Accept':'application/json','X-Client-Id':'radar-sp-local-prototype'}; h.update(headers or {})
 raw,status,final,_=http_request(url,data=data,headers=h,timeout=timeout,method='POST',attempts=attempts)
 if status>=400:raise RuntimeError(f'HTTP {status} em {final}')
 return json.loads(raw.decode('utf-8'))

def _rad(a):return a*math.pi/180
def _xy(lon,lat,lat0):return lon*111320*math.cos(_rad(lat0)),lat*110540
def point_seg_distance_m(pt,a,b):
 lat0=pt[1]; px,py=_xy(pt[0],pt[1],lat0); ax,ay=_xy(a[0],a[1],lat0); bx,by=_xy(b[0],b[1],lat0); dx,dy=bx-ax,by-ay
 if dx==dy==0:return math.hypot(px-ax,py-ay),0.0
 t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy))); return math.hypot(px-(ax+t*dx),py-(ay+t*dy)),t

def bearing_deg(a,b):
 lon1,lat1,lon2,lat2=map(_rad,[a[0],a[1],b[0],b[1]]); y=math.sin(lon2-lon1)*math.cos(lat2);x=math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(lon2-lon1);return (math.degrees(math.atan2(y,x))+360)%360

def _direction_bearing(v):
 n=_dir_norm(v)
 if not n or '/' in n:return None
 return {'n':0.0,'e':90.0,'s':180.0,'w':270.0}.get(n)

def _angle_diff(a,b):return abs((a-b+180)%360-180)

def _alert_lateral_threshold(r):
 q=str(r.get('position_quality') or '')
 if q=='exact_official':return 65
 if q.startswith('derived_official'):return 55
 if q.startswith('geocoded_official_address'):return 38
 return 45

def route_alerts(coords, threshold=130):
 if len(coords)<2:return []
 cum=[0.0]
 for a,b in zip(coords,coords[1:]):cum.append(cum[-1]+distance_ll(a,b))
 alerts=[]
 for r in get_radars(True):
  if r.get('latitude') is None or not r.get('speed_limit'):continue
  pt=(float(r['longitude']),float(r['latitude'])); best=(1e18,0,0.0)
  for i,(a,b) in enumerate(zip(coords,coords[1:])):
   d,t=point_seg_distance_m(pt,a,b)
   if d<best[0]:best=(d,i,t)
  allowed=min(threshold,_alert_lateral_threshold(r))
  if best[0]>allowed:continue
  seg_bearing=bearing_deg(coords[best[1]],coords[best[1]+1]); rb=_direction_bearing(r.get('direction')); dstatus='unknown'
  if rb is not None:
   delta=_angle_diff(seg_bearing,rb);dstatus='match' if delta<=75 else 'opposite'
   if dstatus=='opposite':continue
  along=cum[best[1]]+(cum[best[1]+1]-cum[best[1]])*best[2]
  alerts.append({'type':'lombada_eletronica' if 'lombada' in str(r.get('radar_type','')).lower() else 'radar','distance_from_route_m':round(best[0]),'lateral_threshold_m':allowed,'direction_check':dstatus,'route_bearing':round(seg_bearing),'along_m':round(along),'latitude':r['latitude'],'longitude':r['longitude'],'speed_limit':r.get('speed_limit'),'title':r.get('name'),'municipality':r.get('municipality'),'id':r.get('id'),'physical_radar_id':r.get('physical_radar_id'),'source':'local_official'})
 return sorted(alerts,key=lambda x:x['along_m'])

def distance_ll(a,b):
 R=6371000; p1,p2=_rad(a[1]),_rad(b[1]); dp=_rad(b[1]-a[1]); dl=_rad(b[0]-a[0]); h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2; return 2*R*math.asin(math.sqrt(h))

def _bumps_cache_key(coords):
 if not coords:return ''
 xs=[p[0] for p in coords];ys=[p[1] for p in coords]
 sig=f"{min(xs):.2f}|{min(ys):.2f}|{max(xs):.2f}|{max(ys):.2f}|{coords[0][0]:.3f}|{coords[0][1]:.3f}|{coords[-1][0]:.3f}|{coords[-1][1]:.3f}"
 return hashlib.sha1(sig.encode()).hexdigest()[:20]

def osm_bumps_for_route(coords):
 if len(coords)<2:return [],'no_route'
 cache=_load_json(BUMPS_CACHE,{});key=_bumps_cache_key(coords);entry=cache.get(key)
 if isinstance(entry,dict) and time.time()-float(entry.get('ts',0))<BUMPS_TTL:
  return entry.get('items',[]),'cache'
 step=max(1,len(coords)//32); samples=coords[::step][:36]
 clauses=''.join(f'node(around:90,{lat:.6f},{lon:.6f})["traffic_calming"];' for lon,lat in samples);query='[out:json][timeout:12];('+clauses+');out body;'
 try:
  raw,_,_,_=http_request(OVERPASS_URL,data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':UA,'Content-Type':'application/x-www-form-urlencoded'},timeout=15,method='POST',attempts=1);data=json.loads(raw.decode())
  out=[];seen=set()
  for e in data.get('elements',[]):
   if e.get('type')!='node' or e.get('id') in seen:continue
   seen.add(e.get('id'));tags=e.get('tags',{});out.append({'type':'lombada','latitude':e.get('lat'),'longitude':e.get('lon'),'title':'Lombada / redutor físico','kind':tags.get('traffic_calming','yes'),'source':'OpenStreetMap'})
  cache[key]={'ts':time.time(),'items':out};_save_json(BUMPS_CACHE,cache);DEPENDENCY_STATE['overpass']={'status':'ok','last_ok':now(),'last_error':None};return out,'ok'
 except Exception as e:
  DEPENDENCY_STATE['overpass']={'status':'degraded','last_ok':DEPENDENCY_STATE['overpass'].get('last_ok'),'last_error':f'{type(e).__name__}: {e}'};return [],f'{type(e).__name__}: {e}'

def _route_osrm(flat,flon,tlat,tlon):
 url=f"{OSRM_URL}/{flon:.7f},{flat:.7f};{tlon:.7f},{tlat:.7f}?overview=full&geometries=geojson&steps=true&alternatives=false"
 raw,status,final,_=http_request(url,headers={'User-Agent':UA,'Accept':'application/json'},timeout=10,method='GET',attempts=1)
 if status>=400:raise RuntimeError(f'OSRM HTTP {status}')
 data=json.loads(raw.decode('utf-8')); routes=data.get('routes') or []
 if not routes:raise RuntimeError('OSRM não retornou rota')
 r=routes[0];coords=(r.get('geometry') or {}).get('coordinates') or [];steps=[]
 for leg in r.get('legs',[]):
  for st in leg.get('steps',[]):
   man=st.get('maneuver') or {};typ=man.get('type','');mod=man.get('modifier','');name=st.get('name') or ''
   from navigation_backend import route_step
   steps.append(route_step(st))
 return r,coords,steps

def _finish_route(r,coords,steps,provider):
 with db() as c:modern=database.table_exists(c,'map_points')
 alerts=community.route_points(sys.modules[__name__],coords) if modern else route_alerts(coords)
 bstatus='local_index';alerts.sort(key=lambda x:x.get('along_m',10**12))
 # Providers disagree on distance units. Use route geometry as the reference and
 # accept either meters or kilometres only when it matches the drawn route.
 geom_m=sum(distance_ll(a,b) for a,b in zip(coords,coords[1:]))
 raw_distance=float(r.get('distance',0) or 0)
 candidates=[raw_distance, raw_distance*1000.0]
 plausible=[x for x in candidates if x>0]
 distance_m=round(min(plausible,key=lambda x:abs(x-geom_m))) if plausible and geom_m>0 else round(raw_distance)
 if geom_m>0 and (distance_m < geom_m*.45 or distance_m > geom_m*2.2):
  distance_m=round(geom_m)
 return {'geometry':{'type':'LineString','coordinates':coords},'distance_m':distance_m,'duration_s':round(float(r.get('duration',0))),'steps':steps,'alerts':alerts,'bumps_status':bstatus,'provider':provider,'alerts_engine':'relas-map-v2' if modern else 'legacy'}

def build_route(flat,flon,tlat,tlon):
 payload={'locations':[{'lat':flat,'lon':flon},{'lat':tlat,'lon':tlon}],'costing':'auto','units':'kilometers','language':'pt-BR','format':'osrm','shape_format':'geojson','voice_instructions':True,'banner_instructions':True}
 errors=[]
 for url,label in ((VALHALLA_URL,'Valhalla demo 1'),(VALHALLA_URL_ALT,'Valhalla demo 2')):
  try:
   data=_post_json(url,payload,10,attempts=1);routes=data.get('routes') or []
   if not routes:raise RuntimeError('sem rota')
   r=routes[0];coords=(r.get('geometry') or {}).get('coordinates') or [];steps=[]
   for leg in r.get('legs',[]):
    for st in leg.get('steps',[]):
     from navigation_backend import route_step
     steps.append(route_step(st))
   DEPENDENCY_STATE['valhalla']={'status':'ok','last_ok':now(),'last_error':None};return _finish_route(r,coords,steps,label)
  except Exception as e:
   errors.append(f'{label}: {type(e).__name__}: {e}')
 DEPENDENCY_STATE['valhalla']={'status':'degraded','last_ok':DEPENDENCY_STATE['valhalla'].get('last_ok'),'last_error':' | '.join(errors)}
 try:
  r,coords,steps=_route_osrm(flat,flon,tlat,tlon);DEPENDENCY_STATE['osrm']={'status':'ok','last_ok':now(),'last_error':None};return _finish_route(r,coords,steps,'OSRM fallback')
 except Exception as e:
  DEPENDENCY_STATE['osrm']={'status':'degraded','last_ok':DEPENDENCY_STATE['osrm'].get('last_ok'),'last_error':f'{type(e).__name__}: {e}'}
  errors.append(f'OSRM: {type(e).__name__}: {e}')
  raise RuntimeError('Nenhum provedor de rota respondeu. '+' | '.join(errors))
# -------------------------------------------------------------------------------



def _cookie_dict(header):
 out={}
 for part in (header or '').split(';'):
  if '=' in part:
   k,v=part.strip().split('=',1);out[k]=v
 return out

def _admin_authed(handler):
 token=_cookie_dict(handler.headers.get('Cookie','')).get('radar_admin')
 return AUTH.valid(token)

def _admin_event(kind,message,details=None):
 try:
  with DB_WRITE_LOCK:
   c=db();c.execute('INSERT INTO admin_events(created_at,kind,message,details) VALUES(?,?,?,?)',(now(),kind,message,json.dumps(details,ensure_ascii=False) if details is not None else None));c.commit();c.close()
 except Exception:pass

def sync_municipalities_ibge():
 started=now()
 try:
  raw,st,final,enc=http_request(IBGE_SP_MUNICIPIOS,headers={'User-Agent':UA,'Accept':'application/json'},timeout=20,attempts=2)
  data=json.loads(raw.decode(enc or 'utf-8','replace'));seen=now();n=0
  with DB_WRITE_LOCK:
   c=db()
   try:
    for x in data:
     mid=str(x.get('id') or '');name=clean(x.get('nome'))
     if mid and name:
      c.execute('INSERT INTO municipalities(ibge_id,name,state,last_refresh) VALUES(?,?,\'SP\',?) ON CONFLICT(ibge_id) DO UPDATE SET name=excluded.name,last_refresh=excluded.last_refresh',(mid,name,seen));n+=1
    c.commit()
   finally:c.close()
  _admin_event('municipalities','Lista municipal atualizada',{'count':n,'source':final});return {'ok':True,'count':n,'source':final,'status':st}
 except Exception as e:
  c=db();cached=c.execute("SELECT COUNT(*) FROM municipalities WHERE state='SP'").fetchone()[0];c.close()
  err=f'{type(e).__name__}: {e}'
  _admin_event('municipalities_error','Falha ao atualizar lista municipal',{'error':err,'cached':cached})
  if cached:
   return {'ok':False,'degraded':True,'count':cached,'cached':True,'error':err,'message':'IBGE indisponível; mantendo lista municipal já salva.'}
  raise

def municipality_coverage():
 c=db();munis=[dict(r) for r in c.execute("SELECT ibge_id,name FROM municipalities ORDER BY name")]
 counts={r['municipality']:dict(r) for r in c.execute("SELECT municipality,COUNT(*) inventory,SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) mapped,COUNT(DISTINCT source) sources FROM radars WHERE state='SP' AND municipality IS NOT NULL GROUP BY municipality")}
 if not munis:
  known=sorted(set(counts)|{'São Paulo','Campinas','Guarulhos','São Bernardo do Campo','Santo André','São Caetano do Sul','Santos','Praia Grande','Sorocaba','São José dos Campos','Osasco','Diadema','Mauá'})
  munis=[{'ibge_id':None,'name':x} for x in known]
 out=[]
 for m in munis:
  x=counts.get(m['name'],{});out.append({'ibge_id':m.get('ibge_id'),'name':m['name'],'inventory':x.get('inventory',0),'mapped':x.get('mapped',0) or 0,'sources':x.get('sources',0),'status':'covered' if (x.get('mapped',0) or 0)>0 else ('inventory' if x.get('inventory',0)>0 else 'missing')})
 c.close();return out

def source_registry_state():
 c=db();rows=[dict(r) for r in c.execute('SELECT * FROM source_registry ORDER BY priority DESC,name')];sync={r['source_id']:dict(r) for r in c.execute('SELECT * FROM source_syncs')};counts={r['source']:dict(r) for r in c.execute("SELECT source,COUNT(*) inventory,SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) mapped,COUNT(DISTINCT municipality) municipalities FROM radars WHERE state='SP' GROUP BY source")};c.close()
 for r in rows:r['sync']=sync.get(r['source_id']);r['counts']=counts.get(r['source_id'],{'inventory':0,'mapped':0,'municipalities':0})
 return rows

def _pick(row,aliases):
 norm={nk(k):v for k,v in row.items()}
 for a in aliases:
  if nk(a) in norm and clean(norm[nk(a)]):return norm[nk(a)]
 return None

def _latest_antt_csv():
 raw,st,final,enc=http_request(ANTT_CKAN_API,headers={'User-Agent':UA,'Accept':'application/json'},timeout=25,attempts=2)
 meta=json.loads(raw.decode(enc or 'utf-8','replace'));resources=(meta.get('result') or {}).get('resources') or []
 candidates=[]
 for r in resources:
  fmt=clean(r.get('format')).lower();name=clean(r.get('name')).lower();url=clean(r.get('url'))
  if not url:continue
  if fmt=='csv' and ('radar' in name or 'dados dos radares' in name):candidates.append(r)
 if not candidates:
  candidates=[r for r in resources if clean(r.get('format')).lower()=='csv' and clean(r.get('url'))]
 if not candidates:raise RuntimeError('ANTT: nenhum recurso CSV encontrado no catálogo atual')
 def dt(r):return clean(r.get('last_modified') or r.get('created') or '')
 pick=sorted(candidates,key=dt)[-1]
 return clean(pick.get('url')),{'name':pick.get('name'),'last_modified':pick.get('last_modified'),'created':pick.get('created'),'format':pick.get('format')}

def sync_antt_sp():
 started=now();_admin_event('sync','Iniciando ANTT SP')
 csv_url,resource=_latest_antt_csv()
 raw,st,final,enc=http_request(csv_url,headers={'User-Agent':UA,'Accept':'text/csv,*/*'},timeout=45,attempts=2)
 text=raw.decode(enc or 'utf-8','replace');sample=text[:4096];delim=';' if sample.count(';')>sample.count(',') else ','
 reader=csv.DictReader(io.StringIO(text),delimiter=delim);items=[];seen=now()
 for i,row in enumerate(reader,1):
  uf=clean(_pick(row,['uf','estado','sg_uf','uf_municipio']))
  if uf and uf.upper()!='SP':continue
  lat=fnum(_pick(row,['latitude','lat','vl_latitude']));lon=fnum(_pick(row,['longitude','lon','lng','vl_longitude']))
  municipio=clean(_pick(row,['municipio','município','nm_municipio','cidade'])) or None
  road=clean(_pick(row,['rodovia','br','via','nm_rodovia'])) or None;km=clean(_pick(row,['km','km_m','quilometro','quilômetro'])) or None
  spd=speed(_pick(row,['velocidade','velocidade_regulamentada','limite','km/h','velocidade permitida']))
  direction=clean(_pick(row,['sentido','direcao','direção'])) or None
  serial=clean(_pick(row,['serie','série','numero_serie','número de série'])) or None
  ext=clean(_pick(row,['id','codigo','código','numero','número'])) or f'{road}|{km}|{direction}|{i}'
  if not any([lat is not None,lon is not None,road,municipio]):continue
  rid='antt_sp:'+hashlib.sha1(ext.encode('utf-8','ignore')).hexdigest()[:20]
  items.append({'id':rid,'source':'antt_sp','external_id':ext,'name':f'{road or "Rodovia federal"}{(" · km "+km) if km else ""}{(" · "+municipio) if municipio else ""}','latitude':lat,'longitude':lon,'speed_limit':spd,'speed_text':str(spd) if spd else None,'direction':direction,'status':'active','confidence':99 if lat is not None and lon is not None else 92,'municipality':municipio,'state':'SP','road':road,'km':km,'radar_type':'Radar em rodovia concedida','der_number':None,'serial_number':serial,'schedule':None,'study_url':None,'source_url':final,'source_date':clean(resource.get('last_modified') or resource.get('created') or 'ANTT dados abertos 2026'),'position_quality':'exact_official' if lat is not None and lon is not None else 'unmapped_official'})
 c=db();imp=upd=unch=0
 with DB_WRITE_LOCK:
  for item in items:
   r=upsert(c,item,seen);imp+=r=='imported';upd+=r=='updated';unch+=r=='unchanged'
  mapped=sum(1 for x in items if x.get('latitude') is not None and x.get('longitude') is not None)
  c.execute(database.upsert_statement("INSERT INTO source_syncs(source_id,status,started_at,finished_at,http_status,imported,updated,unchanged,skipped,mapped,roads,source_url,error,diagnostic) VALUES('antt_sp',?,?,?,?,?,?,?,?,?,?,?,?,?)"),('ok' if items else 'error',started,now(),st,imp,upd,unch,0,mapped,0,final,None,f'{len(items)} registros SP lidos do recurso ANTT mais recente; resource={resource.get("name")}; delimiter={delim}'))
  c.commit();c.close()
 refresh_physical_ids();checkpoint_db();res={'ok':True,'count':len(items),'mapped':mapped,'imported':imp,'updated':upd,'unchanged':unch};_admin_event('sync','ANTT SP concluída',res);return res

def admin_dashboard():
 c=db();tot=c.execute("SELECT COUNT(*) n,SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) mapped,COUNT(DISTINCT municipality) municipalities,COUNT(DISTINCT source) sources FROM radars WHERE state='SP'").fetchone();pending=c.execute("SELECT COUNT(*) FROM radars WHERE state='SP' AND (latitude IS NULL OR longitude IS NULL)").fetchone()[0];events=[dict(r) for r in c.execute('SELECT * FROM admin_events ORDER BY id DESC LIMIT 20')];c.close()
 cov=municipality_coverage();return {'ok':True,'kpis':{'inventory':tot['n'] or 0,'mapped':tot['mapped'] or 0,'municipalities':tot['municipalities'] or 0,'sources':tot['sources'] or 0,'unmapped':pending,'target_municipalities':645,'municipalities_loaded':len(cov)},'sources':source_registry_state(),'coverage':cov,'events':events,'credentials_warning':'Senha temporária local. Troque antes de publicar o app.'}

def stability_diagnostics():
 if hosted():
  with db() as c:return dict(database.status(c),environment=environment(),dependencies='request-scoped external providers')
 c=db(); syncs=[dict(r) for r in c.execute('SELECT * FROM source_syncs ORDER BY source_id')]; total=c.execute("SELECT COUNT(*) FROM radars WHERE state='SP'").fetchone()[0];mapped=c.execute("SELECT COUNT(*) FROM radars WHERE state='SP' AND latitude IS NOT NULL AND longitude IS NOT NULL").fetchone()[0];phys=c.execute("SELECT COUNT(DISTINCT physical_radar_id) FROM radars WHERE state='SP' AND physical_radar_id IS NOT NULL").fetchone()[0];c.close()
 def cache_info(path):
  obj=_load_json(path,{}) if path.exists() else {};return {'exists':path.exists(),'entries':len(obj) if isinstance(obj,dict) else 0,'path':str(path)}
 return {'ok':True,'version':'2.2.0','db':{'path':str(DB_PATH),'persistent':DB_PATH.parent!=BUNDLED_DATA_DIR,'exists':DB_PATH.exists(),'inventory':total,'mapped':mapped,'physical_ids':phys},'maplibre':{'js':MAPLIBRE_JS.exists(),'css':MAPLIBRE_CSS.exists()},'caches':{'geocode':cache_info(GEOCODE_CACHE),'bumps':cache_info(BUMPS_CACHE),'road':cache_info(ROAD_CACHE)},'dependencies':DEPENDENCY_STATE,'sources':syncs,'baixada':BAIXADA_SYNC}

# --- v1.4 State Intelligence: objetos viários + semáforos ---------------------
def canonical_radar_type(v, source=None):
    x=nk(v or '')
    if 'lombada' in x or 'redutor' in x:return 'lombada_eletronica'
    if 'semafor' in x or 'red light' in x:return 'radar_semaforo'
    if source in ('antt_sp','der_sp') or 'rodov' in x:return 'radar_rodoviario'
    if 'restricao' in x or 'caminhao' in x:return 'restricao'
    return 'radar_fixo'

def radar_type_stats():
    c=db();rows=c.execute("SELECT source,radar_type,COUNT(*) n,SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) mapped FROM radars WHERE state='SP' GROUP BY source,radar_type").fetchall();c.close()
    out={}
    for r in rows:
        k=canonical_radar_type(r['radar_type'],r['source']);x=out.setdefault(k,{'inventory':0,'mapped':0});x['inventory']+=r['n'] or 0;x['mapped']+=r['mapped'] or 0
    return out

def seed_signal_networks():
    rows=[
      ('sp_scats','São Paulo','Semáforos inteligentes SCATS','adaptive',1677,0,'Tempos são recalculados a cada ciclo conforme fluxo. Não existe contagem fixa confiável para todos os cruzamentos.','https://prefeitura.sp.gov.br/web/obras/w/sem%C3%A1foros-inteligentes-reduzem-lentid%C3%A3o-e-tornam-o-tr%C3%A2nsito-mais-fluido-em-s%C3%A3o-paulo','2026'),
      ('santos_sync','Santos','Rede semafórica sincronizada','coordinated',381,0,'Rede municipal modernizada/sincronizada. Alguns cruzamentos usam detecção de demanda; tempos individuais não são publicados como feed aberto.','https://www.santos.sp.gov.br/?q=noticia%2Fsistema-de-sincronizacao-de-semaforos-ja-facilita-transito-em-santos','2024-2026'),
      ('campinas_smart','Campinas','Semáforos inteligentes EMDEC','adaptive',100,0,'Câmeras detectam fluxo e ajustam a fase verde em tempo real.','https://www.campinas.sp.gov.br/noticias/campinas-alcanca-a-instalacao-de-100-semaforos-%E2%80%98inteligentes%E2%80%99-tecnologia-a-servico-da-fluidez-135729','2026'),
    ]
    c=db();ts=now()
    with DB_WRITE_LOCK:
        for r in rows:c.execute(database.upsert_statement('INSERT INTO signal_networks(id,municipality,name,mode,count_known,live_timing,description,source_url,source_date,last_seen) VALUES(?,?,?,?,?,?,?,?,?,?)'),(*r,ts))
        c.commit();c.close()
    return len(rows)

def signal_network_state():
    c=db();rows=[dict(r) for r in c.execute('SELECT * FROM signal_networks ORDER BY municipality')];c.close();return rows

def road_object_stats():
    c=db();rows=c.execute("SELECT object_type,COUNT(*) n,SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) mapped,COUNT(DISTINCT municipality) municipalities FROM road_objects WHERE state='SP' GROUP BY object_type").fetchall();c.close()
    return {r['object_type']:{'inventory':r['n'] or 0,'mapped':r['mapped'] or 0,'municipalities':r['municipalities'] or 0} for r in rows}

def _upsert_road_object(c,item,seen):
    raw=json.dumps(item,ensure_ascii=False,sort_keys=True);rid=item['id'];old=c.execute('SELECT first_seen,raw_json FROM road_objects WHERE id=?',(rid,)).fetchone()
    keys=('source','external_id','object_type','name','latitude','longitude','municipality','state','status','confidence','official','speed_limit','direction','timing_mode','cycle_seconds','green_seconds','red_seconds','adaptive','timing_source','source_url','source_date','ingested_by','ingestion_batch','provenance_note')
    vals=[item.get(k) for k in keys]
    if old and old['raw_json']==raw:
        c.execute('UPDATE road_objects SET last_seen=?,ingested_by=COALESCE(?,ingested_by),ingestion_batch=COALESCE(?,ingestion_batch),provenance_note=COALESCE(?,provenance_note) WHERE id=?',(seen,item.get('ingested_by'),item.get('ingestion_batch'),item.get('provenance_note'),rid));return 'unchanged'
    if old:c.execute('INSERT INTO road_object_history(object_id,source,captured_at,raw_json) VALUES(?,?,?,?)',(rid,item['source'],seen,old['raw_json']))
    cols=','.join(keys);qs=','.join(['?']*(1+len(keys)+3))
    c.execute(database.upsert_statement(f'INSERT INTO road_objects(id,{cols},first_seen,last_seen,raw_json) VALUES({qs})'),[rid]+vals+[old['first_seen'] if old else seen,seen,raw])
    return 'updated' if old else 'imported'

def _municipality_osm_area_id(name):
    q=urllib.parse.urlencode({'q':f'{name}, São Paulo, Brasil','format':'jsonv2','limit':5,'addressdetails':1})
    raw,_,_,enc=http_request('https://nominatim.openstreetmap.org/search?'+q,headers={'User-Agent':UA,'Accept':'application/json'},timeout=25,attempts=2)
    arr=json.loads(raw.decode(enc or 'utf-8','replace'));target=nk(name)
    for x in arr:
        disp=nk(x.get('display_name',''));addr=x.get('address') or {}
        if target in disp and x.get('osm_type')=='relation' and ('sao paulo' in disp or nk(addr.get('state',''))=='sao paulo'):
            return 3600000000+int(x['osm_id'])
    return None

def _municipality_bbox(name):
    q=urllib.parse.urlencode({'q':f'{name}, São Paulo, Brasil','format':'jsonv2','limit':3,'addressdetails':1})
    raw,_,_,enc=http_request('https://nominatim.openstreetmap.org/search?'+q,headers={'User-Agent':UA,'Accept':'application/json'},timeout=25,attempts=2)
    arr=json.loads(raw.decode(enc or 'utf-8','replace'))
    for x in arr:
        bb=x.get('boundingbox');disp=nk(x.get('display_name',''))
        if bb and len(bb)==4 and ('sao paulo' in disp or ', sp' in disp):
            south,north,west,east=map(float,bb);return south,west,north,east
    raise RuntimeError('município não localizado para caixa geográfica')


def _overpass_request(query,timeout=55):
    payload=urllib.parse.urlencode({'data':query}).encode('utf-8')
    errors=[]
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            raw,st,final,enc=http_request(endpoint,data=payload,method='POST',headers={'User-Agent':UA,'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},timeout=timeout,attempts=1)
            data=json.loads(raw.decode(enc or 'utf-8','replace'))
            if isinstance(data,dict) and 'elements' in data:
                DEPENDENCY_STATE['overpass']={'status':'ok','last_ok':now(),'last_error':None}
                return data,st,endpoint
            errors.append(f'{endpoint}: resposta sem elements')
        except Exception as e:
            errors.append(f'{endpoint}: {type(e).__name__}: {e}')
    DEPENDENCY_STATE['overpass']={'status':'degraded','last_ok':DEPENDENCY_STATE['overpass'].get('last_ok'),'last_error':' | '.join(errors)}
    raise RuntimeError('Overpass indisponível: '+' | '.join(errors))

def _wfs_feature_types(base_url):
    q=urllib.parse.urlencode({'service':'WFS','version':'2.0.0','request':'GetCapabilities'})
    raw,st,final,enc=http_request(base_url+'?'+q,headers={'User-Agent':UA,'Accept':'application/xml,text/xml,*/*'},timeout=30,attempts=2)
    root=ET.fromstring(raw)
    out=[]
    for ft in root.iter():
        if not str(ft.tag).endswith('FeatureType'): continue
        name=title=''
        for ch in list(ft):
            tag=str(ch.tag)
            if tag.endswith('Name') and not name:name=clean(ch.text)
            elif tag.endswith('Title') and not title:title=clean(ch.text)
        if name:out.append({'name':name,'title':title})
    return out

def _wfs_pick_feature(base_url,keywords):
    kws=[_norm_city(x).replace(' ','') for x in keywords]
    types=_wfs_feature_types(base_url)
    scored=[]
    for x in types:
        hay=_norm_city((x.get('name') or '')+' '+(x.get('title') or '')).replace(' ','')
        score=sum(10 for k in kws if k and k in hay)
        if 'semafor' in hay:score+=20
        if 'cruzamento' in hay:score+=5
        if score:scored.append((score,x))
    if not scored:return None,types
    scored.sort(key=lambda z:z[0],reverse=True)
    return scored[0][1],types

def _wfs_hits(base_url,type_name):
    errors=[]
    for ver,key in [('2.0.0','typeNames'),('1.1.0','typeName')]:
        try:
            q=urllib.parse.urlencode({'service':'WFS','version':ver,'request':'GetFeature',key:type_name,'resultType':'hits'})
            raw,st,final,enc=http_request(base_url+'?'+q,headers={'User-Agent':UA,'Accept':'application/xml,text/xml,*/*'},timeout=25,attempts=1)
            root=ET.fromstring(raw)
            for attr in ('numberMatched','numberOfFeatures'):
                v=root.attrib.get(attr)
                if v not in (None,'unknown'):
                    try:return int(v)
                    except:pass
            return 0
        except Exception as e:errors.append(f'{ver}: {type(e).__name__}: {e}')
    raise RuntimeError('WFS hits falhou: '+' | '.join(errors))

def _wfs_geojson(base_url,type_name):
    attempts=[
      ('2.0.0','typeNames', 'application/json'),
      ('1.1.0','typeName', 'application/json'),
      ('1.1.0','typeName', 'json'),
    ]
    errors=[]
    for ver,key,outfmt in attempts:
        try:
            q=urllib.parse.urlencode({'service':'WFS','version':ver,'request':'GetFeature',key:type_name,'outputFormat':outfmt,'srsName':'EPSG:4326'})
            raw,st,final,enc=http_request(base_url+'?'+q,headers={'User-Agent':UA,'Accept':'application/json,*/*'},timeout=45,attempts=1)
            obj=json.loads(raw.decode(enc or 'utf-8','replace'))
            if isinstance(obj,dict) and isinstance(obj.get('features'),list):return obj,st,final
            errors.append(f'{ver}: sem features')
        except Exception as e:errors.append(f'{ver}: {type(e).__name__}: {e}')
    raise RuntimeError('WFS GetFeature falhou: '+' | '.join(errors))

def _point_from_geometry(g):
    if not isinstance(g,dict):return None
    typ=g.get('type');coords=g.get('coordinates')
    if typ=='Point' and isinstance(coords,list) and len(coords)>=2:
        try:return float(coords[1]),float(coords[0])
        except:return None
    if typ in ('MultiPoint','LineString') and isinstance(coords,list) and coords:
        c=coords[0]
        if isinstance(c,list) and len(c)>=2:
            try:return float(c[1]),float(c[0])
            except:return None
    return None

def _sync_official_signal_wfs(municipality,source_id,source_name,base_url,keywords):
    seen=now();chosen,types=_wfs_pick_feature(base_url,keywords)
    if not chosen:raise RuntimeError(f'Nenhuma camada de semáforos localizada em {source_name}')
    gj,st,final=_wfs_geojson(base_url,chosen['name']);features=gj.get('features') or []
    imp=upd=unch=skipped=0
    c=db()
    with DB_WRITE_LOCK:
        for idx,f in enumerate(features):
            p=_point_from_geometry(f.get('geometry'))
            if not p:skipped+=1;continue
            lat,lon=p;props=f.get('properties') or {};ext=clean(props.get('id') or props.get('codigo') or hashlib.sha256(f'{lon:.7f},{lat:.7f}'.encode()).hexdigest()[:20])
            existing=c.execute('SELECT id,external_id FROM road_objects WHERE source=? AND abs(latitude-?)<0.0000001 AND abs(longitude-?)<0.0000001 LIMIT 1',(source_id,lat,lon)).fetchone()
            name=clean(props.get('nome') or props.get('name') or props.get('local') or props.get('endereco') or chosen.get('title') or 'Semáforo')
            timing='adaptive' if any('scats' in str(v).lower() or 'adapt' in str(v).lower() for v in props.values()) else 'unknown'
            item={'id':existing['id'] if existing else f'{source_id}:{ext}','source':source_id,'external_id':ext,'object_type':'traffic_signal','name':name,'latitude':lat,'longitude':lon,'municipality':municipality,'state':'SP','status':'active','confidence':96,'official':1,'speed_limit':None,'direction':clean(props.get('sentido') or props.get('direction')),'timing_mode':timing,'cycle_seconds':None,'green_seconds':None,'red_seconds':None,'adaptive':1 if timing=='adaptive' else 0,'timing_source':source_name,'source_url':base_url,'source_date':'consulta WFS oficial'}
            r=_upsert_road_object(c,item,seen);imp+=r=='imported';upd+=r=='updated';unch+=r=='unchanged'
        c.execute(database.upsert_statement("INSERT INTO source_syncs(source_id,status,started_at,finished_at,http_status,imported,updated,unchanged,mapped,source_url,diagnostic) VALUES(?,?,?,?,?,?,?,?,?,?,?)"),(source_id,'ok',seen,now(),st,imp,upd,unch,imp+upd+unch,base_url,f'{municipality}: camada {chosen["name"]}; {len(features)} features; {skipped} sem ponto'))
        c.commit()
    c.close();_admin_event('signals',f'Semáforos oficiais sincronizados · {municipality}',{'source':source_name,'layer':chosen,'features':len(features),'imported':imp,'updated':upd,'unchanged':unch,'skipped':skipped})
    return {'ok':True,'municipality':municipality,'source_id':source_id,'source_name':source_name,'layer':chosen,'features':len(features),'imported':imp,'updated':upd,'unchanged':unch,'skipped':skipped}

def discover_official_signals_city(municipality,op_id):
    norm=_norm_city(municipality)
    cfg=None
    if norm in ('sao paulo','sao paulo sp'):
        cfg=('geosampa_signals','GeoSampa · Cruzamentos Semaforizados',GEOSAMPA_WFS,['semaforo','cruzamentos semaforizados'])
    elif norm=='santos':
        cfg=('santos_signals_wfs','SIGSantos · Semáforos',SANTOS_WFS,['semaforo','sinalizacao semaforica'])
    if not cfg:return None
    sid,name,url,kws=cfg;_oplog(op_id,f'Testando fonte oficial de semáforos: {name}',stage='semáforos oficiais',municipality=municipality,source_id=sid)
    try:
        chosen,types=_wfs_pick_feature(url,kws)
        if not chosen:raise RuntimeError('camada de semáforos não identificada no WFS')
        try: count=_wfs_hits(url,chosen['name'])
        except Exception: count=0
        _save_municipality_source(municipality,sid,name,url,'wfs_official','available',True,count,0,f'Camada: {chosen.get("name")} · {chosen.get("title")} · {count} feature(s)')
        _record_source_attempt(municipality,sid,'available',count,0,f'WFS disponível; camada {chosen.get("name")}; {count} feature(s)',url)
        _queue_update(municipality,'signals',sid,f'Importar semáforos oficiais · {municipality}',{'source_name':name,'url':url,'layer':chosen,'count':count})
        _oplog(op_id,f'Fonte oficial pronta: {chosen.get("title") or chosen.get("name")} · {count} ponto(s). Adicionada à fila.',level='success',stage='semáforos oficiais',municipality=municipality,source_id=sid,details={'layer':chosen,'count':count})
        return {'source_id':sid,'name':name,'status':'available','items':count,'mapped':0,'queued':True,'layer':chosen}
    except Exception as e:
        msg=f'{type(e).__name__}: {e}';_record_source_attempt(municipality,sid,'error',0,0,msg,url);_oplog(op_id,f'Fonte oficial de semáforos falhou: {msg}',level='error',stage='semáforos oficiais',municipality=municipality,source_id=sid);return {'source_id':sid,'name':name,'status':'error','error':msg}

def sync_osm_objects_city(municipality,ingested_by=None,ingestion_batch=None,provenance_note=None,strict_area=False):
    municipality=clean(municipality)
    if not municipality:raise RuntimeError('Informe o município')
    area_id=None
    if strict_area:
        try:area_id=_municipality_osm_area_id(municipality)
        except Exception:area_id=None
    if area_id:
        query=f'''[out:json][timeout:55];area({area_id})->.a;(node["highway"="traffic_signals"](area.a);node["traffic_calming"](area.a);node["highway"="speed_camera"](area.a);node["enforcement"="maxspeed"](area.a););out body;''';bbox=None
    else:
        south,west,north,east=_municipality_bbox(municipality)
        if (north-south)*(east-west)>0.8:raise RuntimeError('Área muito grande para consulta pública; use uma cidade/bairro menor')
        query=f'''[out:json][timeout:45];(node["highway"="traffic_signals"]({south},{west},{north},{east});node["traffic_calming"]({south},{west},{north},{east});node["highway"="speed_camera"]({south},{west},{north},{east});node["enforcement"="maxspeed"]({south},{west},{north},{east}););out body;''';bbox=[south,west,north,east]
    obj,st,endpoint=_overpass_request(query,timeout=65);els=obj.get('elements') or [];seen=now();imp=upd=unch=0;counts={'traffic_signal':0,'physical_bump':0,'speed_camera_osm':0}
    c=db()
    with DB_WRITE_LOCK:
        for e in els:
            tags=e.get('tags') or {};typ=None
            if tags.get('highway')=='traffic_signals':typ='traffic_signal'
            elif tags.get('highway')=='speed_camera' or tags.get('enforcement')=='maxspeed':typ='speed_camera_osm'
            elif tags.get('traffic_calming'):typ='physical_bump'
            if not typ:continue
            counts[typ]=counts.get(typ,0)+1;ext=str(e.get('id'));rid='osmobj:'+ext
            name=clean(tags.get('name') or tags.get('ref') or tags.get('traffic_calming') or ('Semáforo' if typ=='traffic_signal' else 'Objeto viário'));maxspeed=speed(tags.get('maxspeed'))
            item={'id':rid,'source':'osm_road_objects','external_id':ext,'object_type':typ,'name':name,'latitude':fnum(e.get('lat')),'longitude':fnum(e.get('lon')),'municipality':municipality,'state':'SP','status':'mapped','confidence':64 if strict_area else 60,'official':0,'speed_limit':maxspeed,'direction':tags.get('direction'),'timing_mode':'unknown','cycle_seconds':None,'green_seconds':None,'red_seconds':None,'adaptive':0,'timing_source':None,'source_url':'https://www.openstreetmap.org/','source_date':'consulta OSM atual','ingested_by':ingested_by,'ingestion_batch':ingestion_batch,'provenance_note':provenance_note}
            r=_upsert_road_object(c,item,seen);imp+=r=='imported';upd+=r=='updated';unch+=r=='unchanged'
        c.execute(database.upsert_statement("INSERT INTO source_syncs(source_id,status,started_at,finished_at,http_status,imported,updated,unchanged,mapped,source_url,diagnostic) VALUES('osm_road_objects',?,?,?,?,?,?,?,?,?,?)"),('ok',seen,now(),st,imp,upd,unch,imp+upd+unch,'https://www.openstreetmap.org/',f'{municipality}: {len(els)} objetos consultados via {endpoint}; area_id={area_id}'));c.commit();c.close()
    _admin_event('osm',f'Objetos viários OSM sincronizados · {municipality}',{'elements':len(els),'imported':imp,'updated':upd,'unchanged':unch,'counts':counts,'ingested_by':ingested_by,'batch':ingestion_batch})
    return {'ok':True,'municipality':municipality,'elements':len(els),'imported':imp,'updated':upd,'unchanged':unch,'counts':counts,'bbox':bbox,'area_id':area_id,'endpoint':endpoint}

def get_road_objects(mapped_only=True):
    c=db();q="SELECT * FROM road_objects WHERE state='SP'"+(' AND latitude IS NOT NULL AND longitude IS NOT NULL' if mapped_only else '')
    rows=[dict(r) for r in c.execute(q)];c.close();return rows

def state_intelligence_dashboard():
    base=admin_dashboard();base['radar_types']=radar_type_stats();base['road_objects']=road_object_stats();base['signal_networks']=signal_network_state()
    base['coverage_model']={'statewide_backbone':['DER-SP · estaduais não concedidas','ANTT · federais concedidas','ARTESP CCM · operação/tempo de percurso'],'urban_connectors':['CET-SP','Santo André','Santos','Praia Grande','Campinas','São Bernardo','São Caetano'],'community_discovery':'OSM apenas como descoberta de semáforos/lombadas; não substitui fonte oficial de fiscalização.','signal_timing':'Só mostrar segundos quando houver feed/fonte do cruzamento. Sistemas adaptativos devem aparecer como “tempo variável”.'}
    return base


# --- v1.5 Admin Operations: persistent city intelligence ---------------------
KNOWN_CITY_CONNECTORS={
 'santo andre':('santo_andre','Prefeitura de Santo André',seed_santo_andre,SANTO_ANDRE_URL),
 'santos':('santos','CET Santos',seed_santos,'https://cetsantos.com.br/radares-2/'),
 'praia grande':('praia_grande','Prefeitura de Praia Grande',seed_praia_grande,'https://www.praiagrande.sp.gov.br/cartaservicos/Servicos/consultaCS.asp'),
}

def _norm_city(v):return nk(v).replace('  ',' ').strip()

def _admin_token(req):
    auth=req.headers.get('Authorization','') or ''
    if auth.lower().startswith('bearer '):return auth[7:].strip()
    return _cookie_dict(req.headers.get('Cookie','')).get('radar_admin')

def _admin_authed_v15(req):
    tok=_admin_token(req)
    return AUTH.valid(tok)

def _record_source_attempt(city,source_id,status,item_count=0,mapped_count=0,diagnostic='',url=''):
    c=db();ts=now()
    with DB_WRITE_LOCK:
        c.execute('INSERT INTO source_attempts(municipality,source_id,attempted_at,status,item_count,mapped_count,diagnostic,url) VALUES(?,?,?,?,?,?,?,?)',(city,source_id,ts,status,int(item_count or 0),int(mapped_count or 0),clean(diagnostic),clean(url)))
        c.commit();c.close()

def _save_municipality_source(city,source_id,name,url,stype,status,official,item_count=0,mapped_count=0,diagnostic=''):
    c=db();ts=now();old=c.execute('SELECT first_seen,last_success FROM municipality_sources WHERE municipality=? AND source_id=?',(city,source_id)).fetchone();first=old['first_seen'] if old else ts;success=ts if status in ('confirmed','available','ok') else (old['last_success'] if old else None)
    with DB_WRITE_LOCK:
        c.execute(database.upsert_statement('INSERT INTO municipality_sources(municipality,source_id,source_name,source_url,source_type,status,official,first_seen,last_attempt,last_success,item_count,mapped_count,diagnostic) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'),(city,source_id,name,url,stype,status,1 if official else 0,first,ts,success,int(item_count or 0),int(mapped_count or 0),clean(diagnostic)))
        c.commit();c.close()

def _set_gap(city,reason,status='needs_source'):
    c=db();ts=now();old=c.execute('SELECT attempts FROM source_gaps WHERE municipality=?',(city,)).fetchone();attempts=(old['attempts'] if old else 0)+1
    with DB_WRITE_LOCK:
        c.execute(database.upsert_statement('INSERT INTO source_gaps(municipality,status,reason,attempts,last_checked,next_retry,notes) VALUES(?,?,?,?,?,?,COALESCE((SELECT notes FROM source_gaps WHERE municipality=?),NULL))'),(city,status,clean(reason),attempts,ts,None,city))
        c.commit();c.close()

def _clear_gap(city):
    c=db();
    with DB_WRITE_LOCK:
        c.execute('DELETE FROM source_gaps WHERE municipality=?',(city,));c.commit();c.close()

def _city_counts(city):
    c=db();r=c.execute("SELECT COUNT(*) n,SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) mapped,COUNT(DISTINCT source) sources FROM radars WHERE state='SP' AND lower(municipality)=lower(?)",(city,)).fetchone();o=c.execute("SELECT COUNT(*) n FROM road_objects WHERE state='SP' AND lower(municipality)=lower(?)",(city,)).fetchone();c.close();return {'radars':r['n'] or 0,'mapped':r['mapped'] or 0,'sources':r['sources'] or 0,'objects':o['n'] or 0}

def _probe_backbones(city):
    c=db();rows=c.execute("SELECT source,COUNT(*) n,SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) mapped FROM radars WHERE state='SP' AND lower(municipality)=lower(?) GROUP BY source",(city,)).fetchall();c.close();out=[]
    for r in rows:
        if r['source'] in ('der_sp','antt_sp'):
            nm='DER-SP' if r['source']=='der_sp' else 'ANTT Dados Abertos'
            _save_municipality_source(city,r['source'],nm,'', 'state_backbone','confirmed',True,r['n'],r['mapped'],f'{r["n"]} registro(s) já salvos na base estadual')
            _record_source_attempt(city,r['source'],'confirmed',r['n'],r['mapped'],'já presente na base estadual')
            out.append({'source_id':r['source'],'name':nm,'status':'confirmed','items':r['n'],'mapped':r['mapped']})
    return out

def _official_open_data_scout(city):
    # Best-effort official catalog search. Failure becomes a logged attempt, never deletes data.
    queries=[f'{city} radar',f'{city} fiscalização eletrônica',f'{city} semáforo']
    found=[]
    endpoints=[
      ('dadosabertos_sp','Dados Abertos SP','https://dadosabertos.sp.gov.br/api/3/action/package_search?q='),
    ]
    for sid,name,base in endpoints:
      ok=False;diag=[]
      for q in queries:
        try:
          raw,st,final,enc=http_request(base+urllib.parse.quote(q),headers={'User-Agent':UA,'Accept':'application/json'},timeout=6,attempts=1)
          obj=json.loads(raw.decode(enc or 'utf-8','replace'));res=((obj.get('result') or {}).get('results') or []) if obj.get('success') else []
          for pkg in res[:8]:
            title=clean(pkg.get('title') or pkg.get('name'));url=clean(pkg.get('url') or '')
            txt=nk(title+' '+clean(pkg.get('notes')))
            if any(k in txt for k in ('radar','fiscalizacao','semafor','transito')):
              found.append({'source_id':sid,'name':title or name,'url':url or base,'status':'candidate','official':True});ok=True
          diag.append(f'{q}:{len(res)}')
        except Exception as e:diag.append(f'{q}:erro {type(e).__name__}')
      _record_source_attempt(city,sid,'candidate' if ok else 'unavailable',0,0,'; '.join(diag),base)
      if ok:_save_municipality_source(city,sid,name,base,'official_catalog','candidate',True,0,0,'; '.join(diag))
    return found

def scan_city_intelligence(city,include_osm=True):
    city=clean(city);norm=_norm_city(city);result={'municipality':city,'sources':[],'errors':[],'counts_before':_city_counts(city)}
    # 1) Persisted statewide backbone already captured.
    result['sources']+=_probe_backbones(city)
    # 2) Known official municipal connector.
    conn=KNOWN_CITY_CONNECTORS.get(norm)
    if conn:
        sid,name,fn,url=conn
        try:
            r=fn(True) or {};cnt=_city_counts(city);items=int(r.get('count') or r.get('inventory') or cnt['radars']);mapped=int(r.get('mapped') or cnt['mapped'])
            _save_municipality_source(city,sid,name,url,'municipal_connector','confirmed',True,items,mapped,json.dumps(r,ensure_ascii=False)[:1200]);_record_source_attempt(city,sid,'confirmed',items,mapped,'connector oficial executado',url)
            result['sources'].append({'source_id':sid,'name':name,'status':'confirmed','items':items,'mapped':mapped})
        except Exception as e:
            msg=f'{type(e).__name__}: {e}';_record_source_attempt(city,sid,'error',0,0,msg,url);result['errors'].append(msg)
    # 3) Official open-data scout (candidate leads only).
    try: result['sources']+=_official_open_data_scout(city)
    except Exception as e: result['errors'].append('catalog:'+str(e))
    # 4) OSM discovery is complementary, never official.
    if include_osm:
        try:
            r=sync_osm_objects_city(city);items=int(r.get('elements') or 0)
            _save_municipality_source(city,'osm_road_objects','OpenStreetMap · descoberta','https://www.openstreetmap.org/','community_discovery','discovery',False,items,items,'semáforos/lombadas/câmeras como candidatos');_record_source_attempt(city,'osm_road_objects','discovery',items,items,'consulta OSM concluída','https://www.openstreetmap.org/')
            result['sources'].append({'source_id':'osm_road_objects','name':'OSM descoberta','status':'discovery','items':items,'mapped':items})
        except Exception as e:
            msg=f'OSM {type(e).__name__}: {e}';_record_source_attempt(city,'osm_road_objects','error',0,0,msg,'https://www.openstreetmap.org/');result['errors'].append(msg)
    result['counts_after']=_city_counts(city)
    has_official=any(x.get('status')=='confirmed' and x.get('source_id')!='osm_road_objects' for x in result['sources']) or result['counts_after']['radars']>0
    if has_official:_clear_gap(city)
    else:_set_gap(city,'Nenhuma fonte oficial com dados importáveis foi confirmada nesta rodada; mantido na fila para nova investigação.')
    result['status']='covered' if has_official else ('discovery_only' if result['counts_after']['objects'] else 'needs_source')
    _admin_event('city_scan',f'Varredura municipal · {city}',result)
    return result

def _prepare_city_batch(cities):
    cities=[clean(x) for x in (cities or []) if clean(x)]
    seen=[];keys=set()
    for x in cities:
        k=_norm_city(x)
        if k and k not in keys:keys.add(k);seen.append(x)
    cities=seen[:5]
    if not cities:raise RuntimeError('Selecione pelo menos 1 município')
    return cities

def _run_city_batch_worker(job_id,cities,include_osm):
    results=[];err=None;status='running'
    # One municipal intelligence batch at a time. External reads may be slow, but this prevents
    # two batches from racing to rewrite the same municipality/source state.
    with CITY_SCAN_LOCK:
        try:
            c=db()
            with DB_WRITE_LOCK:
                c.execute('UPDATE city_scan_jobs SET started_at=?,status=? WHERE id=?',(now(),'running',job_id));c.commit()
            c.close()
            for city in cities:
                results.append(scan_city_intelligence(city,include_osm=include_osm))
                c=db()
                with DB_WRITE_LOCK:
                    c.execute('UPDATE city_scan_jobs SET summary_json=? WHERE id=?',(json.dumps(results,ensure_ascii=False),job_id));c.commit()
                c.close()
            status='done'
        except Exception as e:
            err=f'{type(e).__name__}: {e}';status='partial' if results else 'error'
        c=db()
        with DB_WRITE_LOCK:
            c.execute('UPDATE city_scan_jobs SET finished_at=?,status=?,summary_json=?,error=? WHERE id=?',(now(),status,json.dumps(results,ensure_ascii=False),err,job_id));c.commit()
        c.close()

def start_city_batch(cities,include_osm=True):
    cities=_prepare_city_batch(cities);ts=now()
    # Persist the job before spawning the worker. The client can poll immediately and IDs cannot collide.
    c=db()
    with DB_WRITE_LOCK:
        cur=database.insert_id(c,'INSERT INTO city_scan_jobs(created_at,status,municipalities_json,summary_json) VALUES(?,?,?,?)',(ts,'queued',json.dumps(cities,ensure_ascii=False),'[]'))
        job_id=int(cur);c.commit()
    c.close()
    launch(_run_city_batch_worker,(job_id,cities,include_osm))
    return {'ok':True,'job_id':job_id,'status':'queued','municipalities':cities}

def admin_ops_state():
    c=db();gaps=[dict(r) for r in c.execute('SELECT * FROM source_gaps ORDER BY attempts DESC, municipality')];ms=[dict(r) for r in c.execute('SELECT * FROM municipality_sources ORDER BY COALESCE(last_success,last_attempt) DESC, municipality LIMIT 500')];jobs=[dict(r) for r in c.execute('SELECT * FROM city_scan_jobs ORDER BY id DESC LIMIT 20')];attempts=[dict(r) for r in c.execute('SELECT * FROM source_attempts ORDER BY id DESC LIMIT 100')];c.close()
    return {'gaps':gaps,'municipality_sources':ms,'jobs':jobs,'attempts':attempts}



def _manual_radar(data):
    name=clean(data.get('name') or data.get('location') or 'Radar manual')
    municipality=clean(data.get('municipality') or '')
    if not municipality: raise RuntimeError('Município é obrigatório')
    lat=fnum(data.get('latitude')); lon=fnum(data.get('longitude'))
    speed=None
    try: speed=int(float(data.get('speed_limit'))) if str(data.get('speed_limit','')).strip() else None
    except: speed=None
    typ=clean(data.get('radar_type') or 'radar_fixo')
    ext=clean(data.get('external_id') or data.get('serial_number') or '')
    rid='manual-'+hashlib.sha1(f'{municipality}|{name}|{lat}|{lon}|{ext}'.encode()).hexdigest()[:16]
    seen=now(); item={
      'id':rid,'source':'admin_manual','external_id':ext or rid,'name':name,'latitude':lat,'longitude':lon,
      'speed_limit':speed,'speed_text':str(speed) if speed else None,'direction':clean(data.get('direction') or ''),
      'status':clean(data.get('status') or 'active'),'confidence':int(data.get('confidence') or 85),'municipality':municipality,
      'state':'SP','road':clean(data.get('road') or ''),'km':clean(data.get('km') or ''),'radar_type':typ,
      'der_number':None,'serial_number':clean(data.get('serial_number') or ''),'schedule':None,'study_url':None,
      'source_url':clean(data.get('source_url') or 'admin://manual'),'source_date':clean(data.get('source_date') or seen[:10]),
      'position_quality':'A' if lat is not None and lon is not None and data.get('official_coord') else ('C' if lat is not None and lon is not None else 'Pendente'),
      'inmetro_registration':clean(data.get('inmetro_registration') or ''),'lanes':None,'local_code':None,
      'quality_grade':clean(data.get('quality_grade') or 'manual'),'physical_radar_id':clean(data.get('physical_radar_id') or '') or None
    }
    c=db()
    with DB_WRITE_LOCK:
      res=upsert(c,item,seen)
      c.execute('INSERT INTO manual_entries(entry_type,entity_id,created_at,notes) VALUES(?,?,?,?)',('radar',rid,seen,clean(data.get('notes') or '')))
      c.commit()
    c.close(); _admin_event('manual_radar',f'Radar manual · {municipality} · {name}',{'id':rid,'result':res})
    return {'ok':True,'id':rid,'result':res}

def _manual_signal(data):
    municipality=clean(data.get('municipality') or '')
    if not municipality: raise RuntimeError('Município é obrigatório')
    lat=fnum(data.get('latitude')); lon=fnum(data.get('longitude'))
    name=clean(data.get('name') or data.get('location') or 'Semáforo manual')
    rid='manual-signal-'+hashlib.sha1(f'{municipality}|{name}|{lat}|{lon}'.encode()).hexdigest()[:16]
    seen=now(); item={'id':rid,'source':'admin_manual','external_id':rid,'object_type':'traffic_signal','name':name,'latitude':lat,'longitude':lon,'municipality':municipality,'state':'SP','status':clean(data.get('status') or 'active'),'confidence':int(data.get('confidence') or 80),'official':1 if data.get('official') else 0,'speed_limit':None,'direction':clean(data.get('direction') or ''),'timing_mode':clean(data.get('timing_mode') or 'unknown'),'cycle_seconds':fnum(data.get('cycle_seconds')),'green_seconds':fnum(data.get('green_seconds')),'red_seconds':fnum(data.get('red_seconds')),'adaptive':1 if data.get('adaptive') else 0,'timing_source':clean(data.get('timing_source') or ''),'source_url':clean(data.get('source_url') or 'admin://manual'),'source_date':clean(data.get('source_date') or seen[:10])}
    c=db()
    with DB_WRITE_LOCK:
      res=_upsert_road_object(c,item,seen)
      c.execute('INSERT INTO manual_entries(entry_type,entity_id,created_at,notes) VALUES(?,?,?,?)',('signal',rid,seen,clean(data.get('notes') or '')))
      c.commit()
    c.close(); _admin_event('manual_signal',f'Semáforo manual · {municipality} · {name}',{'id':rid,'result':res})
    return {'ok':True,'id':rid,'result':res}

def update_city_scope(city,mode='all',include_osm=True):
    city=clean(city); mode=clean(mode or 'all')
    if not city: raise RuntimeError('Município obrigatório')
    result={'municipality':city,'mode':mode,'started_at':now(),'steps':[],'errors':[]}
    if mode in ('all','radars'):
      try:
        x=scan_city_intelligence(city,include_osm=False); result['steps'].append({'kind':'radars','result':x})
      except Exception as e: result['errors'].append('radars: '+f'{type(e).__name__}: {e}')
    if mode in ('all','signals','objects'):
      try:
        x=sync_osm_objects_city(city) if include_osm else {'ok':True,'elements':0}; result['steps'].append({'kind':'signals_objects','result':x})
      except Exception as e: result['errors'].append('signals: '+f'{type(e).__name__}: {e}')
    ts=now(); c=db()
    with DB_WRITE_LOCK:
      c.execute('INSERT INTO municipality_profiles(municipality,last_radar_scan,last_signal_scan,last_full_scan) VALUES(?,?,?,?) ON CONFLICT(municipality) DO UPDATE SET last_radar_scan=CASE WHEN ? IN (\'all\',\'radars\') THEN excluded.last_radar_scan ELSE municipality_profiles.last_radar_scan END,last_signal_scan=CASE WHEN ? IN (\'all\',\'signals\',\'objects\') THEN excluded.last_signal_scan ELSE municipality_profiles.last_signal_scan END,last_full_scan=CASE WHEN ?=\'all\' THEN excluded.last_full_scan ELSE municipality_profiles.last_full_scan END',(city,ts,ts,ts,mode,mode,mode)); c.commit()
    c.close(); result['finished_at']=now(); result['counts']=_city_counts(city); result['ok']=not bool(result['errors']); _admin_event('city_update',f'Atualização {mode} · {city}',result); return result

def admin_inventory(city=''):
    c=db(); args=[]; wr=" WHERE state='SP'"; wor=" WHERE state='SP'"
    if city:
      wr+=' AND lower(municipality)=lower(?)'; wor+=' AND lower(municipality)=lower(?)'; args=[city]
    rad=[dict(r) for r in c.execute('SELECT id,name,municipality,radar_type,speed_limit,direction,status,position_quality,source,last_seen,inmetro_registration,serial_number,latitude,longitude FROM radars'+wr+' ORDER BY last_seen DESC LIMIT 500',args)]
    obj=[dict(r) for r in c.execute('SELECT id,name,municipality,object_type,status,timing_mode,adaptive,source,last_seen,latitude,longitude FROM road_objects'+wor+' ORDER BY last_seen DESC LIMIT 500',args)]
    prof=[dict(r) for r in c.execute('SELECT * FROM municipality_profiles ORDER BY municipality')]
    c.close(); return {'radars':rad,'objects':obj,'profiles':prof}


# --- v1.7 Operations / observability / discovery-first -----------------------
def ensure_v18_tables():
 if database.backend()=='sqlite':
  from db.sqlite_schema import upgrade
  return upgrade(sys.modules[__name__])

# backwards alias used by older self-tests/extensions
def ensure_v17_tables():
    return ensure_v18_tables()

def _opid(prefix='op'):
    return f'{prefix}-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}-{secrets.token_hex(3)}'

def _oplog(op_id,message,level='info',stage='',municipality='',source_id='',details=None):
    c=db()
    with DB_WRITE_LOCK:
        c.execute('INSERT INTO operation_logs(operation_id,created_at,level,stage,municipality,source_id,message,details) VALUES(?,?,?,?,?,?,?,?)',(op_id,now(),level,clean(stage),clean(municipality),clean(source_id),clean(message),json.dumps(details,ensure_ascii=False) if details is not None else None));c.commit()
    c.close()

def _queue_update(municipality,category,source_id,label,details=None):
    c=db();ts=now()
    with DB_WRITE_LOCK:
        exists=c.execute("SELECT id FROM update_queue WHERE municipality=? AND category=? AND source_id=? AND label=? AND status='pending'",(clean(municipality),clean(category),clean(source_id),clean(label))).fetchone()
        if not exists:c.execute("INSERT INTO update_queue(municipality,category,source_id,label,status,discovered_at,details) VALUES(?,?,?,?,'pending',?,?)",(clean(municipality),clean(category),clean(source_id),clean(label),ts,json.dumps(details,ensure_ascii=False) if details is not None else None))
        c.commit()
    c.close()

def update_queue_state(status='pending'):
    c=db();q='SELECT * FROM update_queue';args=[]
    if status:q+=' WHERE status=?';args=[status]
    q+=' ORDER BY id DESC LIMIT 300';rows=[dict(r) for r in c.execute(q,args)];c.close();return rows

def operation_logs_state(after=0,limit=250,operation_id=''):
    c=db();args=[int(after or 0)];q='SELECT * FROM operation_logs WHERE id>?'
    if clean(operation_id):q+=' AND operation_id=?';args.append(clean(operation_id))
    q+=' ORDER BY id ASC LIMIT ?';args.append(int(limit))
    rows=[dict(r) for r in c.execute(q,args)];c.close();return rows

def _known_connector_probe(city,op_id):
    norm=_norm_city(city);conn=KNOWN_CITY_CONNECTORS.get(norm)
    if not conn:return None
    sid,name,fn,url=conn;_oplog(op_id,f'Consultando disponibilidade de {name}',stage='fonte municipal',municipality=city,source_id=sid)
    try:
        raw,st,final,enc=http_request(url,headers={'User-Agent':UA,'Accept':'text/html,application/json,*/*'},timeout=12,attempts=2)
        _save_municipality_source(city,sid,name,url,'municipal_connector','available',True,0,0,f'HTTP {st}; fonte acessível')
        _record_source_attempt(city,sid,'available',0,0,f'HTTP {st}; descoberta sem importar',url)
        _queue_update(city,'radars',sid,f'Atualizar radares oficiais · {city}',{'source_name':name,'url':url})
        _oplog(op_id,'Fonte oficial acessível. Atualização adicionada à fila Alimentar base.',level='success',stage='fonte municipal',municipality=city,source_id=sid)
        return {'source_id':sid,'name':name,'status':'available','items':0,'mapped':0,'queued':True}
    except Exception as e:
        msg=f'{type(e).__name__}: {e}';_record_source_attempt(city,sid,'error',0,0,msg,url);_oplog(op_id,f'Fonte municipal indisponível: {msg}',level='error',stage='fonte municipal',municipality=city,source_id=sid);return {'source_id':sid,'name':name,'status':'error','error':msg}

def discover_osm_summary_city(municipality,op_id):
    _oplog(op_id,'Localizando limites municipais para descoberta complementar',stage='OSM',municipality=municipality,source_id='osm')
    south,west,north,east=_municipality_bbox(municipality)
    query=f'[out:json][timeout:35];(node["highway"="traffic_signals"]({south},{west},{north},{east});node["traffic_calming"]({south},{west},{north},{east});node["highway"="speed_camera"]({south},{west},{north},{east});node["enforcement"="maxspeed"]({south},{west},{north},{east}););out body;'
    data,st,endpoint=_overpass_request(query,timeout=55)
    els=(data.get('elements') or []);counts={'traffic_signal':0,'physical_bump':0,'speed_camera_candidate':0}
    for e in els:
        t=e.get('tags') or {}
        if t.get('highway')=='traffic_signals':counts['traffic_signal']+=1
        elif t.get('traffic_calming'):counts['physical_bump']+=1
        elif t.get('highway')=='speed_camera' or t.get('enforcement')=='maxspeed':counts['speed_camera_candidate']+=1
    total=sum(counts.values());_save_municipality_source(municipality,'osm_road_objects','OpenStreetMap · descoberta','https://www.openstreetmap.org/','community_discovery','candidate',False,total,total,json.dumps(counts,ensure_ascii=False));_record_source_attempt(municipality,'osm_road_objects','candidate',total,total,'descoberta sem importar: '+json.dumps(counts,ensure_ascii=False),'https://www.openstreetmap.org/')
    if total:_queue_update(municipality,'objects','osm_road_objects',f'Importar objetos viários descobertos · {municipality}',counts)
    _oplog(op_id,f'Descoberta: {counts["traffic_signal"]} semáforos, {counts["physical_bump"]} lombadas, {counts["speed_camera_candidate"]} câmeras/radares candidatos',level='success',stage='OSM',municipality=municipality,source_id='osm',details=counts)
    return {'source_id':'osm_road_objects','name':'OSM descoberta','status':'candidate','items':total,'mapped':total,'counts':counts,'queued':bool(total)}

def discover_city_intelligence(city,include_osm=True,op_id=None):
    city=clean(city);op_id=op_id or _opid('scan');result={'operation_id':op_id,'municipality':city,'sources':[],'errors':[],'mode':'discovery_only','counts_before':_city_counts(city)};_oplog(op_id,f'Iniciando varredura de {city}',stage='início',municipality=city)
    try:
        back=_probe_backbones(city);result['sources']+=back;_oplog(op_id,f'{len(back)} fonte(s) estaduais já presentes na base',level='success' if back else 'info',stage='base estadual',municipality=city,details=back)
    except Exception as e:result['errors'].append(str(e));_oplog(op_id,f'Falha ao verificar base estadual: {e}',level='error',stage='base estadual',municipality=city)
    p=_known_connector_probe(city,op_id)
    if p:result['sources'].append(p)
    try:
        _oplog(op_id,'Pesquisando catálogos oficiais de dados abertos',stage='catálogos',municipality=city);leads=_official_open_data_scout(city);result['sources']+=leads;_oplog(op_id,f'{len(leads)} pista(s) de fonte oficial encontradas',level='success' if leads else 'info',stage='catálogos',municipality=city,details=leads)
        for x in leads:_queue_update(city,'investigate',x.get('source_id','catalog'),f'Revisar fonte candidata · {x.get("name") or city}',x)
    except Exception as e:result['errors'].append('catalog:'+str(e));_oplog(op_id,f'Falha nos catálogos: {e}',level='error',stage='catálogos',municipality=city)
    try:
        sig=discover_official_signals_city(city,op_id)
        if sig:result['sources'].append(sig)
    except Exception as e:
        result['errors'].append('signals-official:'+str(e));_oplog(op_id,f'Falha na fonte oficial de semáforos: {e}',level='error',stage='semáforos oficiais',municipality=city)
    if include_osm:
        try:result['sources'].append(discover_osm_summary_city(city,op_id))
        except Exception as e:result['errors'].append('OSM:'+str(e));_oplog(op_id,f'Falha na descoberta OSM: {e}',level='error',stage='OSM',municipality=city)
    result['counts_after']=_city_counts(city);has_source=any(x.get('status') in ('confirmed','available') for x in result['sources']) or result['counts_after']['radars']>0
    if has_source:_clear_gap(city)
    else:_set_gap(city,'Varredura não encontrou fonte oficial importável confirmada. Mantido na fila de investigação.')
    result['status']='ready_to_update' if has_source else ('discovery_only' if any(x.get('items',0) for x in result['sources']) else 'needs_source');_admin_event('city_discovery',f'Varredura (sem alterar base pública) · {city}',result);_oplog(op_id,f'Varredura concluída · {result["status"]}. Nada foi importado automaticamente.',level='success',stage='fim',municipality=city);return result

def _run_city_batch_worker_v17(job_id,cities,include_osm):
    op_id=f'batch-{job_id}'
    try:
        with CITY_BATCH_LOCK:
            results=[];c=db()
            with DB_WRITE_LOCK:c.execute('UPDATE city_scan_jobs SET status=?,started_at=? WHERE id=?',('running',now(),job_id));c.commit()
            c.close();_oplog(op_id,f'Rodada #{job_id} iniciada com {len(cities)} cidade(s)',stage='batch')
            for idx,city in enumerate(cities,1):
                _oplog(op_id,f'[{idx}/{len(cities)}] Varredura de {city}',stage='batch',municipality=city)
                try:results.append(discover_city_intelligence(city,include_osm,op_id))
                except Exception as e:results.append({'municipality':city,'status':'error','error':f'{type(e).__name__}: {e}'});_oplog(op_id,f'Erro em {city}: {e}',level='error',stage='batch',municipality=city)
            c=db();fin=now()
            with DB_WRITE_LOCK:c.execute('UPDATE city_scan_jobs SET status=?,finished_at=?,result_json=? WHERE id=?',('done',fin,json.dumps(results,ensure_ascii=False),job_id));c.commit()
            c.close();_oplog(op_id,f'Rodada #{job_id} concluída. Revise Alimentar base.',level='success',stage='batch')
    except Exception as e:
        c=db()
        with DB_WRITE_LOCK:c.execute('UPDATE city_scan_jobs SET status=?,finished_at=?,result_json=? WHERE id=?',('error',now(),json.dumps({'error':f'{type(e).__name__}: {e}'},ensure_ascii=False),job_id));c.commit()
        c.close();_oplog(op_id,f'Rodada #{job_id} falhou: {e}',level='error',stage='batch')

def start_city_batch_v17(cities,include_osm=True):
    cities=_prepare_city_batch(cities);c=db();ts=now()
    with DB_WRITE_LOCK:
        jid=database.insert_id(c,'INSERT INTO city_scan_jobs(created_at,status,municipalities_json,include_osm,result_json) VALUES(?,?,?,?,?)',(ts,'queued',json.dumps(cities,ensure_ascii=False),1 if include_osm else 0,None));c.commit()
    c.close();launch(_run_city_batch_worker_v17,(jid,cities,include_osm))
    status='queued'
    if hosted():
        with db() as c:status=c.execute('SELECT status FROM city_scan_jobs WHERE id=?',(jid,)).fetchone()[0]
    return {'ok':status in ('queued','done'),'job_id':jid,'status':status,'municipalities':cities,'operation_id':f'batch-{jid}'}


def queue_state_updates(selected):
    selected=[clean(x) for x in (selected or []) if clean(x)]
    op_id=_opid('state-plan');added=[]
    catalog={
      'antt_sp':('state_radars','Atualizar ANTT · radares de rodovias concedidas'),
      'der_sp':('state_radars','Atualizar DER-SP · radares e malha rodoviária'),
    }
    _oplog(op_id,f'Preparando {len(selected)} atualização(ões) estaduais para aprovação',stage='planejamento')
    for sid in selected:
        if sid not in catalog:continue
        cat,label=catalog[sid];_queue_update('',cat,sid,label,{'scope':'Estado de São Paulo','requires_approval':True});added.append({'source_id':sid,'label':label});_oplog(op_id,f'Adicionado à fila: {label}',level='success',stage='fila',source_id=sid)
    return {'ok':True,'operation_id':op_id,'queued':added}

def discover_city_targeted(city,mode='all',include_osm=True,op_id=None):
    city=clean(city);mode=clean(mode or 'all');op_id=op_id or _opid('city-check')
    if not city:raise RuntimeError('Município obrigatório')
    result={'operation_id':op_id,'municipality':city,'mode':mode,'sources':[],'errors':[],'counts_before':_city_counts(city)}
    _oplog(op_id,f'Inspeção direcionada iniciada · {city} · {mode}',stage='início',municipality=city)
    if mode in ('all','radars'):
        try:
            back=_probe_backbones(city);result['sources']+=back;_oplog(op_id,f'Base estadual: {len(back)} fonte(s) já presentes',level='success' if back else 'info',stage='radares',municipality=city,details=back)
        except Exception as e:result['errors'].append(str(e));_oplog(op_id,f'Erro na base estadual: {e}',level='error',stage='radares',municipality=city)
        p=_known_connector_probe(city,op_id)
        if p:result['sources'].append(p)
        try:
            leads=_official_open_data_scout(city);result['sources']+=leads
            for x in leads:_queue_update(city,'investigate',x.get('source_id','catalog'),f'Revisar fonte candidata · {x.get("name") or city}',x)
            _oplog(op_id,f'Catálogos oficiais: {len(leads)} pista(s)',level='success' if leads else 'info',stage='catálogos',municipality=city,details=leads)
        except Exception as e:result['errors'].append('catalog:'+str(e));_oplog(op_id,f'Erro nos catálogos: {e}',level='error',stage='catálogos',municipality=city)
    if mode in ('all','signals','objects'):
        try:
            sig=discover_official_signals_city(city,op_id)
            if sig:result['sources'].append(sig)
        except Exception as e:
            result['errors'].append('signals-official:'+str(e));_oplog(op_id,f'Falha na fonte oficial de semáforos: {e}',level='error',stage='semáforos oficiais',municipality=city)
    if mode in ('all','signals','objects') and include_osm:
        try:result['sources'].append(discover_osm_summary_city(city,op_id))
        except Exception as e:result['errors'].append('OSM:'+str(e));_oplog(op_id,f'Falha em semáforos/lombadas/câmeras: {e}',level='error',stage='OSM',municipality=city)
    result['counts_after']=_city_counts(city);result['queued']=len([x for x in update_queue_state('pending') if (x.get('municipality') or '').lower()==city.lower()])
    _oplog(op_id,f'Inspeção concluída · {result["queued"]} atualização(ões) pendente(s) para {city}',level='success',stage='fim',municipality=city,details=result)
    return result

def start_target_city_discovery(city,mode='all',include_osm=True):
    city=clean(city);mode=clean(mode or 'all')
    if not city:raise RuntimeError('Município obrigatório')
    op_id=_opid('city-check')
    def work():
        try:return discover_city_targeted(city,mode,include_osm,op_id)
        except Exception as e:_oplog(op_id,f'Falha na inspeção: {type(e).__name__}: {e}',level='error',stage='fim',municipality=city);return {'ok':False,'operation_id':op_id,'error':'City discovery failed; inspect operation logs'}
    if hosted():return launch(work)
    launch(work)
    return {'ok':True,'operation_id':op_id,'municipality':city,'mode':mode,'status':'running'}

def _apply_one_update(row,op_id):
    city=row['municipality'];sid=row['source_id'];cat=row['category'];_oplog(op_id,f'Aplicando: {row["label"]}',stage='aplicação',municipality=city,source_id=sid)
    if sid in ('santo_andre','santos','praia_grande'):res=KNOWN_CITY_CONNECTORS[_norm_city(city)][2](True)
    elif sid=='osm_road_objects':res=sync_osm_objects_city(city)
    elif sid=='geosampa_signals':res=_sync_official_signal_wfs('São Paulo','geosampa_signals','GeoSampa · Cruzamentos Semaforizados',GEOSAMPA_WFS,['semaforo','cruzamentos semaforizados'])
    elif sid=='santos_signals_wfs':res=_sync_official_signal_wfs('Santos','santos_signals_wfs','SIGSantos · Semáforos',SANTOS_WFS,['semaforo','sinalizacao semaforica'])
    elif sid=='antt_sp':res=sync_antt_sp()
    elif sid=='der_sp':res=start('full','')
    elif cat=='investigate':res={'ok':True,'note':'Fonte candidata mantida para revisão manual; nenhum dado importado.'}
    else:raise RuntimeError(f'Atualização sem executor: {sid}/{cat}')
    _oplog(op_id,f'Concluído: {row["label"]}',level='success',stage='aplicação',municipality=city,source_id=sid,details=res);return res

def apply_update_decisions(data):
    decisions=data.get('decisions') or [];op_id=_opid('feed');results=[];_oplog(op_id,f'Iniciando alimentação da base · {len(decisions)} decisão(ões)',stage='início');c=db()
    for d in decisions:
        uid=int(d.get('id'));decision=clean(d.get('decision') or 'skip');rr=c.execute('SELECT * FROM update_queue WHERE id=?',(uid,)).fetchone()
        if not rr:continue
        row=dict(rr)
        if decision not in ('yes','apply'):
            with DB_WRITE_LOCK:c.execute('UPDATE update_queue SET status=? WHERE id=?',('rejected',uid));c.commit()
            _oplog(op_id,f'Ignorado: {row["label"]}',level='warning',stage='decisão',municipality=row['municipality'],source_id=row['source_id']);results.append({'id':uid,'status':'rejected'});continue
        try:
            res=_apply_one_update(row,op_id)
            with DB_WRITE_LOCK:c.execute('UPDATE update_queue SET status=?,applied_at=? WHERE id=?',('applied',now(),uid));c.commit()
            results.append({'id':uid,'status':'applied','result':res})
        except Exception as e:_oplog(op_id,f'Falha ao aplicar {row["label"]}: {e}',level='error',stage='aplicação',municipality=row['municipality'],source_id=row['source_id']);results.append({'id':uid,'status':'error','error':f'{type(e).__name__}: {e}'})
    c.close();_oplog(op_id,'Alimentação da base concluída',level='success',stage='fim',details=results);return {'ok':not any(x.get('status')=='error' for x in results),'operation_id':op_id,'results':results}

def _mark_assistant_provenance(municipality,batch_id,sources=None,note=''):
    c=db();args=[ASSISTANT_ACTOR,batch_id,note,municipality];q='UPDATE road_objects SET ingested_by=?,ingestion_batch=?,provenance_note=? WHERE lower(municipality)=lower(?)'
    if sources:q+=' AND source IN ('+','.join('?' for _ in sources)+')';args+=list(sources)
    with DB_WRITE_LOCK:n=c.execute(q,args).rowcount;c.commit()
    c.close();return n

def _assistant_seed_official_crossings(batch_id,municipality=None,op_id=''):
    seeds=[x for x in ASSISTANT_OFFICIAL_SIGNAL_SEEDS if not municipality or _norm_city(x['municipality'])==_norm_city(municipality)];seen=now();results=[];c=db()
    for row in seeds:
        city=row['municipality'];name=row['name'];coords=geocode_text(f'{name}, {city}, SP, Brasil',3);lat=lon=None;provider=''
        if coords:hit=coords[0];lat,lon=hit['lat'],hit['lon'];provider=hit.get('provider','')
        ext=hashlib.sha1(f"{row['source_id']}|{city}|{name}".encode()).hexdigest()[:18]
        item={'id':f'assistant-official:{ext}','source':row['source_id'],'external_id':ext,'object_type':'traffic_signal','name':name,'latitude':lat,'longitude':lon,'municipality':city,'state':'SP','status':'active' if lat is not None else 'inventory','confidence':88 if lat is not None else 80,'official':1,'speed_limit':None,'direction':None,'timing_mode':'unknown','cycle_seconds':None,'green_seconds':None,'red_seconds':None,'adaptive':0,'timing_source':'Prefeitura / publicação oficial','source_url':row['source_url'],'source_date':row['source_date'],'ingested_by':ASSISTANT_ACTOR,'ingestion_batch':batch_id,'provenance_note':f'Endereço/cruzamento publicado oficialmente; coordenada geocodificada por {provider or "pendente"}. Alimentado por {ASSISTANT_ACTOR}.'}
        with DB_WRITE_LOCK:r=_upsert_road_object(c,item,seen);c.commit()
        results.append({'municipality':city,'name':name,'status':r,'mapped':lat is not None,'provider':provider})
        if op_id:_oplog(op_id,f'Semente oficial: {name} · '+('mapeado' if lat is not None else 'sem coordenada'),level='success' if lat is not None else 'warning',stage='semente oficial',municipality=city,source_id=row['source_id'],details=results[-1])
    c.close();return results

def assistant_pack_state():
    ensure_v18_tables();c=db();run=c.execute('SELECT * FROM assistant_update_runs WHERE batch_id=?',(ASSISTANT_SIGNAL_BATCH,)).fetchone();counts=[]
    for city in ASSISTANT_SIGNAL_CITIES:
        r=c.execute("SELECT COUNT(*) n,SUM(CASE WHEN object_type='traffic_signal' THEN 1 ELSE 0 END) signals,SUM(CASE WHEN ingested_by=? THEN 1 ELSE 0 END) mine FROM road_objects WHERE lower(municipality)=lower(?)",(ASSISTANT_ACTOR,city)).fetchone();counts.append({'municipality':city,'objects':r['n'] or 0,'signals':r['signals'] or 0,'by_chatgpt':r['mine'] or 0})
    c.close();return {'batch_id':ASSISTANT_SIGNAL_BATCH,'actor':ASSISTANT_ACTOR,'targets':ASSISTANT_SIGNAL_CITIES,'run':dict(run) if run else None,'cities':counts}

def run_assistant_signal_pack(force=False):
    ensure_v18_tables();c=db();old=c.execute('SELECT status FROM assistant_update_runs WHERE batch_id=?',(ASSISTANT_SIGNAL_BATCH,)).fetchone();c.close()
    if old and old['status']=='done' and not force:return {'ok':True,'skipped':True,**assistant_pack_state()}
    op_id='assistant-'+ASSISTANT_SIGNAL_BATCH;started=now();summary=[];errors=[];c=db()
    with DB_WRITE_LOCK:c.execute(database.upsert_statement('INSERT INTO assistant_update_runs(batch_id,actor,started_at,finished_at,status,targets_json,summary_json,error) VALUES(?,?,?,?,?,?,?,?)'),(ASSISTANT_SIGNAL_BATCH,ASSISTANT_ACTOR,started,None,'running',json.dumps(ASSISTANT_SIGNAL_CITIES,ensure_ascii=False),None,None));c.commit()
    c.close();_oplog(op_id,'Lote ChatGPT/OpenAI iniciado: semáforos da Baixada Santista + São Bernardo',stage='assistant',details={'targets':ASSISTANT_SIGNAL_CITIES})
    try:_assistant_seed_official_crossings(ASSISTANT_SIGNAL_BATCH,op_id=op_id)
    except Exception as e:errors.append('official-seeds:'+str(e));_oplog(op_id,f'Falha nas sementes oficiais: {e}',level='error',stage='assistant')
    for idx,city in enumerate(ASSISTANT_SIGNAL_CITIES,1):
        row={'municipality':city};_oplog(op_id,f'[{idx}/{len(ASSISTANT_SIGNAL_CITIES)}] Alimentando {city}',stage='assistant',municipality=city)
        try:
            if _norm_city(city)=='santos':
                try:
                    off=_sync_official_signal_wfs('Santos','santos_signals_wfs','SIGSantos · Semáforos',SANTOS_WFS,['semaforo','sinalizacao semaforica']);_mark_assistant_provenance('Santos',ASSISTANT_SIGNAL_BATCH,['santos_signals_wfs'],'Importado da fonte municipal oficial pelo lote ChatGPT/OpenAI.');row['official']=off
                except Exception as e:row['official_error']=f'{type(e).__name__}: {e}'
            if _norm_city(city)=='sao bernardo do campo':_save_municipality_source(city,'sbcgeo','SBCGEO · São Bernardo do Campo',SBCGEO_URL,'official_geoportal','available',True,0,0,'Portal municipal de dados geoespaciais públicos; lote ChatGPT usa OSM como complemento enquanto a camada semafórica específica é validada.')
            osm=sync_osm_objects_city(city,ingested_by=ASSISTANT_ACTOR,ingestion_batch=ASSISTANT_SIGNAL_BATCH,provenance_note='Descoberta complementar OpenStreetMap alimentada pelo ChatGPT/OpenAI; não classificada como fonte oficial.',strict_area=True);row['osm']=osm
            _mark_assistant_provenance(city,ASSISTANT_SIGNAL_BATCH,['osm_road_objects'],'Descoberta complementar OSM alimentada pelo ChatGPT/OpenAI; fonte comunitária.')
            _oplog(op_id,f'{city}: {osm.get("counts",{}).get("traffic_signal",0)} semáforos OSM carregados',level='success',stage='assistant',municipality=city,source_id='osm_road_objects',details=osm)
        except Exception as e:row['error']=f'{type(e).__name__}: {e}';errors.append(city+':'+row['error']);_oplog(op_id,f'{city}: falha {row["error"]}',level='error',stage='assistant',municipality=city)
        summary.append(row)
    status='done' if not errors else ('partial' if summary else 'error');finished=now();c=db()
    with DB_WRITE_LOCK:c.execute('UPDATE assistant_update_runs SET finished_at=?,status=?,summary_json=?,error=? WHERE batch_id=?',(finished,status,json.dumps(summary,ensure_ascii=False),'; '.join(errors) if errors else None,ASSISTANT_SIGNAL_BATCH));c.commit()
    c.close();_oplog(op_id,f'Lote ChatGPT/OpenAI concluído · {status}',level='success' if status=='done' else 'warning',stage='assistant',details={'errors':errors,'summary':summary});return {'ok':status!='error','status':status,'batch_id':ASSISTANT_SIGNAL_BATCH,'summary':summary,'errors':errors}

def start_assistant_signal_pack(force=False):
    if hosted():return launch(lambda:run_assistant_signal_pack(force))
    state=assistant_pack_state();run=state.get('run') or {}
    if not hosted() and run.get('status')=='running':return {'ok':True,'status':'running','batch_id':ASSISTANT_SIGNAL_BATCH}
    launch(lambda:run_assistant_signal_pack(force));return {'ok':True,'status':'started','batch_id':ASSISTANT_SIGNAL_BATCH,'actor':ASSISTANT_ACTOR}


LEGACY_MUTATIONS={'/api/sync/praia-grande','/api/sync/santos','/api/sync/santo-andre','/api/sync/der/start','/api/georef/der/start'}

def health_status():
 result={'ok':False,'app':'ok','database':'unavailable','engine':'unconfigured','environment':environment(),'version':'2.2.0','time':now()}
 try:
  result['engine']=database.backend()
  with db() as c:result.update(database.status(c))
  result['ok']=not bool(AUTH.configuration_errors())
  if not result['ok']:
   result['configuration']='Admin environment incomplete';result['configuration_errors']=AUTH.configuration_errors()
 except database.DatabaseConfigurationError as error:result['configuration_errors']=[str(error)]
 except Exception as error:
  __import__('logging').getLogger('relas.api').error('health_database_unavailable error_type=%s',type(error).__name__)
 return result

def runtime_sync_state(kind,local):
 return runtime_jobs.state(sys.modules[__name__],kind) if hosted() else local

def launch(callback,args=()):
 if hosted():
  runtime_jobs.check()
  if runtime_jobs.deadline.get() is None:raise RuntimeError('Hosted jobs require a request-bound executor')
  return callback(*args)
 threading.Thread(target=callback,args=args,daemon=True).start()

class H(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(APP_DIR),**kw)
 def log_message(self,fmt,*args):sys.stdout.write('[HTTP] '+fmt%args+'\n')
 def end_headers(self):
  if self.path.startswith(('/admin','/api/admin','/sw.js','/boot.js','/index.html','/navigation-core.js')) or urlparse(self.path).path in ('/',''):
   self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
   self.send_header('Pragma','no-cache')
  super().end_headers()
 def js(self,o,status=200,extra_headers=None):
  b=json.dumps(o,ensure_ascii=False,indent=2).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');
  for k,v in (extra_headers or {}).items():self.send_header(k,v)
  self.end_headers()
  try:self.wfile.write(b)
  except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
 def _body_json(self):
  try:
   n=int(self.headers.get('Content-Length','0') or 0);return json.loads(self.rfile.read(n).decode('utf-8')) if n else {}
  except:return {}
 def do_POST(self):
  p=urlparse(self.path)
  from road_data import api as road_api
  if road_api.handles(p.path):return road_api.dispatch(sys.modules[__name__],self,p.path,parse_qs(p.query),'POST')
  if p.path.startswith("/api/map/") or p.path.startswith("/api/admin/community/"):
   if p.path.startswith("/api/admin/") and not _admin_authed_v15(self):return self.js({"error":"n?o autorizado"},401)
   try:
    if int(self.headers.get('Content-Length','0'))>2097152:return self.js({'error':'request too large'},413)
   except ValueError:return self.js({'error':'invalid content length'},400)
   try:return self.js(community.post(sys.modules[__name__],self,p.path,self._body_json()))
   except (ValueError,KeyError,TypeError) as e:return self.js({"error":str(e)},400)
  if p.path=='/api/admin/login':
   data=self._body_json()
   if AUTH.configuration_errors():return self.js({'ok':False,'error':'Admin environment is incomplete'},503)
   if AUTH.password_valid(data.get('username',''),data.get('password','')):
    tok=AUTH.issue();_admin_event('auth','Login admin efetuado');return self.js({'ok':True,'token':tok,'user':ADMIN_USER},extra_headers={'Set-Cookie':AUTH.cookie(tok)})
   return self.js({'ok':False,'error':'Usuário ou senha inválidos'},401)
  if p.path=='/api/admin/logout':
   return self.js({'ok':True},extra_headers={'Set-Cookie':AUTH.cookie(logout=True)})
  if p.path.startswith('/api/admin/') and not _admin_authed_v15(self):return self.js({'ok':False,'error':'não autorizado'},401)
  if p.path=='/api/admin/sync/municipalities':
   try:
    r=sync_municipalities_ibge();return self.js(r,200 if r.get('ok') or r.get('cached') else 503)
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}','message':'Falha ao atualizar municípios e não há cache local.'},503)
  if p.path=='/api/admin/sync/antt':
   try:return self.js(sync_antt_sp())
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}'},500)
  if p.path=='/api/admin/sync/santo-andre':return self.js(seed_santo_andre(True))
  if p.path=='/api/admin/sync/praia-grande':return self.js(seed_praia_grande(True))
  if p.path=='/api/admin/sync/santos':return self.js(seed_santos(True))
  if p.path=='/api/admin/sync/der':return self.js(start('full',''))
  if p.path=='/api/admin/georef/der':return self.js(georef_inventory(bool(self._body_json().get('force',False))))
  if p.path=='/api/admin/sync/osm-city':
   try:
    data=self._body_json();return self.js(sync_osm_objects_city(data.get('municipality','')))
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}'},500)
  if p.path=='/api/admin/batch-scan':
   try:
    data=self._body_json();cities=data.get('municipalities') or [];return self.js(start_city_batch_v17(cities, bool(data.get('include_osm',True))))
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}'},500)
  if p.path=='/api/admin/manual/radar':
   try:return self.js(_manual_radar(self._body_json()))
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}'},400)
  if p.path=='/api/admin/manual/signal':
   try:return self.js(_manual_signal(self._body_json()))
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}'},400)
  if p.path=='/api/admin/apply-updates':
   try:return self.js(apply_update_decisions(self._body_json()))
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}'},500)
  if p.path=='/api/admin/queue-state-updates':
   try:return self.js(queue_state_updates((self._body_json() or {}).get('sources') or []))
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}'},500)
  if p.path=='/api/admin/assistant-pack/run':
   try:return self.js(start_assistant_signal_pack(bool((self._body_json() or {}).get('force',False))))
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}'},500)
  if p.path=='/api/admin/update-city':
   try:
    data=self._body_json();return self.js(start_target_city_discovery(data.get('municipality',''),data.get('mode','all'),bool(data.get('include_osm',True))))
   except Exception as e:return self.js({'ok':False,'error':f'{type(e).__name__}: {e}'},500)
  return self.js({'ok':False,'error':'endpoint não encontrado'},404)
 def do_GET(self):
  p=urlparse(self.path);q=parse_qs(p.query)
  from road_data import api as road_api
  if road_api.handles(p.path):return road_api.dispatch(sys.modules[__name__],self,p.path,q,'GET')
  if p.path in LEGACY_MUTATIONS and not _admin_authed_v15(self):return self.js({'error':'Admin authentication required'},401)
  if hosted() and p.path in LEGACY_MUTATIONS:return self.js({'error':'Use Admin POST operations'},405)
  if p.path in ['/api/map/features','/api/admin/community','/api/admin/community/export']:
   if p.path.startswith('/api/admin/') and not _admin_authed_v15(self):return self.js({'error':'não autorizado'},401)
   try:return self.js(community.features(sys.modules[__name__],q,True) if p.path.endswith('/export') else community.summary(sys.modules[__name__],q) if p.path.startswith('/api/admin/') else community.features(sys.modules[__name__],q))
   except (ValueError,TypeError) as e:return self.js({'error':str(e)},400)
  if p.path=='/favicon.ico':
   self.path='/icon.svg';return super().do_GET()
  if p.path=='/admin':
   self.path='/admin.html';return super().do_GET()
  if p.path=='/api/admin/me':return self.js({'ok':_admin_authed_v15(self),'user':ADMIN_USER if _admin_authed_v15(self) else None})
  if p.path.startswith('/api/admin/'):
   if not _admin_authed_v15(self):return self.js({'ok':False,'error':'não autorizado'},401)
   if p.path=='/api/admin/database-status':
    with db() as c:return self.js(dict(database.status(c),environment=environment()))
   if p.path=='/api/admin/jobs' and hosted():
    with db() as c:return self.js({'items':[dict(r) for r in c.execute('SELECT * FROM runtime_jobs ORDER BY started_at DESC LIMIT 100')]})
   if p.path=='/api/admin/dashboard':return self.js(state_intelligence_dashboard())
   if p.path=='/api/admin/coverage':return self.js({'items':municipality_coverage()})
   if p.path=='/api/admin/sources':return self.js({'items':source_registry_state()})
   if p.path=='/api/admin/ops':return self.js(admin_ops_state())
   if p.path=='/api/admin/inventory':return self.js(admin_inventory((q.get('city') or [''])[0]))
   if p.path=='/api/admin/update-queue':return self.js({'items':update_queue_state((q.get('status') or ['pending'])[0])})
   if p.path=='/api/admin/logs':return self.js({'items':operation_logs_state(int((q.get('after') or ['0'])[0] or 0),250,(q.get('operation') or [''])[0])})
   if p.path=='/api/admin/assistant-pack':return self.js(assistant_pack_state())
  if p.path=='/api/road-objects':return self.js({'items':get_road_objects((q.get('mapped') or ['1'])[0]!='0')})
  if p.path=='/api/signal-networks':return self.js({'items':signal_network_state()})
  if p.path=='/api/health':
   status=health_status();return self.js(status,200 if status['ok'] else 503)
  if p.path=='/api/access' and hosted():return self.js({'local':'/','lan':None,'note':'HTTPS e permissao de localizacao necessarios.'})
  if p.path=='/api/access':return self.js({'local':f'{"https" if os.environ.get("RELAS_TLS_CERT") else "http"}://127.0.0.1:{PORT}/?v=220','lan':f'{"https" if os.environ.get("RELAS_TLS_CERT") else "http"}://{lan_ip()}:{PORT}/?v=220','note':'GPS no telefone requer HTTPS confiável e permissão de localização.'})
  if p.path=='/api/vendor/status':return self.js(ensure_maplibre_assets())
  if p.path=='/api/diagnostics':return self.js(stability_diagnostics())
  if p.path=='/api/autocomplete':
   try:
    qq=(q.get('q') or [''])[0];lat=(q.get('lat') or [None])[0];lon=(q.get('lon') or [None])[0]
    lat=float(lat) if lat not in (None,'') else None;lon=float(lon) if lon not in (None,'') else None
    return self.js({'items':autocomplete_text(qq,lat,lon,7,(q.get('submitted') or ['0'])[0]=='1')})
   except Exception as e:
    __import__('logging').getLogger('relas.api').error('autocomplete_failed error_type=%s',type(e).__name__)
    return self.js({'items':[],'error':'Autocomplete temporarily unavailable'},503)
  if p.path=='/api/geocode':
   try:return self.js({'items':geocode_text((q.get('q') or [''])[0],5)})
   except Exception as e:
    __import__('logging').getLogger('relas.api').error('geocode_failed error_type=%s',type(e).__name__)
    return self.js({'items':[],'error':'Geocoding temporarily unavailable'},503)
  if p.path=='/api/route':
   try:
    vals=[float((q.get(k) or [''])[0]) for k in ('flat','flon','tlat','tlon')];return self.js(build_route(*vals))
   except Exception as e:
    __import__('logging').getLogger('relas.api').error('route_failed error_type=%s',type(e).__name__)
    return self.js({'error':'Route calculation temporarily unavailable'},503)
  if p.path=='/api/sync/praia-grande':return self.js(seed_praia_grande(True))
  if p.path=='/api/sync/santos':return self.js(seed_santos(True))
  if p.path=='/api/radars':return self.js({'items':get_radars(False),'demo':False})
  if p.path=='/api/radars/mapped':return self.js({'items':get_radars(True),'demo':False})
  if p.path=='/api/stats':return self.js(get_stats())
  if p.path=='/api/sources':return self.js({'items':get_sources()})
  if p.path=='/api/sync/state':return self.js(runtime_sync_state('der',SYNC))
  if p.path=='/api/sync/baixada/state':return self.js(runtime_sync_state('baixada',BAIXADA_SYNC))
  if p.path=='/api/sync/santo-andre':return self.js(seed_santo_andre(True))
  if p.path=='/api/sync/der/start':return self.js(start((q.get('mode') or ['sample'])[0],(q.get('road') or [''])[0]))
  if p.path=='/api/der/diagnostic':return self.js(diagnostic())
  if p.path=='/api/roads/status':return self.js(road_network_status())
  if p.path=='/api/georef/der/start':
   def _run_geo():
    try:
     SYNC.update({'running':True,'message':'Baixando/validando malha oficial DER…','error':None});r=georef_inventory((q.get('force') or ['0'])[0]=='1');SYNC.update({'running':False,'message':f'Georreferenciamento: {r["mapped_total"]} radares no mapa; {r["unmatched"]} sem correspondência.','mapped':r['mapped_total'],'derived':r['mapped_now']})
    except Exception as e:SYNC.update({'running':False,'message':'Falha no georreferenciamento','error':f'{type(e).__name__}: {e}'})
   launch(_run_geo);return self.js({'status':'started'})
  if p.path.startswith('/api/'):return self.js({'error':'Endpoint not found'},404)
  return super().do_GET()

import community

def configure_server_tls(srv):
 cert,key=os.environ.get('RELAS_TLS_CERT'),os.environ.get('RELAS_TLS_KEY')
 if bool(cert)!=bool(key):raise ValueError('RELAS_TLS_CERT e RELAS_TLS_KEY precisam ser configurados juntos')
 if cert:
  context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
  srv.socket=context.wrap_socket(srv.socket,server_side=True)
  print('HTTPS ativo; o certificado deve ser confiável no telefone.')

def main(open_browser=True):
 if hosted():raise RuntimeError('Hosted mode imports server:app; do not start an HTTPServer')
 if database.backend()=='sqlite':
  init_db();ensure_v18_tables();community.init(sys.modules[__name__]);seed_signal_networks();seed_santo_andre(False);seed_praia_grande(False);seed_santos(False);community.bootstrap_public_data(sys.modules[__name__]);refresh_physical_ids();checkpoint_db()
 srv=ThreadingHTTPServer(('0.0.0.0',PORT),H);configure_server_tls(srv);lip=lan_ip();print('Relas v2.2.0 - local / Neon');print('Senha Admin: RELAS_ADMIN_PASSWORD ou arquivo local',USER_DATA_DIR/'admin_password.txt');scheme='https' if os.environ.get('RELAS_TLS_CERT') else 'http';print(f'PC -> {scheme}://127.0.0.1:{PORT}/?v=220');print(f'Celular na mesma rede -> {scheme}://{lip}:{PORT}/?v=220');print('Sincronização pesada municipal: manual pelo Admin (evita travar o banco no startup)');print('MapLibre local:', 'OK' if MAPLIBRE_JS.exists() and MAPLIBRE_CSS.exists() else 'cache ainda não preenchido · fallback CDN ativo')
 def _warm_vendor():
  vend=ensure_maplibre_assets()
  print('MapLibre cache:', 'OK' if vend['js'].get('ok') and vend['css'].get('ok') else 'indisponível; navegador usará fallback CDN')
  if not (vend['js'].get('ok') and vend['css'].get('ok')):print('Detalhes vendor:',json.dumps(vend,ensure_ascii=False))
 threading.Thread(target=_warm_vendor,daemon=True).start()
 if database.backend()=='sqlite':threading.Timer(1.2,lambda:start_assistant_signal_pack(False)).start()
 if open_browser:threading.Timer(.6,lambda:webbrowser.open(f'{scheme}://127.0.0.1:{PORT}/?v=220')).start()
 try:srv.serve_forever()
 except KeyboardInterrupt:pass
from web_app import create_app
app=create_app(sys.modules[__name__])

if __name__=='__main__':main()
