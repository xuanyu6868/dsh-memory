"""Controlled fixtures only: no real memory, model calls, launchd, or external API."""
import contextlib
import hashlib
import http.server
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import types
import unittest
import urllib.parse

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from ov_api import ApiError, Client, uri_parts


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

backup = load('backup', 'backup-memories.py')
restore = load('restore', 'restore-memories.py')
scope = load('scope', 'verify-peer-scope.py')
blackhole = load('blackhole', 'blackhole-server.py')
USER = 'viking://user/example-user'
PERSONAL = USER + '/memories/preferences/language.md'
PROJECT = USER + '/peers/project-a/memories/events/2026/10/22/fact.md'
PROJECT_B = USER + '/peers/project-b/memories/preferences/style.md'


class FakeState:
    def __init__(self):
        self.files = {PERSONAL: '---\nid: fixture-personal\n---\n示例偏好\n', PROJECT: 'synthetic project A\n', PROJECT_B: 'synthetic project B\n'}
        self.calls = []
        self.leak = False
        self.invalid_listing = False
        self.repeat_page = False
        self.fail_read = None
        self.error_envelope = False


@contextlib.contextmanager
def server():
    state = FakeState()
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def send(self, code, result, **extra):
            data = json.dumps({'status': 'error' if state.error_envelope else 'ok', 'result': result, **extra}).encode()
            self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            uri = q.get('uri', [''])[0]
            state.calls.append(('GET', parsed.path, q))
            if parsed.path.endswith('/read'):
                if uri not in state.files or uri == state.fail_read:
                    self.send(404 if uri not in state.files else 500, {}); return
                self.send(200, state.files[uri]); return
            if parsed.path.endswith('/ls'):
                children = {}
                for name in state.files:
                    if name.startswith(uri + '/'):
                        rel = name[len(uri)+1:]
                        child = uri + '/' + rel.split('/')[0]
                        children[child] = {'uri': child, 'isDir': '/' in rel}
                items = sorted(children.values(), key=lambda i: i['uri'])
                # Return one entry per page to exercise discovery AND nested pagination.
                offset = 0 if state.repeat_page else int(q.get('offset', ['0'])[0])
                page = items[offset:offset+1]
                if state.invalid_listing:
                    self.send(200, page); return
                self.send(200, page, has_more=bool(page) if state.repeat_page else offset+1 < len(items)); return
            self.send(404, {})
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            actor = self.headers.get('X-OpenViking-Actor-Peer')
            state.calls.append(('POST', self.path, body))
            if self.path.endswith('/search'):
                entries = [{'uri': PERSONAL}, {'uri': 'viking://agent/skills/example/SKILL.md'}]
                if actor != 'project-b':
                    entries.append({'uri': PROJECT})
                if state.leak:
                    entries.append({'uri': USER + '/peers/project-c/memories/events/leak.md'})
                # Omit optional origin stats, intentionally. URI checks must stand alone.
                self.send(200, {'entries': entries, 'stats': {}}); return
            if self.path.endswith('/write'):
                if body['uri'] in state.files:
                    self.send(409, {}); return
                state.files[body['uri']] = body['content']; self.send(200, {}); return
            self.send(404, {})
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True); thread.start()
    try:
        yield state, Client(f'http://127.0.0.1:{httpd.server_port}', timeout=1)
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=1)


class BackupTests(unittest.TestCase):
    def test_default_discovers_all_project_roots_and_paginates(self):
        with server() as (state, client), tempfile.TemporaryDirectory() as td:
            roots = backup.discover_roots(client, USER)
            self.assertEqual(len(roots), 3)
            result = backup.export(client, Path(td) / 'export', roots)
            self.assertTrue(result['complete']); self.assertEqual(len(result['files']), 3)
            self.assertEqual({e['uri'] for e in result['files']}, set(state.files))
            self.assertTrue(any(int(q.get('offset', ['0'])[0]) > 0 for method, path, q in state.calls if method == 'GET' and path.endswith('/ls')))
            self.assertTrue(all(q.get('raw') == ['true'] for method, path, q in state.calls if method == 'GET' and path.endswith('/read')))
    def test_directory_with_dot_and_extensionless_memory_are_not_skipped(self):
        with server() as (state, client), tempfile.TemporaryDirectory() as td:
            uri = USER + '/memories/project.v2/fact'
            state.files = {uri: 'fixture'}
            result = backup.export(client, Path(td) / 'export', [USER + '/memories'])
            self.assertEqual(result['files'][0]['uri'], uri)
    def test_missing_pagination_fails_closed(self):
        with server() as (state, client):
            state.invalid_listing = True
            with self.assertRaises(ApiError): backup.discover_roots(client, USER)
    def test_repeated_page_fails_instead_of_truncating_or_looping(self):
        with server() as (state, client):
            state.repeat_page = True
            with self.assertRaises(ApiError): list(client.listing(USER))
    def test_read_failure_leaves_manifest_incomplete(self):
        with server() as (state, client), tempfile.TemporaryDirectory() as td:
            state.fail_read = PERSONAL; out = Path(td) / 'export'
            with self.assertRaises(ApiError): backup.export(client, out, [USER + '/memories'])
            self.assertFalse(json.loads((out/'manifest.json').read_text())['complete'])
            with self.assertRaises(ValueError): restore.load_export(out)
    def test_refuses_existing_destination(self):
        with server() as (_, client), tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileExistsError): backup.export(client, td, [USER + '/memories'])
    def test_error_envelope_is_not_an_empty_success(self):
        with server() as (state, client):
            state.error_envelope = True
            with self.assertRaises(ApiError): backup.discover_roots(client, USER)
    def test_empty_export_refused(self):
        with server() as (state, client), tempfile.TemporaryDirectory() as td:
            state.files = {}
            with self.assertRaises(ApiError): backup.export(client, Path(td)/'out', [USER+'/memories'])


class RestoreTests(unittest.TestCase):
    def make_export(self, client, td):
        out = Path(td) / 'export'
        backup.export(client, out, backup.discover_roots(client, USER))
        return out
    def test_export_restore_round_trip_via_real_http_and_read_back(self):
        with server() as (state, client), tempfile.TemporaryDirectory() as td:
            original = dict(state.files); out = self.make_export(client, td)
            plan = restore.plan_restore(out, USER + '/memories/restore-fixture')
            self.assertEqual(restore.apply_restore(client, plan), (3, 0))
            self.assertEqual(sorted(text for _, text in plan), sorted(original.values()))
            self.assertTrue(set(original).issubset(state.files))
            self.assertEqual(restore.apply_restore(client, plan), (0, 3))
            writes = [b for m,p,b in state.calls if m == 'POST' and p.endswith('/write')]
            self.assertTrue(all(b['mode']=='create' and b['processing_mode']=='vectors_only' for b in writes))
    def test_dry_run_cli_makes_no_network_request(self):
        with server() as (state, client), tempfile.TemporaryDirectory() as td:
            out = self.make_export(client, td); before = len(state.calls)
            proc = subprocess.run([sys.executable, '-B', str(SCRIPTS/'restore-memories.py'), '--from', str(out), '--base', 'http://127.0.0.1:1'], capture_output=True, text=True, timeout=3)
            self.assertEqual(proc.returncode, 0, proc.stderr); self.assertEqual(len(state.calls), before)
    def test_corruption_rejected_before_restore(self):
        with server() as (_, client), tempfile.TemporaryDirectory() as td:
            out = self.make_export(client, td); manifest=json.loads((out/'manifest.json').read_text())
            (out/manifest['files'][0]['path']).write_text('tampered')
            with self.assertRaises(ValueError): restore.plan_restore(out)
    def test_manifest_path_escape_rejected(self):
        with server() as (_, client), tempfile.TemporaryDirectory() as td:
            out = self.make_export(client, td); p=out/'manifest.json'; m=json.loads(p.read_text()); m['files'][0]['path']='../outside.txt'; p.write_text(json.dumps(m))
            with self.assertRaises(ValueError): restore.plan_restore(out)
    def test_conflicts_block_all_writes(self):
        with server() as (state, client), tempfile.TemporaryDirectory() as td:
            out = self.make_export(client, td); plan=restore.plan_restore(out, USER+'/memories/restore-fixture')
            state.files[plan[-1][0]]='different'; before=len(state.files)
            with self.assertRaises(ValueError): restore.apply_restore(client, plan)
            self.assertEqual(len(state.files), before)
    def test_duplicate_uri_rejected(self):
        with server() as (_, client), tempfile.TemporaryDirectory() as td:
            out=self.make_export(client, td); p=out/'manifest.json'; m=json.loads(p.read_text()); m['files'][1]['uri']=m['files'][0]['uri']; p.write_text(json.dumps(m))
            with self.assertRaises(ValueError): restore.plan_restore(out)


class ScopeTests(unittest.TestCase):
    def args(self):
        return types.SimpleNamespace(user='example-user', peer='project-a', other='project-b', query_project='synthetic project fact', query_personal='synthetic language preference', project_uri=PROJECT, personal_uri=PERSONAL)
    def test_valid_global_self_and_actor_results_pass_without_stats(self):
        with server() as (_, client): self.assertEqual(scope.run_checks(client, self.args()), 0)
    def test_third_peer_leak_fails_without_stats(self):
        with server() as (state, client):
            state.leak=True; self.assertEqual(scope.run_checks(client, self.args()), 1)
    def test_third_peer_leak_fails_even_when_stats_claim_zero(self):
        with self.assertRaises(ValueError): scope.validate_result({'entries':[{'uri':USER+'/peers/project-c/memories/x.md'}], 'stats':{'origins':{'other_peer':0}}}, user='example-user', peer='project-a', scope='actor', actor='project-a')
    def test_cross_user_or_unknown_namespace_fails(self):
        for uri in ('viking://user/another-user/memories/f.md', 'viking://user/example-user/unknown/f.md'):
            with self.subTest(uri=uri), self.assertRaises(ValueError): scope.validate_result({'entries':[{'uri':uri}]}, user='example-user', peer='project-a', scope='actor', actor='project-a')
    def test_false_personal_stat_does_not_replace_personal_uri(self):
        with self.assertRaises(ValueError): scope.validate_result({'entries':[{'uri':PROJECT}], 'stats':{'origins':{'self':99}}}, user='example-user', peer='project-a', scope='actor', actor='project-a', expect_self=True)
    def test_missing_entries_is_not_empty_pass(self):
        with self.assertRaises(ValueError): scope.validate_result({'stats':{}}, user='example-user', peer='project-a', scope='actor', actor='project-a')
    def test_missing_exact_sentinel_fails(self):
        with self.assertRaises(ValueError): scope.validate_result({'entries':[{'uri':PERSONAL}]}, user='example-user', peer='project-a', scope='actor', actor='project-a', required_uri=PROJECT)
    def test_no_session_id_or_ledger_side_effect_in_search_request(self):
        with server() as (state, client):
            scope.run_checks(client, self.args())
            searches=[b for m,p,b in state.calls if m=='POST']
            self.assertEqual(len(searches),5); self.assertTrue(all('session_id' not in b and b.get('quotas') for b in searches))


class TransportTests(unittest.TestCase):
    def test_uri_traversal_rejected(self):
        for uri in ('viking://user/a/../b', 'viking://user/a/%2e%2e/b', 'viking://user/a/%2fb', 'viking://user/a/\\b'):
            with self.subTest(uri=uri), self.assertRaises(ValueError): uri_parts(uri)
    def test_hanging_helper_returns_no_bytes_and_times_out(self):
        srv=blackhole.BlackholeServer(('127.0.0.1',0),hold=1)
        thread=threading.Thread(target=srv.serve_forever,kwargs={'poll_interval':0.01},daemon=True);thread.start()
        try:
            with socket.create_connection(srv.server_address,timeout=1) as conn:
                conn.settimeout(0.05); conn.sendall(b'GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n')
                with self.assertRaises(socket.timeout): conn.recv(1)
        finally:
            srv.stopping.set();srv.shutdown();srv.server_close();thread.join(timeout=1)


if __name__ == '__main__':
    unittest.main()
