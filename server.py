"""
CMC AlphaPulse Local Server & CORS Proxy
Serves the web dashboard and proxies live CoinMarketCap API calls cleanly
without exposing API keys in static frontend code.
"""

from __future__ import annotations

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from cmc_client import CoinMarketCapClient, compute_alpha_signals

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))


class AlphaPulseHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/cmc/"):
            self._handle_cmc_api(parsed)
            return
        super().do_GET()

    def _handle_cmc_api(self, parsed) -> None:
        qs = parse_qs(parsed.query)
        api_key = (
            self.headers.get("X-CMC-API-Key")
            or qs.get("apiKey", [""])[0]
            or os.getenv("CMC_PRO_API_KEY", "")
        ).strip()
        use_sandbox = qs.get("sandbox", ["false"])[0].lower() == "true"

        if not api_key:
            self._send_json(400, {
                "error": "No CMC API key provided. Enter your CoinMarketCap key in the UI or .env file."
            })
            return

        client = CoinMarketCapClient(api_key=api_key, use_sandbox=use_sandbox)
        try:
            if parsed.path == "/api/cmc/screener":
                limit = int(qs.get("limit", ["20"])[0])
                raw = client.get_listings_latest(limit=limit)
                signals = compute_alpha_signals(raw.get("data", []))
                self._send_json(200, {
                    "endpoint": "/v1/cryptocurrency/listings/latest",
                    "credit_count": raw.get("status", {}).get("credit_count", 1),
                    "timestamp": raw.get("status", {}).get("timestamp"),
                    "signals": signals,
                    "raw_sample": raw.get("data", [])[:2],
                })
            elif parsed.path == "/api/cmc/global":
                raw = client.get_global_metrics_latest()
                self._send_json(200, {
                    "endpoint": "/v1/global-metrics/quotes/latest",
                    "status": raw.get("status"),
                    "data": raw.get("data"),
                })
            elif parsed.path == "/api/cmc/quotes":
                symbols = qs.get("symbols", ["BTC,ETH,SOL,TAO,LINK"])[0]
                raw = client.get_quotes_latest(symbols=symbols)
                self._send_json(200, {
                    "endpoint": "/v2/cryptocurrency/quotes/latest",
                    "status": raw.get("status"),
                    "data": raw.get("data"),
                })
            else:
                self._send_json(404, {"error": f"Unknown API route: {parsed.path}"})
        except Exception as exc:
            self._send_json(502, {"error": str(exc)})


def run_server(port: int = 8083) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), AlphaPulseHandler)
    print(f"CMC AlphaPulse running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server(int(os.getenv("PORT", "8083")))
