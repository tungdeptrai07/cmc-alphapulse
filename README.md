# CMC AlphaPulse — Real-Time Market Velocity Screener & AI Agent Signal Engine

**Hackathon Submission:** Build with CMC: API Hackathon (Plushie) on DoraHacks  
**Selected Track:** Markets and Trading Tools  
**Hashtag:** `#BuildwithCMC`

---

## 1. Overview
**CMC AlphaPulse** is a trading intelligence terminal and market screener powered by the **CoinMarketCap Pro API**. Instead of displaying raw static prices, AlphaPulse calculates **Liquidity Velocity** (`24h Volume / Market Cap`) and a composite **Alpha Momentum Score (0–100)** to detect high-conviction capital rotation across L1s, DeFi, AI/DePIN, and RWAs.

---

## 2. Explicit CoinMarketCap API Endpoints Used
Implemented cleanly in [`backend/cmc_client.py`](backend/cmc_client.py) and served via the local CORS proxy [`backend/server.py`](backend/server.py):

1. `GET /v1/cryptocurrency/listings/latest` — Pulls ranked asset prices, 1h/24h/7d performance, 24h spot volume, and market cap for velocity scoring.
2. `GET /v2/cryptocurrency/quotes/latest` — Polls targeted watchlist symbols for automated AI alert evaluation.
3. `GET /v1/global-metrics/quotes/latest` — Tracks macro total market cap, BTC/ETH dominance, and DeFi volume share.
4. `GET /v1/cryptocurrency/info` — Fetches token metadata, official URLs, and sector tags.
5. `GET /v1/cryptocurrency/map` — Resolves canonical CMC IDs to eliminate ticker symbol collisions.

---

## 3. Visible Evidence of Real API Call Implementation
```python
from backend.cmc_client import CoinMarketCapClient, compute_alpha_signals

client = CoinMarketCapClient(api_key=os.getenv("CMC_PRO_API_KEY"))
raw_response = client.get_listings_latest(limit=20, convert="USD")
signals = compute_alpha_signals(raw_response["data"])
```
Sample structured response emitted by `/api/cmc/screener`:
```json
{
  "endpoint": "/v1/cryptocurrency/listings/latest",
  "credit_count": 1,
  "signals": [
    {
      "rank": 64,
      "symbol": "NOS",
      "price_usd": 4.18,
      "velocity_pct": 13.94,
      "momentum_score": 88.7,
      "signal": "ACCUMULATE"
    }
  ]
}
```
*(Note: No API keys are committed in this repository. Copy `.env.example` to `.env` or enter your key directly in the dashboard header.)*

---

## 4. Short CoinMarketCap API Feedback
- **What worked well:** Normalized `quote.USD` fields across `/v1/cryptocurrency/listings/latest` and `/v1/global-metrics/quotes/latest` allowed rapid calculation of cross-market liquidity velocity in just 1–2 API credits per refresh.
- **Where friction occurred:**
  1. Direct frontend browser calls to `pro-api.coinmarketcap.com` are blocked by CORS (requiring a lightweight backend proxy like `backend/server.py`).
  2. Supporting a native server-side sector/category filter directly on `/v1/cryptocurrency/listings/latest` would reduce payload size and credit waste when screening niche sectors like RWA or DePIN.

---

## 5. Run Locally
```bash
pip install -r requirements.txt
cp .env.example .env
python backend/server.py
```
Then open `http://127.0.0.1:8083`.
