# -------------------------------------------------
# scripts/fetch_player_stats.py
# -------------------------------------------------
# Fetches player game logs + calculates hit rates
# Used by Player Prop Analyzer and model feature building
# -------------------------------------------------

import os
import pandas as pd
from datetime import datetime
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "player_logs")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_player_id(player_name: str):
    """
    Returns NBA player ID from name (partial match allowed).
    """
    player_dict = players.get_players()
    for p in player_dict:
        if player_name.lower() in p["full_name"].lower():
            return p["id"], p["full_name"]
    return None, None


def fetch_player_gamelog(player_name: str, season: str = "2024-25"):
    """
    Fetch recent game logs for a given player (up to 20 games).
    """
    player_id, full_name = get_player_id(player_name)
    if not player_id:
        print(f"❌ Player not found: {player_name}")
        return pd.DataFrame()

    cache_path = os.path.join(CACHE_DIR, f"{player_id}.csv")

    try:
        gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=season)
        df = gamelog.get_data_frames()[0]
        df.to_csv(cache_path, index=False)
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
        df = df.sort_values("GAME_DATE", ascending=False).head(20)
        print(f"✅ {full_name} logs fetched ({len(df)} games)")
        return df
    except Exception as e:
        print(f"⚠️ Error fetching logs for {player_name}: {e}")
        if os.path.exists(cache_path):
            print("➡️ Using cached data.")
            return pd.read_csv(cache_path)
        return pd.DataFrame()


def calc_hit_rates(df: pd.DataFrame, stat: str, line: float):
    """
    Calculates hit rates for a given stat and prop line.
    Returns L5/L10/L20 hit percentages.
    """
    if df.empty or stat not in df.columns:
        return {"L5": None, "L10": None, "L20": None}

    df = df.copy()
    df = df.sort_values("GAME_DATE", ascending=False)
    df["hit"] = (df[stat] > line).astype(int)

    def rate(n):
        return round(df.head(n)["hit"].mean() * 100, 1) if len(df) >= n else None

    return {"L5": rate(5), "L10": rate(10), "L20": rate(20)}


def get_player_stats_summary(player_name: str, prop_type: str, line: float):
    """
    Full pipeline: fetch logs + compute hit rates for the selected prop.
    """
    prop_map = {
        "Points": "PTS",
        "Rebounds": "REB",
        "Assists": "AST",
        "PRA": None,  # computed below
        "3PM": "FG3M"
    }

    df = fetch_player_gamelog(player_name)
    if df.empty:
        return pd.DataFrame(), {}

    if prop_type == "PRA":
        df["PRA"] = df["PTS"] + df["REB"] + df["AST"]

    stat = prop_map.get(prop_type)
    if stat is None:
        stat = prop_type  # fallback if custom type used

    rates = calc_hit_rates(df, stat, line)
    avg = df[stat].mean() if stat in df.columns else None

    summary = {
        "player": player_name,
        "prop_type": prop_type,
        "avg": round(avg, 1) if avg else None,
        "line": line,
        "hit_rates": rates,
        "last_updated": datetime.utcnow().isoformat()
    }

    return df, summary


if __name__ == "__main__":
    # Example test
    df, summary = get_player_stats_summary("LeBron James", "Points", 25.5)
    print(summary)
