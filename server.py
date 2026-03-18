#!/usr/bin/env python3
"""LARA — Backend proxy for Google Places API"""

import http.server
import json
import os
import urllib.request
import urllib.parse
import urllib.error

PORT = int(os.environ.get("PORT", 8080))
PLACES_KEY = "AIzaSyCzdhnOZw0P95391IzXUZ7L-X_u-V3xofQ"

class LaraHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/api/search":
            self._proxy_search(qs)
        elif parsed.path == "/api/details":
            self._proxy_details(qs)
        elif parsed.path == "/":
            self.path = "/index.html"
            return super().do_GET()
        else:
            return super().do_GET()

    def _proxy_search(self, qs):
        try:
            if "pagetoken" in qs:
                token = qs["pagetoken"][0]
                url = (
                    "https://maps.googleapis.com/maps/api/place/textsearch/json"
                    f"?pagetoken={urllib.parse.quote(token)}"
                    f"&key={PLACES_KEY}"
                )
            elif "query" in qs:
                query = qs["query"][0]
                url = (
                    "https://maps.googleapis.com/maps/api/place/textsearch/json"
                    f"?query={urllib.parse.quote(query)}"
                    f"&language=pt-BR"
                    f"&key={PLACES_KEY}"
                )
            else:
                self._json_response(400, {"error": "Missing query or pagetoken"})
                return

            data = self._fetch(url)
            self._json_response(200, data)

        except Exception as e:
            self._json_response(500, {"error": str(e)})

    def _proxy_details(self, qs):
        try:
            place_id = qs.get("place_id", [None])[0]
            if not place_id:
                self._json_response(400, {"error": "Missing place_id"})
                return

            url = (
                "https://maps.googleapis.com/maps/api/place/details/json"
                f"?place_id={urllib.parse.quote(place_id)}"
                f"&fields=formatted_phone_number,international_phone_number,website"
                f"&language=pt-BR"
                f"&key={PLACES_KEY}"
            )

            data = self._fetch(url)
            self._json_response(200, data)

        except Exception as e:
            self._json_response(500, {"error": str(e)})

    def _fetch(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "LARA/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _json_response(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Clean log format
        print(f"[LARA] {args[0]}" if args else "")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(("", PORT), LaraHandler)
    print(f"[LARA] Server running on http://localhost:{PORT}")
    server.serve_forever()
