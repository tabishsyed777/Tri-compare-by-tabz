"""Zero-dependency web server: python -m tripcompare.server  ->  http://127.0.0.1:8000
For production, wrap `service.search` in FastAPI/Flask/Next.js API routes (see docs/HANDOFF.md)."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .service import search

WEB = Path(__file__).parent / "web"


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (WEB / "index.html").read_bytes(), "text/html")
        elif self.path == "/health":
            self._send(200, '{"status":"ok"}')
        else:
            self._send(404, '{"error":"not found"}')

    def do_POST(self):
        if self.path != "/api/search":
            return self._send(404, '{"error":"not found"}')
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 10_000: raise ValueError("request too large")
            q = json.loads(self.rfile.read(n) or b"{}").get("query", "")
            if not isinstance(q, str) or not q.strip() or len(q) > 300: raise ValueError("query must be 1-300 characters")
            self._send(200, json.dumps(search(q.strip())))
        except Exception as e:          # never leak stack traces
            self._send(400, json.dumps({"ok": False, "errors": [str(e)]}))

    def log_message(self, *a): pass


def main(host="127.0.0.1", port=8000):
    print(f"Serving on http://{host}:{port}")
    ThreadingHTTPServer((host, port), H).serve_forever()


if __name__ == "__main__":
    main()
