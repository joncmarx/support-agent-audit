"""Local demo server for recording the video. Serves site/index.html and runs the final bot (v4) live.

  python3 -m audit.serve          then open http://localhost:8765

It uses your OpenRouter key from ~/Keys (see audit/llm.py) and only listens on this computer (127.0.0.1)."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import llm
from .bot import answer
from .common import ROOT
from .docs_index import Docs

PORT = 8765
DOCS = Docs()
MODEL = "openai/gpt-5.4-mini"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, (ROOT / "site" / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/health":
            return self._send(200, {"ok": True})
        self._send(404, {"error": "Not found."})

    def do_POST(self):
        if self.path != "/api/ask":
            return self._send(404, {"error": "Not found."})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            q = {"id": 0, "title": str(body.get("title", ""))[:200], "question": str(body.get("question", ""))[:8000]}
            if not q["question"].strip():
                return self._send(400, {"error": "Type a question first."})
            r = answer(llm.chat, MODEL, DOCS, q, "v4")
            self._send(200, {k: r.get(k) for k in ("answer", "triage", "draft", "review_safe", "review_problem", "cost")})
        except Exception as e:
            self._send(500, {"error": f"The bot call failed: {e}"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"Open http://localhost:{PORT} in your browser. Press Control-C here to stop.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
