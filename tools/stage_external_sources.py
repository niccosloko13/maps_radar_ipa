#!/usr/bin/env python3
"""RELAS: import external public data into review-only JSON staging; never write production DB.
Usage: python tools/stage_external_sources.py --output artifacts/staging/external-sp.json
       python tools/stage_external_sources.py --pardal-file /path/file.csv --freeflow-file /path/file.csv --offline
"""
import argparse,csv,io,json,urllib.request,urllib.parse,datetime,hashlib,pathlib
PARDAL="https://raw.githubusercontent.com/Murkiriel/pardal/main/estados/SP/radares.csv"
FREEFLOW="https://raw.githubusercontent.com/Sem-Parar/SEM-PARAR-FREE-FLOW/main/dados/porticos-free-flow.csv"
BUNDA="https://servidor3.lucas.inf.br/openclaw/radar/api.pse"
CITIES={"São Bernardo do Campo":(-23.82,-23.57,-46.69,-46.42),"Santo André":(-23.86,-23.60,-46.60,-46.36),"São Paulo":(-23.91,-23.35,-46.83,-46.35)}
def get(url):
 if not url.startswith("https://"):raise ValueError("HTTPS required")
 req=urllib.request.Request(url,headers={"User-Agent":"RELAS-source-audit/1.0 (read-only)"})
 with urllib.request.urlopen(req,timeout=20) as res:
  body=res.read(8_000_001)
 if len(body)>8_000_000:raise ValueError("source too large")
 return body.decode("utf-8-sig")
def parse_csv(txt):return list(csv.DictReader(io.StringIO(txt)))
def municipality_candidates(lat,lon):
 # Bounding boxes overlap and do NOT establish municipal jurisdiction.
 return [city for city,(s,n,w,e) in CITIES.items() if s<=lat<=n and w<=lon<=e]
def pardal(rows):
 out=[]
 for row in rows:
  try:lat=float(row["lat"]);lon=float(row["lng"])
  except (KeyError,ValueError,TypeError):continue
  if not (-26.5<=lat<=-19 and -54<=lon<=-44):continue
  kind=row.get("kind","UNKNOWN").upper()
  if kind not in {"FIXED","SECTION","RED_LIGHT","TRAFFIC_LIGHT","MOBILE","AVERAGE","SPEED_CAMERA"}:continue
  source=row.get("source","");limit=row.get("limit_kmh","")
  out.append({"external_key":hashlib.sha256(("pardal|"+str(lat)+"|"+str(lon)+"|"+kind).encode()).hexdigest()[:20],"kind":kind,"lat":lat,"lon":lon,"speed_kmh":int(limit) if limit.isdigit() and 0<int(limit)<=140 else None,"heading_deg":float(row["direction_deg"]) if row.get("direction_deg","").replace(".","",1).isdigit() else None,"claimed_active":row.get("active"),"upstream_source":source,"municipality_candidates_bbox_only":municipality_candidates(lat,lon),"status":"candidate_unverified","source_id":"github_pardal","license":"ODbL-1.0; review obligations before publishing"})
 return out
def freeflow(rows):
 out=[]
 for row in rows:
  if row.get("uf","").upper()!="SP":continue
  out.append({"external_key":hashlib.sha256(("freeflow|"+row.get("sigla","")+"|"+row.get("km","")+"|"+row.get("municipio","")+"|"+row.get("sentido","")).encode()).hexdigest()[:20],"kind":"FREE_FLOW_GANTRY","municipality":row.get("municipio"),"road":row.get("sigla"),"km_text":row.get("km"),"direction_text":row.get("sentido"),"operator":row.get("concessionaria"),"upstream_status":row.get("status"),"upstream_updated_at":row.get("atualizado_em"),"lat":None,"lon":None,"geocode_required":True,"status":"candidate_unverified","source_id":"github_semparar_freeflow","license":"CC BY 4.0; attribution required"})
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",required=True);ap.add_argument("--offline",action="store_true");ap.add_argument("--pardal-file");ap.add_argument("--freeflow-file");ap.add_argument("--bunda-json");ap.add_argument("--bunda-sample",action="store_true",help="fetch a single bounded SP API page for schema review");args=ap.parse_args()
 if args.offline and not (args.pardal_file and args.freeflow_file):ap.error("--offline requires two local CSV files")
 def read(path,url):
  return pathlib.Path(path).read_text(encoding="utf-8-sig") if path else get(url)
 data={"generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"mode":"staging_only","production_writes":False,"sources":{},"candidates":[],"warnings":["Municipality candidates use approximate bounding boxes ONLY, not authoritative borders.","No candidates are real-time confirmed or production-ready.","Free Flow kilometre markers are NOT geocoded. Do not pin without official coordinates."]}
 for name,path,url,parser in [("pardal",args.pardal_file,PARDAL,pardal),("semparar_freeflow",args.freeflow_file,FREEFLOW,freeflow)]:
  try:
   rows=parse_csv(read(path,url));items=parser(rows);data["candidates"].extend(items);data["sources"][name]={"fetched":True,"rows":len(rows),"candidates":len(items),"url":url}
  except Exception as e:data["sources"][name]={"fetched":False,"error_type":type(e).__name__};data["warnings"].append(name+" unavailable; no inferred data")
 # Bunda de Urso API is separate; no automated bulk import until response contract and usage policy are reviewed.
 data["sources"]["bunda_de_urso"]={"fetched":False,"endpoint":BUNDA,"mode":"manual API evaluation required","reason":"No authenticated permission/validated bulk schema; avoid blind remote harvesting"}
 if args.bunda_sample and not args.offline:
  # One page, state filter, no crawling. API's payload is intentionally not merged.
  try:
   url=BUNDA+"?"+urllib.parse.urlencode({"rota":"/api/v1/radares/busca","uf":"SP","limite":"100","formato":"json"})
   payload=json.loads(get(url))
   points=payload.get("resultado",{}).get("pontos",[])
   data["sources"]["bunda_de_urso"].update({"fetched":True,"sample_count":len(points),"mode":"schema_review_only","sample":points[:3],"warning":"Requires source and redistribution review; no automatic production merge"})
  except Exception as e:data["sources"]["bunda_de_urso"].update({"fetched":False,"error_type":type(e).__name__})
 if args.bunda_json:
  try:
   parsed=json.loads(pathlib.Path(args.bunda_json).read_text(encoding="utf-8"))
   data["sources"]["bunda_de_urso"]["sample_type"]=type(parsed).__name__
   data["sources"]["bunda_de_urso"]["local_sample_inspected"]=True
  except Exception as e:data["sources"]["bunda_de_urso"]["local_sample_error"]=type(e).__name__
 path=pathlib.Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"output":str(path),"staged":len(data["candidates"]),"sources":data["sources"],"production_writes":False},ensure_ascii=False))
if __name__=="__main__":main()
