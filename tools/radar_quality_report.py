#!/usr/bin/env python3
"""RELAS radar inventory quality audit. Read-only; never changes a table or credential."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from runtime_config import load_environment
load_environment()
import db as database

def report():
    now=datetime.now(timezone.utc).isoformat()
    result={'generated_at_utc':now,'scope':'current configured database','read_only':True,'definitions':{
        'last_seen':'last database observation, NOT proof radar is operating',
        'source_date':'date supplied by source, when present',
        'suspicious_coordinates':'outside approximate Sao Paulo state envelope; requires manual investigation',
        'source_sync':'last registered attempt; not proof that external data is complete'
    }}
    if database.backend()=='sqlite':
        import os
        import sqlite3
        from contextlib import closing
        local=os.environ.get('LOCALAPPDATA')
        data_dir=Path(os.environ['RADAR_DATA_DIR']).expanduser() if os.environ.get('RADAR_DATA_DIR') else (Path(local)/'RadarSP'/'data' if local else ROOT/'user-data')
        path=data_dir/'radar.db'
        if not path.is_file():
            raise FileNotFoundError('SQLite database not found: check RADAR_DATA_DIR')
        connection=sqlite3.connect('file:'+str(path.resolve())+'?mode=ro',uri=True)
        connection.row_factory=sqlite3.Row
    else:
        from contextlib import closing
        connection=database.connect()
    with closing(connection) as c:
        result['by_source']=[dict(r) for r in c.execute("""
            SELECT source, COUNT(*) AS total,
            SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS marked_active,
            SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) AS geocoded,
            SUM(CASE WHEN speed_limit BETWEEN 1 AND 140 THEN 1 ELSE 0 END) AS with_limit,
            SUM(CASE WHEN direction IS NOT NULL AND direction<>'' THEN 1 ELSE 0 END) AS with_direction,
            SUM(CASE WHEN source_date IS NOT NULL AND source_date<>'' THEN 1 ELSE 0 END) AS with_source_date,
            MIN(last_seen) AS oldest_last_seen, MAX(last_seen) AS newest_last_seen
            FROM radars WHERE state='SP' GROUP BY source ORDER BY total DESC
        """).fetchall()]
        result['municipalities']=[dict(r) for r in c.execute("""
            SELECT municipality,COUNT(*) AS radar_count,
            SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) AS mapped
            FROM radars WHERE state='SP' GROUP BY municipality ORDER BY radar_count DESC
        """).fetchall()]
        result['coordinate_flags']=[dict(r) for r in c.execute("""
            SELECT source,COUNT(*) AS suspicious
            FROM radars WHERE state='SP' AND latitude IS NOT NULL AND longitude IS NOT NULL
            AND (latitude NOT BETWEEN -26.5 AND -19 OR longitude NOT BETWEEN -54 AND -44)
            GROUP BY source ORDER BY suspicious DESC
        """).fetchall()]
        result['source_syncs']=[dict(r) for r in c.execute("""
            SELECT source_id,status,finished_at,http_status,imported,updated,unchanged,mapped,error
            FROM source_syncs ORDER BY source_id
        """).fetchall()]
    return result

if __name__=='__main__':
    try: print(json.dumps(report(),ensure_ascii=False,indent=2,default=str))
    except Exception as exc:
        print(json.dumps({'ok':False,'error_type':type(exc).__name__,'message':'Audit failed; inspect secure application logs without exposing credentials'}),file=sys.stderr)
        raise SystemExit(1)
