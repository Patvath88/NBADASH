import requests
import pandas as pd
from datetime import date

def fetch_games_today():
    """Fetch today's NBA games from BallDontLie."""
    try:
        today = date.today().strftime("%Y-%m-%d")
        url = f"https://api.balldontlie.io/v1/games?dates[]={today}"
        headers = {"Authorization": "69e7de67-01fa-4285-8e2f-21e3d8394fd3"}
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return pd.DataFrame()

        data = r.json().get("data", [])
        games = []
        for g in data:
            games.append({
                "home_team": g["home_team"]["full_name"],
                "visitor_team": g["visitor_team"]["full_name"],
                "status": g["status"],
                "start_time": g["date"]
            })
        return pd.DataFrame(games)
    except Exception as e:
        print("Game fetch error:", e)
        return pd.DataFrame()
