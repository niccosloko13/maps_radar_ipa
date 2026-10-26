import json,unittest
from urllib.parse import urlparse,parse_qs
from navigation_backend import address_query,search_address,instruction_pt,route_step


class NavigationBackendTests(unittest.TestCase):
 def test_rui_barbosa_exact_street_wins_and_missing_number_stays_on_street(self):
  features=[
   {'geometry':{'coordinates':[-46.41,-24.01]},'properties':{'street':'Rua Rui Barbosa','housenumber':'521','city':'Praia Grande','state':'Sao Paulo'}},
   {'geometry':{'coordinates':[-46.42,-24.01]},'properties':{'street':'Rua Barbosa','housenumber':'521','city':'Praia Grande','state':'Sao Paulo'}},
   {'geometry':{'coordinates':[-46.43,-24.01]},'properties':{'street':'Rua Rui Barbosa','city':'Praia Grande','state':'Sao Paulo'}},
  ]
  def http(*args,**kwargs):return json.dumps({'features':features}).encode(),200,{},None
  for number in ('198','521','818'):
   row=search_address('Rua Rui Barbosa, '+number+', Praia Grande',http,'test',submitted=True)[0]
   self.assertEqual(row['address']['street'],'Rua Rui Barbosa');self.assertEqual(row['address']['city'],'Praia Grande')
  row=search_address('Rua Rui Barbosa, 999999, Praia Grande',http,'test',submitted=True)[0]
  self.assertEqual(row['address_state'],'APPROXIMATE_NUMBER');self.assertEqual(row['precision_label'],'Número aproximado')
 def test_address_number_city_and_cep(self):
  for q in ['Av. Paulista, 1578, São Paulo','Avenida Paulista 1578, São Paulo','Avenida Paulista 1578 São Paulo']:
   p=address_query(q);self.assertEqual(p['housenumber'],'1578');self.assertEqual(p['city'],'São Paulo')
  self.assertEqual(address_query('01310-200')['postcode'],'01310200')
  self.assertEqual(address_query('Centro, São Bernardo do Campo')['district'],'Centro')
  self.assertNotIn('housenumber',address_query('Rua 25 de Março, São Paulo'))

 def test_structured_then_fulltext_rank_exact_number_before_nearby_street(self):
  requests=[]
  def http(url,**kwargs):
   requests.append(url);path=urlparse(url).path
   fs=[] if path=='/structured' else [dict(geometry={'coordinates':[-46.65,-23.56]},properties={'street':'Avenida Paulista','housenumber':'100','city':'São Paulo','state':'São Paulo'}),dict(geometry={'coordinates':[-46.66,-23.56]},properties={'street':'Avenida Paulista','housenumber':'1578','city':'São Paulo','state':'São Paulo'})]
   return json.dumps({'features':fs}).encode(),200,url,{}
  result=search_address('Av. Paulista, 1578, São Paulo',http,'test',-23.56,-46.65,submitted=True)
  self.assertEqual(result[0]['address']['housenumber'],'1578');self.assertIn('/structured?',requests[0]);self.assertIn('/api?',requests[1]);self.assertEqual(result[0]['match_quality'],'house_number')

 def test_typing_does_not_call_nominatim_or_structured(self):
  urls=[]
  def http(url,**kwargs):urls.append(url);return b'{"features":[]}',200,url,{}
  self.assertEqual(search_address('Avenida Paulista',http,'test'),[])
  self.assertEqual(len(urls),1);self.assertIn('photon.komoot.io/api?',urls[0])

 def test_approximate_house_number_is_not_fabricated(self):
  def http(url,**kwargs):return json.dumps({'features':[{'geometry':{'coordinates':[-46.65,-23.56]},'properties':{'name':'Avenida Paulista','city':'São Paulo'}}]}).encode(),200,url,{}
  row=search_address('Av. Paulista, 1578, São Paulo',http,'test',submitted=True)[0]
  self.assertEqual(row['match_quality'],'approximate');self.assertNotIn('1578',row['label']);self.assertIn('não localizado',row['precision_note'])

 def test_complete_portuguese_maneuvers(self):
  for typ,mod,expected in [('turn','right','Vire à direita'),('depart','straight','Inicie o trajeto em frente'),('arrive','','Você chegou ao destino'),('off ramp','right','Pegue a saída à direita')]:
   r=route_step({'maneuver':{'type':typ,'modifier':mod},'name':'SP-160','ref':'SP-160'});self.assertTrue(r['instruction'].startswith(expected));self.assertEqual(r['road_ref'],'SP-160')
  hybrid=instruction_pt({'instruction':'Turn à direita toward Avenida X','name':'Avenida X'});self.assertEqual(hybrid,'Siga para Avenida X')

 def test_source_failure_returns_empty_without_fabricating_destination(self):
  def http(*a,**k):raise OSError('unavailable')
  self.assertEqual(search_address('Rua X, 12, São Paulo',http,'test',submitted=True),[])

 def test_postcode_does_not_send_user_to_another_city_or_postcode(self):
  def http(url,**kwargs):
   if 'viacep' in url:return b'{"cep":"01310-200","uf":"SP","localidade":"Sao Paulo","logradouro":"Avenida Paulista"}',200,url,{}
   fs=[{'geometry':{'coordinates':[-46.65,-23.56]},'properties':{'street':'Avenida Paulista','city':'Sao Paulo','postcode':'01310-100'}},{'geometry':{'coordinates':[-46.66,-23.56]},'properties':{'street':'Avenida Paulista','city':'Sao Paulo','postcode':'01310-200'}}]
   return json.dumps({'features':fs}).encode(),200,url,{}
  rows=search_address('01310-200',http,'test',submitted=True);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['address']['postcode'],'01310-200');self.assertEqual(rows[0]['postal_source'],'viacep')

 def test_road_report_kinds_stay_community_in_isolated_database(self):
  import tempfile
  from pathlib import Path
  import server,community
  old=server.DATA_DIR,server.DB_PATH
  try:
   with tempfile.TemporaryDirectory() as tmp:
    server.DATA_DIR=Path(tmp);server.DB_PATH=Path(tmp)/'isolated.sqlite';server.init_db();community.init(server)
    handler=type('Handler',(),{'client_address':('127.0.0.1',12345)})()
    for kind in ['animal','closure']:
     result=community.post(server,handler,'/api/map/report',{'kind':kind,'longitude':-46.655,'latitude':-23.563})
     with server.db() as c:row=dict(c.execute('SELECT kind,report_kind,source,trust FROM map_points WHERE id=?',(result['id'],)).fetchone())
     self.assertEqual(row,{'kind':'other','report_kind':kind,'source':'public_report','trust':'recent'})
  finally:server.DATA_DIR,server.DB_PATH=old

 def test_asgi_assets_and_submitted_address_query_contract(self):
  import server
  from fastapi.testclient import TestClient
  from unittest.mock import patch
  with TestClient(server.app) as client:
   for path in ['/navigation/intelligence.js','/navigation/road-runtime.js','/navigation/road-mode.css','/icons/animal.svg','/icons/closure.svg']:
    self.assertEqual(client.get(path).status_code,200)
   with patch.object(server,'autocomplete_text',return_value=[{'label':'Fixture address'}]) as search:
    response=client.get('/api/autocomplete',params={'q':'Av Paulista 1578','lat':-23.56,'lon':-46.65,'submitted':1})
    self.assertEqual(response.status_code,200);self.assertEqual(response.json()['items'][0]['label'],'Fixture address')
    search.assert_called_once_with('Av Paulista 1578',-23.56,-46.65,7,True)


if __name__=='__main__':unittest.main()
