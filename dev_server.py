import http.server
import socketserver
import json
import os
import mimetypes
import urllib.request
import urllib.error
import urllib.parse

PORT = 8000
# Ensure we are pointing to the correct absolute path for web directory
WEB_DIR = os.path.join(os.getcwd(), 'web')
POSTGREST_BASE = os.getenv('POSTGREST_BASE', 'http://localhost:5000')

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Handle root path
        request_path = self.path.split('?')[0]
        if request_path == '/':
            request_path = '/index.html'
        
        # API Routes (proxy to PostgREST)
        if request_path.startswith('/api/'):
            self.handle_api_proxy('GET')
            return

        # Static File Serving
        # Remove leading slash to join correctly
        clean_path = request_path.lstrip('/')
        file_path = os.path.join(WEB_DIR, clean_path)
        
        # Security check: ensure the resolved path is within WEB_DIR
        # (Basic check for this dev tool)
        if not os.path.abspath(file_path).startswith(WEB_DIR):
            self.send_error(403, "Access Denied")
            return

        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            # Guess mime type
            ctype, _ = mimetypes.guess_type(file_path)
            if ctype:
                self.send_header('Content-type', ctype)
            # Add CORS headers just in case
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            except Exception as e:
                print(f"Error serving file: {e}")
        else:
            print(f"404 Not Found: {file_path}")
            self.send_error(404, "File not found")

    def handle_api_proxy(self, method):
        # Forward /api/... directly to backend base
        target_path = self.path
        url = urllib.parse.urljoin(POSTGREST_BASE, target_path)
        try:
            headers = {
                'Content-Type': self.headers.get('Content-Type', 'application/json'),
                'Accept': 'application/json'
            }
            if method == 'GET':
                req = urllib.request.Request(url, headers=headers, method='GET')
                resp = urllib.request.urlopen(req)
                data = resp.read()
                status = resp.getcode()
            elif method == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length) if content_length > 0 else b''
                req = urllib.request.Request(url, data=body, headers=headers, method='POST')
                resp = urllib.request.urlopen(req)
                data = resp.read()
                status = resp.getcode()
            else:
                self.send_error(405, "Method Not Allowed")
                return
            self.send_response(status)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                err = e.read()
            except Exception:
                err = json.dumps({'error': str(e)}).encode()
            self.wfile.write(err)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            data = {}
        
        response_data = {}
        status_code = 200
        request_path = self.path.split('?')[0]

        # Proxy all /api/* POST requests to PostgREST
        if request_path.startswith('/api/'):
            self.handle_api_proxy('POST')
            return
        else:
            status_code = 404
            response_data = {"message": "Endpoint not found"}
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == "__main__":
    print(f"Starting Dev Server at http://localhost:{PORT}")
    print(f"Serving files from {WEB_DIR}")
    # Allow address reuse to avoid 'Address already in use' errors on restart
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
