"""带 CORS 的静态文件服务器，serve public/ 目录"""
import http.server
import os

PORT = 8888
DIRECTORY = os.path.join(os.path.dirname(__file__), "public")

class CORSHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.send_header("Access-Control-Expose-Headers", "Content-Length, Content-Range")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

print(f"Serving {DIRECTORY} on http://localhost:{PORT} with CORS")
http.server.HTTPServer(("", PORT), CORSHandler).serve_forever()
