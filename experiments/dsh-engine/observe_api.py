"""Record the actual DSH wire traffic without changing requests or scheduling."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid


ROOT = Path('/home/Liangyijia_Hu/dsh-lab')
OUTPUT = ROOT/'artifacts/wire'
UPSTREAM = 'http://127.0.0.1:18082'


class Observer(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.forward()

    def do_POST(self):
        self.forward()

    def forward(self):
        call = str(time.time_ns())+'-'+uuid.uuid4().hex[:8]
        directory = OUTPUT/call
        directory.mkdir(parents=True)
        data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        (directory/'request.body').write_bytes(data)
        request_info = {'call_id': call, 'started_wall_time': time.time(), 'method': self.command,
                        'path': self.path, 'headers': {k: v for k, v in self.headers.items()
                                                     if k.lower() not in ('authorization', 'cookie')}}
        (directory/'request.json').write_text(json.dumps(request_info, indent=2), encoding='utf-8')
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ('host', 'connection', 'content-length')}
        request = urllib.request.Request(UPSTREAM+self.path, data=data if data else None,
                                         headers=headers, method=self.command)
        start = time.monotonic()
        first = None
        try:
            try:
                response = urllib.request.urlopen(request, timeout=240)
            except urllib.error.HTTPError as error:
                response = error
            with response, (directory/'response.body').open('wb') as output:
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in ('connection', 'transfer-encoding', 'server', 'date'):
                        self.send_header(key, value)
                self.end_headers()
                while chunk := response.read1(65536):
                    if first is None:
                        first = time.monotonic()-start
                    output.write(chunk)
                    output.flush()
                    self.wfile.write(chunk)
                    self.wfile.flush()
                info = {'status': response.status, 'duration_seconds': time.monotonic()-start,
                        'first_body_seconds': first, 'headers': dict(response.headers)}
        except (OSError, urllib.error.URLError) as error:
            info = {'error': repr(error), 'duration_seconds': time.monotonic()-start}
        (directory/'response.json').write_text(json.dumps(info, indent=2), encoding='utf-8')


if __name__ == '__main__':
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 18083), Observer)
    print('Observation endpoint http://127.0.0.1:18083 -> '+UPSTREAM, flush=True)
    server.serve_forever()
