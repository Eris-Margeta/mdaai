"""Loopback-only preview with clean routes and genuine 404 responses."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent / 'dist'


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        request = unquote(urlsplit(self.path).path)
        candidate = (ROOT / request.lstrip('/')).resolve()
        if not candidate.is_relative_to(ROOT.resolve()) or '..' in request.split('/'):
            return self.not_found()
        if candidate.is_dir() and (candidate / 'index.html').is_file():
            if not request.endswith('/'):
                self.send_response(308)
                self.send_header('Location', request + '/' + ('?' + urlsplit(self.path).query if urlsplit(self.path).query else ''))
                self.end_headers()
                return None
        elif not candidate.is_file():
            return self.not_found()
        return super().send_head()

    def not_found(self):
        data = (ROOT / '404.html').read_bytes()
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)
        return None

    def list_directory(self, path):
        return self.not_found()

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', (Path(__file__).resolve().parent / 'csp-header.conf').read_text().split('"')[1])
        super().end_headers()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8770)
    args = parser.parse_args()
    if not (ROOT / 'index.html').is_file():
        parser.error('Build first: python3 -B website/build.py')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(ROOT)))
    print(f'MDAAI: http://127.0.0.1:{args.port}', flush=True)
    server.serve_forever()
