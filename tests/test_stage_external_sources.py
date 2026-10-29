import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from stage_external_sources import pardal,freeflow,municipality_candidates
class TestExternalSources(unittest.TestCase):
 def test_pardal_sp_and_missing_limit(self):
  rows=[dict(lat="-23.7",lng="-46.5",kind="FIXED",limit_kmh="",source="OSM",active="1",direction_deg="")]
  result=pardal(rows)
  self.assertEqual(len(result),1)
  self.assertIsNone(result[0]["speed_kmh"])
  self.assertEqual(result[0]["status"],"candidate_unverified")
 def test_pardal_rejects_invalid_positions(self):
  self.assertEqual(pardal([{"lat":"0","lng":"0","kind":"FIXED"}]),[])
 def test_freeflow_no_geocode_invention(self):
  a=freeflow([dict(uf="SP",sigla="SP-021",km="135",municipio="Guarulhos",sentido="ambos",status="ativo")])
  self.assertEqual(len(a),1)
  self.assertIsNone(a[0]["lat"])
  self.assertTrue(a[0]["geocode_required"])
 def test_bbox_not_authoritative(self):
  self.assertIsInstance(municipality_candidates(-23.7,-46.55),list)
if __name__=="__main__":unittest.main()
