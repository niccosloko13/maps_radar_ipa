"""Regression: a nearby Rua Amparo must beat the distant namesake municipality."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from navigation_backend import search_address
class TestAddressProximity(unittest.TestCase):
 def test_city_omitted_prefers_nearby_street(self):
  def fake(url,**kwargs):
   features=[]
   for lon,lat,city in [(-46.77,-22.7,"Amparo"),(-46.54,-23.71,"São Bernardo do Campo")]:
    features.append({"geometry":{"coordinates":[lon,lat]},"properties":{"name":"Rua Amparo","street":"Rua Amparo","city":city,"state":"São Paulo","countrycode":"BR","type":"street"}})
   return json.dumps({"features":features}).encode(),None,None,None
  results=search_address("Rua Amparo 110",fake,"RELAS-test",near_lat=-23.71,near_lon=-46.54,submitted=True)
  self.assertGreaterEqual(len(results),2)
  self.assertIn("São Bernardo",results[0]["label"])
  self.assertNotEqual(results[0]["address_state"],"EXACT_ADDRESS")
if __name__=="__main__":unittest.main()
