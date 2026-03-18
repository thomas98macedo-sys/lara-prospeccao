#!/usr/bin/env python3
"""LARA — Backend proxy for Google Places API + Stripe"""

import http.server
import json
import os
import urllib.request
import urllib.parse
import urllib.error

import stripe

PORT = int(os.environ.get("PORT", 8080))
PLACES_KEY = "AIzaSyCzdhnOZw0P95391IzXUZ7L-X_u-V3xofQ"

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

MONTHLY_PRICE_ID = "price_1TCCFVRsd1817j5Hu5uRDc8P"
QUARTERLY_PRICE_ID = "price_1TCCFjRsd1817j5Hz8QOBOeL"

stripe.api_key = STRIPE_SECRET_KEY


class LaraHandler(http.server.SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/api/search":
            self._proxy_search(qs)
        elif parsed.path == "/api/details":
            self._proxy_details(qs)
        elif parsed.path == "/api/config":
            self._get_config()
        elif parsed.path == "/api/verify-session":
            self._verify_session(qs)
        elif parsed.path == "/":
            self.path = "/index.html"
            return super().do_GET()
        else:
            return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""

        if parsed.path == "/api/create-checkout-session":
            self._create_checkout_session(body)
        elif parsed.path == "/api/create-portal-session":
            self._create_portal_session(body)
        else:
            self._json_response(404, {"error": "Not found"})

    # ── Stripe Endpoints ──

    def _get_config(self):
        self._json_response(200, {
            "publishableKey": STRIPE_PUBLISHABLE_KEY,
            "monthlyPriceId": MONTHLY_PRICE_ID,
            "quarterlyPriceId": QUARTERLY_PRICE_ID,
        })

    def _create_checkout_session(self, body):
        try:
            data = json.loads(body) if body else {}
            price_id = data.get("price_id")
            user_email = data.get("email", "")
            user_uid = data.get("uid", "")

            if price_id not in (MONTHLY_PRICE_ID, QUARTERLY_PRICE_ID):
                self._json_response(400, {"error": "Invalid price_id"})
                return

            origin = self.headers.get("Origin") or self.headers.get("Referer", "").rstrip("/")
            if not origin:
                origin = "https://lara-prospeccao.onrender.com"

            session = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                customer_email=user_email,
                client_reference_id=user_uid,
                success_url=f"{origin}?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{origin}?checkout=cancel",
                metadata={"uid": user_uid},
            )

            self._json_response(200, {"url": session.url})

        except Exception as e:
            print(f"[LARA] Checkout error: {e}")
            self._json_response(500, {"error": str(e)})

    def _create_portal_session(self, body):
        try:
            data = json.loads(body) if body else {}
            customer_id = data.get("customer_id", "")

            if not customer_id:
                self._json_response(400, {"error": "Missing customer_id"})
                return

            origin = self.headers.get("Origin") or "https://lara-prospeccao.onrender.com"

            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=origin,
            )

            self._json_response(200, {"url": session.url})

        except Exception as e:
            print(f"[LARA] Portal error: {e}")
            self._json_response(500, {"error": str(e)})

    def _verify_session(self, qs):
        try:
            session_id = qs.get("session_id", [None])[0]
            if not session_id:
                self._json_response(400, {"error": "Missing session_id"})
                return

            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                self._json_response(200, {
                    "status": "active",
                    "customer_id": session.customer,
                    "subscription_id": session.subscription,
                })
            else:
                self._json_response(200, {"status": session.payment_status})

        except Exception as e:
            print(f"[LARA] Verify session error: {e}")
            self._json_response(500, {"error": str(e)})

    # ── Google Places Proxy ──

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

    # ── Helpers ──

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
        print(f"[LARA] {args[0]}" if args else "")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(("", PORT), LaraHandler)
    print(f"[LARA] Server running on http://localhost:{PORT}")
    print(f"[LARA] Stripe: {'configured' if STRIPE_SECRET_KEY else 'NOT configured (set STRIPE_SECRET_KEY)'}")
    server.serve_forever()
