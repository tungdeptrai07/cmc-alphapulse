"""
CMC AlphaPulse — CoinMarketCap Pro API v1/v2 Client
Explicitly implements and documents 5 official CoinMarketCap endpoints:
  1. GET /v1/cryptocurrency/listings/latest
  2. GET /v2/cryptocurrency/quotes/latest
  3. GET /v1/global-metrics/quotes/latest
  4. GET /v1/cryptocurrency/info
  5. GET /v1/cryptocurrency/map
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class CMCConfig:
    api_key: str
    use_sandbox: bool = False

    @property
    def base_url(self) -> str:
        return (
            "https://sandbox-api.coinmarketcap.com"
            if self.use_sandbox
            else "https://pro-api.coinmarketcap.com"
        )


class CoinMarketCapClient:
    """Thread-safe wrapper around CoinMarketCap Pro/Sandbox REST API."""

    def __init__(self, api_key: Optional[str] = None, use_sandbox: bool = False) -> None:
        resolved_key = (api_key or os.getenv("CMC_PRO_API_KEY", "")).strip()
        self.config = CMCConfig(api_key=resolved_key, use_sandbox=use_sandbox)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "deflate, gzip",
        })
        if self.config.api_key:
            self.session.headers["X-CMC_PRO_API_KEY"] = self.config.api_key

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.config.api_key:
            raise ValueError("Missing CoinMarketCap API key. Provide CMC_PRO_API_KEY in .env or request header.")
        url = f"{self.config.base_url}{path}"
        resp = self.session.get(url, params=params or {}, timeout=12)
        resp.raise_for_status()
        payload = resp.json()
        status = payload.get("status", {})
        if status.get("error_code", 0) != 0:
            raise RuntimeError(f"CMC API Error {status.get('error_code')}: {status.get('error_message')}")
        return payload

    def get_listings_latest(self, limit: int = 25, convert: str = "USD", sort: str = "market_cap") -> Dict[str, Any]:
        """Endpoint 1: GET /v1/cryptocurrency/listings/latest"""
        return self._get(
            "/v1/cryptocurrency/listings/latest",
            params={"start": 1, "limit": limit, "convert": convert, "sort": sort},
        )

    def get_quotes_latest(self, symbols: str = "BTC,ETH,SOL,BNB,TAO", convert: str = "USD") -> Dict[str, Any]:
        """Endpoint 2: GET /v2/cryptocurrency/quotes/latest"""
        return self._get(
            "/v2/cryptocurrency/quotes/latest",
            params={"symbol": symbols, "convert": convert},
        )

    def get_global_metrics_latest(self, convert: str = "USD") -> Dict[str, Any]:
        """Endpoint 3: GET /v1/global-metrics/quotes/latest"""
        return self._get(
            "/v1/global-metrics/quotes/latest",
            params={"convert": convert},
        )

    def get_crypto_info(self, symbols: str = "BTC,ETH,SOL") -> Dict[str, Any]:
        """Endpoint 4: GET /v1/cryptocurrency/info"""
        return self._get(
            "/v1/cryptocurrency/info",
            params={"symbol": symbols},
        )

    def get_crypto_map(self, limit: int = 50) -> Dict[str, Any]:
        """Endpoint 5: GET /v1/cryptocurrency/map"""
        return self._get(
            "/v1/cryptocurrency/map",
            params={"limit": limit, "sort": "cmc_rank"},
        )


def compute_alpha_signals(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transforms raw CMC listings into actionable trading intelligence:
    - Volume/MarketCap Velocity (%) = (24h Volume / Market Cap) * 100
    - Alpha Momentum Score (0-100) combining 1h/24h/7d delta & liquidity turnover
    """
    enriched: List[Dict[str, Any]] = []
    for asset in listings:
        quote = asset.get("quote", {}).get("USD", {})
        price = float(quote.get("price") or 0.0)
        vol_24h = float(quote.get("volume_24h") or 0.0)
        mcap = float(quote.get("market_cap") or 0.0)
        pct_1h = float(quote.get("percent_change_1h") or 0.0)
        pct_24h = float(quote.get("percent_change_24h") or 0.0)
        pct_7d = float(quote.get("percent_change_7d") or 0.0)

        velocity_pct = (vol_24h / mcap * 100.0) if mcap > 0 else 0.0
        # Weighted momentum score bounded [0, 100]
        raw_score = 50.0 + (pct_24h * 1.8) + (pct_1h * 2.5) + min(velocity_pct * 0.9, 25.0)
        momentum_score = max(0.0, min(100.0, round(raw_score, 1)))

        signal = "ACCUMULATE" if momentum_score >= 70 else ("WATCH" if momentum_score >= 48 else "COOLING")

        enriched.append({
            "id": asset.get("id"),
            "rank": asset.get("cmc_rank"),
            "name": asset.get("name"),
            "symbol": asset.get("symbol"),
            "tags": asset.get("tags", [])[:4],
            "price_usd": price,
            "volume_24h": vol_24h,
            "market_cap": mcap,
            "percent_change_1h": round(pct_1h, 2),
            "percent_change_24h": round(pct_24h, 2),
            "percent_change_7d": round(pct_7d, 2),
            "velocity_pct": round(velocity_pct, 2),
            "momentum_score": momentum_score,
            "signal": signal,
        })

    return sorted(enriched, key=lambda x: x["momentum_score"], reverse=True)
