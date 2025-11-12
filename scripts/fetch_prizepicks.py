# -------------------------------------------------
# scripts/fetch_prizepicks.py
# -------------------------------------------------
# Emergency fallback for NBA player props using the
# public PrizePicks API (no auth required)
# -------------------------------------------------

import os
import json
import requests
import pandas as pd
from datetime import datetime

PRIZEPICKS_URL = "https://api.prizepicks.com/projections"

def fetch_prizepicks_data():
    """
    Fetch NBA player props from PrizePicks as a last-resort source.
    Returns a normalized pandas DataFrame.
    """
    print("Fetching NBA props from PrizePicks fallback...")
    try:
        params = {"league_id": "7"}  # 7 = NBA
        response = requests.get(PRIZEPICKS_URL, params=params, timeout=15)
        if response.status_code != 200:
            print(f"⚠️ PrizePicks request failed: {response.status_code}")
            return pd.DataFrame()

        raw = response.json()
        included = {item["id"]: item for item in raw.get("included", []) if "attributes" in item}
        projections = raw.get("data", [])

        props_list = []
        for proj in projections:
            try:
                attr = proj["attributes"]
                player_id = attr.get("player_id")
                player_info = included.get(str(player_id), {}).get("attributes", {})
                player = player_info.get("name", "Unknown Player").strip()

                prop_type = attr.get("stat_type", "").replace("_", " ").title()
                line = attr.get("line_score")
                odds = -119  # PrizePicks uses 1:1 payout; map to pseudo-odds

                if attr.get("league_id") == 7:  # NBA only
                    props_list.append({
                        "player": player,
                        "prop_type": prop_type,
                        "line": line,
                        "odds_over": odds,
                        "odds_under": odds,
                        "book": "PrizePicks",
                        "source": "PrizePicks API",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except Exception:
                continue

        df = pd.DataFrame(props_list)
        if df.empty:
            print("⚠️ No props returned from PrizePicks.")
            return pd.DataFrame()

        save_path = os.path.join(os.path.dirname(__file__), "..", "data", "odds_snapshot.json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_json(save_path, orient="records", indent=2)
        print(f"✅ PrizePicks fallback success — {len(df)} props saved.")
        return df

    except Exception as e:
        print(f"❌ Error fetching PrizePicks data: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    df = fetch_prizepicks_data()
    if not df.empty:
        print(df.head())
    else:
        print("No PrizePicks data available.")
