"""Loopback-only static UI and bounded read-only analysis API."""
import os
os.environ.setdefault("OTRECON_FORCE_RUPTURES", "1")

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit, parse_qs
import microscope
from live_service import LiveService

PUBLIC = Path(__file__).resolve().parent / "public/fork-microscope"
COMPUTE = threading.BoundedSemaphore(2)
FIELDS = {"row", "samples", "stride", "shift", "start", "end", "draw_start"}
LIVE = LiveService()


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        if "/api/live/status" not in self.path:
            super().log_message(format, *args)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def json_response(self, status, body):
        data = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.headers.get("Host", "") not in {f"127.0.0.1:{self.server.server_port}",f"localhost:{self.server.server_port}"}:
            return self.json_response(403,{"error":"Use the localhost address."})
        parsed = urlsplit(self.path)
        if parsed.path == "/": self.path = "/live.html"
        if parsed.path.startswith("/api/live/"):
            try:
                if parsed.path == "/api/live/status" and not parsed.query:
                    return self.json_response(200, LIVE.status())
                if parsed.path == "/api/live/runs" and not parsed.query:
                    return self.json_response(200, LIVE.results())
                if parsed.path in ("/api/live/result", "/api/live/export"):
                    q=parse_qs(parsed.query)
                    if set(q)!={"id"} or len(q["id"])!=1: raise ValueError("Provide one run ID.")
                    return self.json_response(200,LIVE.result(q["id"][0],raw=parsed.path.endswith("export")))
                raise ValueError("Unknown live endpoint.")
            except ValueError as exc:
                return self.json_response(400,{"error":str(exc)})
        if parsed.path.startswith("/api/"):
            if len(parsed.query) > 1024:
                return self.json_response(400, {"error": "Query is too long."})
            try:
                query = parse_qs(parsed.query, keep_blank_values=True)
                if any(len(v) != 1 or not re.fullmatch(r"-?\d{1,6}", v[0]) for v in query.values()):
                    raise ValueError("Use one whole-number value per setting.")
                params = {k: int(v[0]) for k, v in query.items()}
                if parsed.path == "/api/questions" and not params:
                    return self.json_response(200, microscope.catalog())
                if parsed.path == "/api/question" and set(params) == {"row"}:
                    return self.json_response(200, microscope.metadata(params["row"]))
                if parsed.path == "/api/analyze" and set(params) == FIELDS:
                    if not COMPUTE.acquire(timeout=5):
                        return self.json_response(503, {"error": "Analysis is busy. Try again in a moment."})
                    try:
                        result = microscope.analyze(params)
                    finally:
                        COMPUTE.release()
                    return self.json_response(200, result)
                raise ValueError("Unknown endpoint or unexpected settings.")
            except ValueError as exc:
                return self.json_response(400, {"error": str(exc)})
            except Exception:
                return self.json_response(500, {"error": "Reconstruction failed for these settings. Try a wider region."})
        if parsed.path not in ("/", "/index.html", "/app.js", "/math.mjs", "/passes.mjs", "/graph-evidence.mjs", "/styles.css", "/plotly.min.js", "/live.html", "/live.js", "/live.css"):
            return self.send_error(404)
        super().do_GET()

    def do_POST(self):
        # Only same-origin JSON may trigger downloads or model computation.
        allowed={f"127.0.0.1:{self.server.server_port}",f"localhost:{self.server.server_port}"}
        host=self.headers.get("Host", "")
        origin=self.headers.get("Origin")
        if host not in allowed or (origin and origin != f"http://{host}"):
            return self.json_response(403,{"error":"Use this dashboard from its localhost address."})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.json_response(415,{"error":"JSON requests are required."})
        try:
            size=int(self.headers.get("Content-Length", "0"))
            if not 0<size<=65536: raise ValueError("Invalid request size.")
            payload=json.loads(self.rfile.read(size))
            route=urlsplit(self.path)
            if route.query: raise ValueError("Unexpected query string.")
            if route.path == "/api/live/estimate":
                with LIVE.lock:
                    if LIVE.job["status"]=="running": raise ValueError("Wait for the current job before estimating.")
                    estimate = LIVE.estimate(payload)
                return self.json_response(200,estimate)
            if route.path == "/api/live/stop":
                if payload!={}: raise ValueError("Stop takes an empty object.")
                return self.json_response(200,LIVE.cancel())
            if route.path in ("/api/live/load","/api/live/base","/api/live/run","/api/live/unload"):
                return self.json_response(202,LIVE.start(route.path.rsplit("/",1)[-1],payload))
            raise ValueError("Unknown action.")
        except (ValueError,TypeError) as exc:
            return self.json_response(400,{"error":str(exc)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Fork microscope: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
