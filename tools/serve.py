"""Loopback-only review UI and replay controller; never transmits CAN."""
from __future__ import annotations
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT/'build'/('ai-vids.exe' if os.name == 'nt' else 'ai-vids')
lock = threading.Lock()
events = deque(maxlen=600)
status = {'running': False, 'error': None, 'run': 0}


def replay():
    with lock:
        if status['running']:
            return False
        events.clear()
        status.update(running=True, error=None, run=status['run'] + 1)
    def worker():
        try:
            with (ROOT/'runtime'/'events.ndjson').open('w', encoding='utf-8') as log:
                with subprocess.Popen([str(BIN), 'replay', str(ROOT/'data'/'demo.csv'),
                                       str(ROOT/'models'/'demo.forest'), '--realtime'],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                      cwd=ROOT) as proc:
                    for line in proc.stdout:
                        event = json.loads(line)
                        log.write(line);log.flush()
                        with lock:
                            events.append(event)
                    error = proc.stderr.read()
                    if proc.wait():
                        raise RuntimeError(error.strip())
        except Exception as exc:
            with lock:
                status['error'] = str(exc)
        finally:
            with lock:
                status['running'] = False
    threading.Thread(target=worker, daemon=True).start()
    return True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, code, body, content_type='application/json; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/state':
            with lock:
                data = dict(status, events=list(events), mode='LOCAL · SYNTHETIC REPLAY')
            self.respond(200, json.dumps(data).encode())
        elif self.path == '/api/validation':
            self.respond(200, (ROOT/'runtime'/'validation.json').read_bytes())
        elif self.path in ['/', '/index.html']:
            self.respond(200, (ROOT/'ui'/'index.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/architecture.svg':
            self.respond(200, (ROOT/'docs'/'architecture.svg').read_bytes(), 'image/svg+xml')
        elif self.path in ['/review', '/review.html']:
            self.respond(200, (ROOT/'docs'/'TASK_REVIEW.html').read_bytes(), 'text/html; charset=utf-8')
        else:
            self.respond(404, b'{"error":"not found"}')

    def do_POST(self):
        # Require our same-origin UI header; reject cross-site replay triggers.
        if self.headers.get('X-AI-VIDS-Local') != '1':
            self.respond(403, b'{"error":"local UI header required"}')
        elif self.path == '/api/replay':
            started = replay()
            self.respond(200 if started else 409, json.dumps({'started': started}).encode())
        else:
            self.respond(404, b'{"error":"not found"}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not BIN.exists() or not (ROOT/'models'/'demo.forest').exists():
        raise SystemExit('Run tools/prepare.py first.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'AI-VIDS local review: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
