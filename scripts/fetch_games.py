# -------------------------------------------------
# scripts/fetch_games.py
# -------------------------------------------------
# Hot Shot Props – Game Fetcher (BallDontLie API Edition)
# Fetches today's NBA games safely via https://api.balldontlie.io
# -------------------------------------------------

import os
import json
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
GAMES_PATH = os.path.join(DATA_DIR, "games_today.json")

BALLDONTLIE_URL = "https://api.balldontlie.io/v1/games"

def fetch_games_today():
    """Fetch today's NBA games from BallDontLie API (EST-corrected)."""
    EST = timezone(timedelta(hours=-5))
    today_est = datetime.now(EST).strftime("%Y-%m-%d")
    print(f"🏀 Fetching NBA games (BallDontLie) for {today_est}...")

    try:
        resp = requests.get(f"{BALLDONTLIE_URL}?dates[]={today_est}", timeout=30)
        if resp.status_code != 200:
            print(f"⚠️ Failed to fetch BallDontLie data: {resp.status_code}")
            return pd.DataFrame()
        data = resp.json().get("data", [])
        if not data:
            print("⚠️ No games returned by BallDontLie.")
            return pd.DataFrame()

        games = []
        for g in data:
            games.append({
                "game_id": g["id"],
                "home_team": g["home_team"]["full_name"],
                "away_team": g["visitor_team"]["full_name"],
                "home_team_abbrev": g["home_team"]["abbreviation"],
                "away_team_abbrev": g["visitor_team"]["abbreviation"],
                "status": g.get("status", "Scheduled"),
                "date": g["date"],
            })

        df = pd.DataFrame(games)
        df.to_json(GAMES_PATH, orient="records", indent=2)
        print(f"✅ Saved {len(df)} games → {GAMES_PATH}")
        return df

    except Exception as e:
        print(f"⚠️ Error fetching games from BallDontLie: {e}")
        return pd.DataFrame()


def load_games_snapshot():
    """Load cached games or fetch fresh if missing/empty."""
    if not os.path.exists(GAMES_PATH) or os.path.getsize(GAMES_PATH) < 10:
        return fetch_games_today()
    try:
        with open(GAMES_PATH, "r") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if df.empty:
            return fetch_games_today()
        return df
    except Exception:
        return fetch_games_today()


if __name__ == "__main__":
    df = fetch_games_today()
    print(df.head())
