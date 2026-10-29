"""Navigation presentation/search helpers. No database schema or radar identity changes."""
import json
import math
import re
import unicodedata
import urllib.parse


def normalized(value):
    return ' '.join(str(value or '').split())[:240]


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',normalized(value)) if not unicodedata.combining(c)).casefold()


def address_query(value):
    q=normalized(value)
    for short,long in [('Av','Avenida'),('Pres','Presidente'),('Dr','Doutor'),('R','Rua')]:
        q=re.sub(r'\b'+short+r'\.(?=\s)',long,q,flags=re.I)
    parts=[p.strip() for p in q.split(',') if p.strip()]
    parts=[p for p in parts if folded(p) not in {'sp','brasil','brazil'}]
    result={'raw':normalized(value),'query':q,'countrycode':'BR','state':'São Paulo'}
    cep=re.fullmatch(r'(\d{5})-?(\d{3})',q)
    if cep:
        result['postcode']=cep[1]+cep[2];return result
    street=parts[0] if parts else q
    if re.match(r'^(Rua|R\.?|Avenida|Av\.?|Alameda|Estrada|Rodovia|Travessa|Praça)\s',street,re.I):
        m=re.match(r'^(.*?)\s+(?:n[ºo°]?\.?\s*)?(\d+[A-Za-z]?)\s*(.*)$',street,re.I)
        if m and not re.match(r'^(de|da|do|dos|das)\b',m[3],re.I):
            street=m[1];result['housenumber']=m[2]
            if m[3]:result['city']=m[3]
        elif len(parts)>1 and re.fullmatch(r'(?:n[ºo°]?\.?\s*)?\d+[A-Za-z]?',parts[1],re.I):
            result['housenumber']=re.sub(r'^n[ºo°]?\.?\s*','',parts[1],flags=re.I);parts.pop(1)
        result['street']=street
    elif len(parts)>1:
        result['district']=street
    if len(parts)>1:
        result['city']=parts[-1]
    return result


# Explicit public name for the structured address parser.
parseAddressQuery=address_query


def distance(lat,lon,a,b):
    if lat is None or lon is None:return None
    return math.hypot((lon-b)*111320*math.cos(math.radians(lat)),(lat-a)*110540)


def search_address(query,http_request,ua,near_lat=None,near_lon=None,limit=7,submitted=False):
    parsed=address_query(query)
    if near_lat is not None and not math.isfinite(near_lat):near_lat=None
    if near_lon is not None and not math.isfinite(near_lon):near_lon=None
    if len(parsed['query'])<3:return []
    if parsed.get('postcode'):
        if not submitted:return []
        try:
            raw,_,_,_=http_request('https://viacep.com.br/ws/'+parsed['postcode']+'/json/',headers={'User-Agent':ua,'Accept':'application/json'},timeout=5,method='GET',attempts=1)
            postal=json.loads(raw.decode('utf-8'))
            if postal.get('erro') or postal.get('uf')!='SP':return []
            parsed.update(street=postal.get('logradouro',''),city=postal.get('localidade',''),postcode=postal.get('cep',parsed['postcode']))
            parsed['query']=', '.join(x for x in [parsed['street'],parsed['city'],'SP'] if x)
        except (OSError,ValueError):
            return []
    # Public Photon currently exposes default/de/en/fr, not pt. Default keeps
    # Brazilian OSM names instead of causing HTTP 400 for every search.
    items=[];seen=set();common={'limit':8,'lang':'default','countrycode':'BR'}
    if near_lat is not None and near_lon is not None and math.isfinite(near_lat) and math.isfinite(near_lon):
        common.update(lat=near_lat,lon=near_lon)
    def collect(path,params,provider):
        try:
            raw,_,_,_=http_request('https://photon.komoot.io/'+path+'?'+urllib.parse.urlencode(params),headers={'User-Agent':ua,'Accept':'application/json'},timeout=7,method='GET',attempts=1)
            for f in json.loads(raw.decode('utf-8')).get('features',[]):
                co=(f.get('geometry') or {}).get('coordinates') or [];p=f.get('properties') or {}
                if len(co)<2:continue
                lon,lat=float(co[0]),float(co[1])
                if not(math.isfinite(lon) and math.isfinite(lat) and -53.2<=lon<=-44 and -25.4<=lat<=-19.7):continue
                if p.get('countrycode') and str(p['countrycode']).upper()!='BR':continue
                if p.get('state') and folded(p['state']) not in {'sao paulo','sp'}:continue
                if parsed.get('postcode') and folded(p.get('city'))!=folded(parsed.get('city')):continue
                if parsed.get('postcode') and p.get('postcode') and re.sub(r'\D','',p['postcode'])!=re.sub(r'\D','',parsed['postcode']):continue
                bits=[]
                for k in ['name','street','housenumber','district','city','state','postcode']:
                    v=normalized(p.get(k))
                    if v and v not in bits:bits.append(v)
                label=', '.join(bits)
                identity=(round(lon,6),round(lat,6),folded(label))
                if not label or identity in seen:continue
                seen.add(identity)
                requested=parsed.get('housenumber');exact=bool(requested and folded(p.get('housenumber'))==folded(requested))
                d=distance(near_lat,near_lon,lat,lon)
                note='Área do CEP · confirme o trecho antes de iniciar' if parsed.get('postcode') else None if not requested or exact else 'Trecho aproximado · número não localizado'
                items.append(dict(lat=lat,lon=lon,label=label,display_name=label,address=p,provider=provider,postal_source='viacep' if parsed.get('postcode') else None,type=p.get('type') or 'place',distance_m=round(d) if d is not None else None,requested_housenumber=requested,match_quality='house_number' if exact else 'approximate' if requested or parsed.get('postcode') else 'place',precision_note=note))
                # UI state is explicit while match_quality remains compatible
                # with the pre-hardening API contract.
                candidate=items[-1]
                same_street=folded(p.get('street') or p.get('name'))==folded(parsed.get('street'))
                same_city=not parsed.get('city') or folded(p.get('city'))==folded(parsed.get('city'))
                candidate['address_state']='EXACT_ADDRESS' if requested and exact and same_street and same_city else 'APPROXIMATE_NUMBER' if requested and same_street and same_city else 'STREET_ONLY' if same_street and same_city else 'FUZZY_ALTERNATIVE'
                candidate['precision_label']={'EXACT_ADDRESS':'Número exato','APPROXIMATE_NUMBER':'Número aproximado','STREET_ONLY':'Rua localizada','FUZZY_ALTERNATIVE':'Sugestão alternativa'}[candidate['address_state']]
        except (OSError,ValueError,TypeError):
            return
    if submitted and any(k in parsed for k in ['street','postcode','district']):
        collect('structured',{**common,**{k:v for k,v in parsed.items() if k not in {'raw','query'}}},'photon_structured')
    if not items or (parsed.get('housenumber') and not any(i['match_quality']=='house_number' for i in items)):
        collect('api',{**common,'q':parsed['query']},'photon')
    def rank(r):
        p=r['address'];street=folded(p.get('street') or p.get('name'));wanted_street=folded(parsed.get('street'));city=folded(p.get('city'));wanted_city=folded(parsed.get('city'));number=folded(p.get('housenumber'));wanted_number=folded(parsed.get('housenumber'));score=0
        # Exact street + city + number has a higher, explainable score than a
        # fuzzy provider result. Distance only breaks a score tie.
        score+=100 if wanted_street and street==wanted_street else 20 if wanted_street and street.startswith(wanted_street) else -80 if wanted_street else 0
        score+=60 if wanted_city and city==wanted_city else -120 if wanted_city else 0
        score+=80 if wanted_number and number==wanted_number else 15 if wanted_number and street==wanted_street else 0
        if parsed.get('postcode') and re.sub(r'\D','',str(p.get('postcode','')))==re.sub(r'\D','',parsed['postcode']):score+=30
        # City omitted: place verified nearby candidates ahead of namesake streets
        # in distant SP municipalities (e.g. Rua Amparo in Amparo versus SBC).
        # A typed city remains authoritative: never bias against intentional travel.
        if not wanted_city and r['distance_m'] is not None:
            d=r['distance_m']
            if d>25000:score-=140
            elif d>12000:score-=80
            elif d<=4000:score+=85
            elif d<=12000:score+=35
        return (-score,r['distance_m'] if r['distance_m'] is not None else 1e12,r['label'])
    return sorted(items,key=rank)[:max(1,min(8,int(limit)))]


def instruction_pt(step):
    """Build from provider maneuver semantics. Never partially translate an English sentence."""
    man=step.get('maneuver') or {};typ=man.get('type') or step.get('maneuver_type') or '';modifier=man.get('modifier') or step.get('modifier') or '';name=normalized(step.get('name'));ref=normalized(step.get('ref'));road=' · '.join(x for x in [name,ref] if x)
    existing=normalized(man.get('instruction') or step.get('instruction'))
    if not typ and existing and not re.search(r'\b(turn|toward|onto|head|continue|keep|exit|arrive|destination|merge|roundabout)\b',existing,re.I):
        return existing
    sides={'right':'à direita','left':'à esquerda','slight right':'levemente à direita','slight left':'levemente à esquerda','sharp right':'à direita','sharp left':'à esquerda','straight':'em frente','uturn':'e faça o retorno'}
    if typ=='arrive':return 'Você chegou ao destino'
    if typ in {'roundabout','rotary','exit roundabout','exit rotary'}:
        exit_number=man.get('exit')
        return f'Na rotatória, pegue a saída {exit_number}'+(' para '+road if road else '') if exit_number else 'Siga pela rotatória'+(' para '+road if road else '')
    if typ in {'on ramp','off ramp'}:
        base='Pegue o acesso' if typ=='on ramp' else 'Pegue a saída'
    elif typ in {'fork','end of road','turn','new name'}:
        base='Vire' if typ in {'turn','end of road'} else 'Mantenha-se'
    elif typ=='merge':base='Entre na via'
    elif typ=='depart':base='Inicie o trajeto'
    else:base='Siga'
    if modifier in sides:base+=' '+sides[modifier]
    return base+(' para '+road if road else '')


def route_step(step):
    man=step.get('maneuver') or {};geometry=(step.get('geometry') or {}).get('coordinates') or []
    return dict(instruction=instruction_pt(step),distance=step.get('distance',0),duration=step.get('duration',0),name=step.get('name',''),ref=step.get('ref',''),maneuver_type=man.get('type'),modifier=man.get('modifier'),road_class=step.get('road_class'),road_ref=step.get('ref'),road_context_basis='provider metadata' if step.get('road_class') or step.get('ref') else 'unknown',maneuver_location=man.get('location'),bearing_after=man.get('bearing_after'),geometry={'type':'LineString','coordinates':geometry} if geometry else None)
