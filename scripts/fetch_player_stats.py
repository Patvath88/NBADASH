# -------------------------------------------------
# scripts/fetch_player_stats.py
# -------------------------------------------------
# Hot Shot Props — Player Stats Fetcher (Stable Build)
# Fetches player game logs safely via nba_api with retry, caching,
# and fallback to local JSON if NBA API rate-limits or times out.
# -------------------------------------------------

import os
import json
import time
import pandas as pd
from datetime import datetime
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
from requests.exceptions import ReadTimeout, ConnectionError

# -------------------------------------------------
# PATHS
# -------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "player_logs")
os.makedirs(DATA_DIR, exist_ok=True)


# -------------------------------------------------
# UTILITIES
# -------------------------------------------------
def _get_player_id(player_name: str):
    """Resolve player ID from name (case-insensitive)."""
    try:
        all_players = players.get_players()
        match = next((p for p in all_players if p["full_name"].lower() == player_name.lower()), None)
        return match["id"] if match else None
    except Exception as e:
        print(f"⚠️ Error resolving ID for {player_name}: {e}")
        return None


def _cache_path(player_name: str, season: str):
    safe_name = player_name.replace(" ", "_").lower()
    return os.path.join(DATA_DIR, f"{safe_name}_{season}.json")


# -------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------
def get_player_stats_summary(player_name: str, season: str = "2024-25"):
    """
    Fetch player logs for given player name.
    Caches results locally to avoid hitting NBA API repeatedly.
    """
    pid = _get_player_id(player_name)
    if not pid:
        print(f"⚠️ Player not found: {player_name}")
        return pd.DataFrame()

    cache_file = _cache_path(player_name, season)
    # Return cached logs if fresh (under 12h old)
    if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < 43200:
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            return pd.DataFrame(data)
        except Exception:
            pass  # fall back to refetch

    # Attempt up to 3 times (for rate-limit safety)
    for attempt in range(3):
        try:
            print(f"📈 Fetching logs for {player_name} (attempt {attempt+1})...")
            gamelog = playergamelog.PlayerGameLog(player_id=pid, season=season, timeout=30)
            df = gamelog.get_data_frames()[0]
            df["PLAYER_NAME"] = player_name
            df["fetched_at"] = datetime.utcnow().isoformat()

            # Save to cache
            df.to_json(cache_file, orient="records", indent=2)
            print(f"✅ Saved {len(df)} games for {player_name} → {cache_file}")
            return df

        except (ReadTimeout, ConnectionError) as e:
            print(f"⚠️ Timeout for {player_name}: {e}. Retrying...")
            time.sleep(3)

        except Exception as e:
            print(f"⚠️ Error fetching logs for {player_name}: {e}")
            time.sleep(1)

    # Fallback: try to load stale cache if available
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            print(f"⚠️ Using cached logs for {player_name} (API unreachable).")
            return pd.DataFrame(data)
        except Exception:
            pass

    print(f"🚫 No logs available for {player_name}")
    return pd.DataFrame()


# -------------------------------------------------
# BULK FETCH (Optional)
# -------------------------------------------------
def bulk_fetch_players(player_names, season="2024-25"):
    """Fetch multiple players with progress display."""
    all_logs = []
    for name in player_names:
        logs = get_player_stats_summary(name, season)
        if not logs.empty:
            all_logs.append(logs)
        time.sleep(1.5)  # rate-limit buffer
    if not all_logs:
        return pd.DataFrame()
    return pd.concat(all_logs, ignore_index=True)


# -------------------------------------------------
# TEST ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    test_players = ["LeBron James", "Stephen Curry", "Luka Doncic"]
    df = bulk_fetch_players(test_players)
    print(df.head())
