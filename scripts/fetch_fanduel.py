# -------------------------------------------------
# scripts/fetch_fanduel.py
# -------------------------------------------------
# Hot Shot Props – OddsAPI integration for NBA props
# Uses your OddsAPI key to fetch live NBA player prop lines.
# -------------------------------------------------

import os
import json
import pandas as pd
import requests
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
ODDS_PATH = os.path.join(DATA_DIR, "odds_snapshot.json")

ODDS_API_KEY = "74bf14afd2c0ee8883e47d044ffe37e2"
ODDS_API_URL = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds?regions=us&markets=player_points,player_rebounds,player_assists,player_threes&oddsFormat=american&apiKey={ODDS_API_KEY}"

def fetch_fanduel_data():
    """Fetch live NBA player props via OddsAPI."""
    print("📊 Fetching NBA player props (OddsAPI)...")
    try:
        resp = requests.get(ODDS_API_URL, timeout=30)
        if resp.status_code != 200:
            print(f"⚠️ OddsAPI error: {resp.status_code} {resp.text}")
            return pd.DataFrame()

        data = resp.json()
        if not data:
            print("⚠️ No odds data returned from OddsAPI.")
            return pd.DataFrame()

        records = []
        for event in data:
            game = event.get("home_team", "") + " vs " + event.get("away_team", "")
            for bookmaker in event.get("bookmakers", []):
                if bookmaker.get("key") != "fanduel":
                    continue
                for market in bookmaker.get("markets", []):
                    prop_type = market["key"]
                    for outcome in market.get("outcomes", []):
                        records.append({
                            "player": outcome.get("name"),
                            "prop_type": prop_type.replace("player_", "").upper(),
                            "line": outcome.get("point"),
                            "odds": outcome.get("price"),
                            "game": game
                        })

        df = pd.DataFrame(records)
        if df.empty:
            print("⚠️ No FanDuel markets found in OddsAPI response.")
            return df

        df["timestamp"] = datetime.utcnow().isoformat()
        df.to_json(ODDS_PATH, orient="records", indent=2)
        print(f"✅ Saved {len(df)} FanDuel props → {ODDS_PATH}")
        return df

    except Exception as e:
        print(f"⚠️ Error fetching OddsAPI data: {e}")
        return pd.DataFrame()

def load_fanduel_snapshot():
    """Load cached snapshot or rebuild."""
    if not os.path.exists(ODDS_PATH) or os.path.getsize(ODDS_PATH) < 10:
        return fetch_fanduel_data()
    try:
        with open(ODDS_PATH, "r") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if df.empty:
            return fetch_fanduel_data()
        return df
    except Exception:
        return fetch_fanduel_data()
