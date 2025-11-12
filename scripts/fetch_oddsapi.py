# -------------------------------------------------
# scripts/fetch_oddsapi.py
# -------------------------------------------------
# Fallback module for NBA player props using The Odds API
# -------------------------------------------------

import os
import json
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load API key from environment (.env) or Streamlit secrets
load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY") or "74bf14afd2c0ee8883e47d044ffe37e2"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"

def fetch_oddsapi_data():
    """
    Fetch NBA player prop odds from The Odds API.
    Returns a normalized pandas DataFrame.
    """
    print("Fetching NBA props from The Odds API...")
    try:
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "player_points,player_rebounds,player_assists,player_threes",
            "oddsFormat": "american"
        }
        response = requests.get(ODDS_API_URL, params=params, timeout=15)
        if response.status_code != 200:
            print(f"⚠️ Odds API request failed: {response.status_code} - {response.text}")
            return pd.DataFrame()

        data = response.json()
        props_list = []

        for game in data:
            home_team = game.get("home_team")
            away_team = game.get("away_team")
            commence_time = game.get("commence_time")

            for bookmaker in game.get("bookmakers", []):
                book = bookmaker.get("title", "")
                for market in bookmaker.get("markets", []):
                    market_key = market.get("key", "")
                    for outcome in market.get("outcomes", []):
                        try:
                            player = outcome.get("name", "").strip()
                            line = outcome.get("point")
                            odds = outcome.get("price")
                            prop_type = (
                                "Points" if "points" in market_key else
                                "Rebounds" if "rebounds" in market_key else
                                "Assists" if "assists" in market_key else
                                "3PM" if "threes" in market_key else
                                market_key
                            )
                            props_list.append({
                                "player": player,
                                "prop_type": prop_type,
                                "line": line,
                                "odds_over": odds,
                                "odds_under": None,
                                "book": book,
                                "game": f"{away_team} @ {home_team}",
                                "source": "The Odds API",
                                "timestamp": datetime.utcnow().isoformat()
                            })
                        except Exception:
                            continue

        df = pd.DataFrame(props_list)
        if df.empty:
            print("⚠️ No props returned from The Odds API.")
            return pd.DataFrame()

        save_path = os.path.join(os.path.dirname(__file__), "..", "data", "odds_snapshot.json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_json(save_path, orient="records", indent=2)
        print(f"✅ Odds API fallback success — {len(df)} props saved.")
        return df

    except Exception as e:
        print(f"❌ Error fetching Odds API data: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    df = fetch_oddsapi_data()
    if not df.empty:
        print(df.head())
    else:
        print("No Odds API data available.")
