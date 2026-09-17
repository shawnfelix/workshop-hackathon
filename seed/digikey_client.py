"""Minimal Digikey ProductSearch v4 client (OAuth2 client-credentials).

Credentials come from digikey-mcp/.env (CLIENT_ID, CLIENT_SECRET). Never logged.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "digikey-mcp" / ".env")

log = logging.getLogger("digikey")


class RateLimited(Exception):
    pass


class DigikeyClient:
    def __init__(self, sandbox: bool = False, locale_site: str = "US", currency: str = "USD"):
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise ValueError("CLIENT_ID / CLIENT_SECRET not set (expected in digikey-mcp/.env)")
        host = "https://sandbox-api.digikey.com" if sandbox else "https://api.digikey.com"
        self.token_url = f"{host}/v1/oauth2/token"
        self.api_base = f"{host}/products/v4"
        self.env_name = "SANDBOX" if sandbox else "PRODUCTION"
        self.locale_site = locale_site
        self.currency = currency
        self._token: str | None = None
        self._token_expiry = 0.0
        self.calls = 0
        self.min_interval = 0.6  # seconds between calls; prod tier is rate limited
        self._last_call = 0.0

    # ---------- auth ----------
    def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        resp = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Digikey OAuth failed: HTTP {resp.status_code}")
        body = resp.json()
        self._token = body["access_token"]
        self._token_expiry = time.time() + int(body.get("expires_in", 600))
        log.info("Obtained Digikey token (%s)", self.env_name)
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._ensure_token()}",
            "X-DIGIKEY-Client-Id": self.client_id,
            "Content-Type": "application/json",
            "X-DIGIKEY-Locale-Site": self.locale_site,
            "X-DIGIKEY-Locale-Language": "en",
            "X-DIGIKEY-Locale-Currency": self.currency,
            "X-DIGIKEY-Customer-Id": "0",
        }

    # ---------- transport ----------
    def _request(self, method: str, path: str, json: dict | None = None, retries: int = 3) -> dict:
        url = f"{self.api_base}{path}"
        for attempt in range(retries + 1):
            wait = self.min_interval - (time.time() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()
            self.calls += 1
            resp = requests.request(method, url, headers=self._headers(), json=json, timeout=60)
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining is not None:
                log.debug("rate-limit remaining: %s", remaining)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                delay = float(resp.headers.get("Retry-After", 5 * (attempt + 1)))
                log.warning("429 rate limited; sleeping %.0fs (attempt %d)", delay, attempt + 1)
                time.sleep(delay)
                continue
            if resp.status_code == 401 and attempt == 0:
                self._token = None  # force refresh once
                continue
            raise RuntimeError(f"Digikey API {method} {path} -> HTTP {resp.status_code}: {resp.text[:300]}")
        raise RateLimited(f"Gave up after {retries} retries on {path}")

    # ---------- endpoints ----------
    def keyword_search(
        self,
        keywords: str,
        limit: int = 25,
        offset: int = 0,
        in_stock: bool = True,
        category_ids: list[int] | None = None,
        manufacturer_ids: list[int] | None = None,
        sort_by_quantity: bool = True,
    ) -> dict:
        body: dict = {"Keywords": keywords, "Limit": min(limit, 50), "Offset": offset}
        filters: dict = {"MarketPlaceFilter": "ExcludeMarketPlace"}
        if in_stock:
            filters["SearchOptions"] = ["InStock"]
        if category_ids:
            filters["CategoryFilter"] = [{"Id": str(c)} for c in category_ids]
        if manufacturer_ids:
            filters["ManufacturerFilter"] = [{"Id": str(m)} for m in manufacturer_ids]
        body["FilterOptionsRequest"] = filters
        if sort_by_quantity:
            body["SortOptions"] = {"Field": "QuantityAvailable", "SortOrder": "Descending"}
        return self._request("POST", "/search/keyword", json=body)

    def product_details(self, product_number: str) -> dict:
        return self._request("GET", f"/search/{requests.utils.quote(product_number, safe='')}/productdetails")

    def substitutions(self, product_number: str, limit: int = 10) -> dict:
        return self._request(
            "GET",
            f"/search/{requests.utils.quote(product_number, safe='')}/substitutions?limit={limit}&excludeMarketPlaceProducts=true",
        )
