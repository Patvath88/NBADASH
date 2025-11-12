# scripts/fetch_games.py
# BallDontLie NBA game schedule (no auth required)
import requests, pandas as pd
from datetime import datetime

def fetch_games_today():
    """Return today's NBA games."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"🏀 Fetching NBA games (BallDontLie) for {today}...")
    try:
        r = requests.get(f"https://api.balldontlie.io/v1/games?dates[]={today}", timeout=10)
        if r.status_code != 200:
            print("⚠️ Failed to fetch BallDontLie data:", r.status_code)
            return pd.DataFrame()
        games = r.json().get("data", [])
        recs = []
        for g in games:
            recs.append({
                "id": g.get("id"),
                "home_team": g.get("home_team", {}).get("full_name"),
                "away_team": g.get("visitor_team", {}).get("full_name"),
                "status": g.get("status"),
                "start_time": g.get("date"),
            })
        return pd.DataFrame(recs)
    except Exception as e:
        print("⚠️ Error fetching games:", e)
        return pd.DataFrame()
