# scripts/fetch_fanduel.py
"""
Fetch live FanDuel NBA player prop odds using direct XHR (JSON) endpoints.
- Fast (no Selenium)
- Works with FanDuel public JSON API
- Saves snapshot to ../data/odds_snapshot.json
"""

import os
import json
import time
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

# -----------------------------
# SETUP
# -----------------------------
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_PATH = DATA_DIR / "odds_snapshot.json"

# FanDuel JSON API endpoint (official sportsbook feed)
FANDUEL_API = (
    "https://sportsbook.fanduel.com/api/sportsbook"
    "/sports/basketball/nba?tab=player-props"
)

# headers that mimic a real browser to avoid 403s
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://sportsbook.fanduel.com/",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://sportsbook.fanduel.com",
}

# -----------------------------
# FETCH JSON DIRECTLY
# -----------------------------
def fetch_fanduel_json() -> dict:
    """Request FanDuel NBA player prop odds feed (JSON)."""
    try:
        response = requests.get(FANDUEL_API, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
        data = response.json()
        return data
    except Exception as e:
        print(f"⚠️ FanDuel XHR request failed: {e}")
        return {}

# -----------------------------
# PARSE JSON STRUCTURE
# -----------------------------
def parse_fanduel_json(data: dict) -> pd.DataFrame:
    """
    Parse FanDuel JSON feed into a flat DataFrame of player props.
    """
    if not data:
        return pd.DataFrame()

    props = []
    events = data.get("events") or []
    for event in events:
        game_name = event.get("name", "")
        competitors = [
            c.get("name", "") for c in event.get("competitors", [])
        ]
        markets = event.get("markets") or []
        for market in markets:
            market_name = market.get("name")
            outcomes = market.get("outcomes") or []
            for outcome in outcomes:
                props.append(
                    {
                        "game": game_name,
                        "teams": " vs ".join(competitors),
                        "market": market_name,
                        "player": outcome.get("label") or outcome.get("name"),
                        "price": outcome.get("price", {}).get("decimalDisplay"),
                        "oddsAmerican": outcome.get("price", {}).get("americanDisplay"),
                        "line": outcome.get("line"),
                        "bookmaker": "FanDuel",
                    }
                )

    df = pd.DataFrame(props)
    if not df.empty:
        df.drop_duplicates(inplace=True)
    return df


# -----------------------------
# SAVE SNAPSHOT
# -----------------------------
def save_snapshot(df: pd.DataFrame):
    """Save DataFrame to JSON snapshot for dashboard use."""
    snapshot = {
        "timestamp": int(time.time()),
        "readable_time": datetime.utcnow().isoformat() + "Z",
        "count": len(df),
        "records": df.to_dict(orient="records"),
    }
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    print(f"✅ Saved FanDuel odds snapshot to {SNAPSHOT_PATH}")


# -----------------------------
# MAIN WRAPPER
# -----------------------------
def fetch_fanduel_data() -> pd.DataFrame:
    """
    Fetches live FanDuel player props and returns DataFrame.
    If network or structure fails, returns empty DataFrame.
    """
    print("📡 Fetching FanDuel NBA props (XHR endpoint)...")
    data = fetch_fanduel_json()
    df = parse_fanduel_json(data)
    if df.empty:
        print("⚠️ No FanDuel data found. JSON may have changed or restricted regionally.")
    else:
        print(f"✅ Parsed {len(df)} player props from FanDuel.")
        save_snapshot(df)
    return df


if __name__ == "__main__":
    df = fetch_fanduel_data()
    print(df.head(15))
