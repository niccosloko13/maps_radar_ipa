import os
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import server
import db
from admin_auth import AdminAuth, hash_password


class RuntimeTests(unittest.TestCase):
    def test_auth_across_instances_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'RELAS_ENV':'production','ADMIN_USERNAME':'operator',
                                        'ADMIN_PASSWORD_HASH':hash_password('test-password'),
                                        'SESSION_SECRET':'a'*48}):
                one=AdminAuth(Path(directory)/'never-created')
                self.assertTrue(one.password_valid('operator','test-password'))
                token=one.issue();two=AdminAuth(Path(directory)/'also-not-created')
                self.assertTrue(two.valid(token));self.assertFalse(two.valid(token+'x'))
                self.assertIn('Secure',two.cookie(token))
                self.assertFalse((Path(directory)/'never-created').exists())
                with patch.dict(os.environ, {'ADMIN_PASSWORD_HASH':''}):
                    self.assertTrue(two.configuration_errors());self.assertFalse(two.password_valid('admin','123'))

    def test_sql_boundary(self):
        self.assertEqual(db.parameters("SELECT ?,'what?', '%x%', \"x?\""),"SELECT %s,'what?', '%%x%%', \"x?\"")
        sql=db.upsert_statement('INSERT INTO source_syncs(source_id,status,error) VALUES(?,?,?)')
        self.assertIn('ON CONFLICT(source_id)',sql);self.assertNotIn('DELETE',sql)
        with self.assertRaises(ValueError):db.upsert_statement('INSERT INTO unknown(id) VALUES(?)')

    def test_asgi_sqlite_transport_and_static(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'DATABASE_BACKEND':'sqlite','RELAS_ENV':'development','RELAS_ADMIN_PASSWORD':'test-local'}):
            with patch.object(server,'DB_PATH',Path(directory)/'test.sqlite'),patch.object(server,'DATA_DIR',Path(directory)),patch.object(server,'AUTH',AdminAuth(directory)):
                server.init_db();server.ensure_v18_tables();server.community.init(server)
                with TestClient(server.app) as client:
                    for url in ['/','/admin','/sw.js','/icons/signal.svg','/api/health','/api/radars','/api/road-objects','/api/stats','/api/map/features?bbox=-46.7,-23.7,-46.6,-23.5']:
                        self.assertEqual(client.get(url).status_code,200,url)
                    self.assertEqual(client.get('/api/unknown').status_code,404)
                    self.assertEqual(client.get('/api/admin/database-status').status_code,401)
                    self.assertEqual(client.get('/api/sync/santos').status_code,401)
                    self.assertEqual(client.post('/api/admin/login',json={'username':'admin','password':'test-local'}).status_code,200)
                    self.assertEqual(client.get('/api/admin/database-status').status_code,200)
                    self.assertEqual(client.post('/api/admin/logout').status_code,200)
                    self.assertFalse(client.get('/api/admin/me').json()['ok'])
                    self.assertEqual(client.post('/api/map/report',headers={'Origin':'https://evil.invalid'},json={}).status_code,403)
                    self.assertEqual(client.post('/api/map/report',content=b'x'*2097153).status_code,413)

    def test_hosted_never_falls_back_to_sqlite(self):
        with patch.dict(os.environ,{'RELAS_ENV':'production','DATABASE_BACKEND':'sqlite'}):
            with self.assertRaises(RuntimeError):db.connect('must-not-exist.sqlite')

    def test_invalid_backend_is_diagnosed_without_exposing_value(self):
        invalid='postgresql://private-user:private-password@private-host/db'
        with patch.dict(os.environ,{'RELAS_ENV':'production','DATABASE_BACKEND':invalid}):
            with TestClient(server.app) as client:
                response=client.get('/api/health')
                self.assertEqual(response.status_code,503)
                self.assertEqual(response.json()['engine'],'unconfigured')
                self.assertIn('DATABASE_BACKEND',response.text)
                self.assertNotIn('private-password',response.text)
                response=client.get('/api/radars')
                self.assertEqual(response.status_code,503)
                self.assertEqual(response.json()['code'],'database_configuration_error')
                self.assertNotIn('private-password',response.text)

    def test_missing_database_url_is_diagnosed(self):
        with patch.dict(os.environ,{'RELAS_ENV':'production','DATABASE_BACKEND':'postgres','DATABASE_URL':''}):
            result=server.health_status()
            self.assertFalse(result['ok'])
            self.assertIn('DATABASE_URL is required',result['configuration_errors'])

    def test_public_api_failures_do_not_expose_internal_errors(self):
        secret='postgresql://private-user:private-password@private-host/neondb'
        with patch.dict(os.environ,{'DATABASE_BACKEND':'sqlite','RELAS_ENV':'development'}):
            with patch.object(server,'autocomplete_text',side_effect=RuntimeError(secret)), \
                 patch.object(server,'geocode_text',side_effect=RuntimeError(secret)), \
                 patch.object(server,'build_route',side_effect=RuntimeError(secret)):
                with TestClient(server.app) as client:
                    requests=(
                        client.get('/api/autocomplete?q=Paulista'),
                        client.get('/api/geocode?q=Paulista'),
                        client.get('/api/route?flat=-23.56&flon=-46.65&tlat=-23.55&tlon=-46.63'),
                    )
                for response in requests:
                    self.assertEqual(response.status_code,503)
                    self.assertNotIn('private-password',response.text)
                    self.assertNotIn('private-host',response.text)

    def test_hosted_import_has_no_database_or_filesystem_initialization(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'must-not-be-created'
            env=dict(os.environ,VERCEL='1',DATABASE_BACKEND='postgres',DATABASE_URL='',RADAR_DATA_DIR=str(target),ADMIN_USERNAME='',ADMIN_PASSWORD_HASH='',SESSION_SECRET='')
            result=subprocess.run([sys.executable,'-c',"import server; assert server.app is not None; assert not server.USER_DATA_DIR.exists(); assert server.AUTH.configuration_errors(); print('IMPORT_OK')"],env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('IMPORT_OK',result.stdout)


if __name__=='__main__':unittest.main()
