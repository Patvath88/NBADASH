# -------------------------------------------------
# scripts/fetch_fanduel.py
# -------------------------------------------------
# Hot Shot Props — Live FanDuel Odds Scraper
# Scrapes official FanDuel NBA player prop odds (points, rebounds, assists, etc.)
# -------------------------------------------------

import os
import json
import pandas as pd
import requests
from datetime import datetime
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
ODDS_PATH = os.path.join(DATA_DIR, "odds_snapshot.json")

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
FANDUEL_URL = "https://sportsbook.fanduel.com/navigation/nba"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/118.0 Safari/537.36"
}


def fetch_fanduel_data():
    """Scrape FanDuel for live NBA player prop odds."""
    print("📊 Fetching FanDuel NBA player props (live)...")

    try:
        r = requests.get(FANDUEL_URL, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"⚠️ Failed to fetch FanDuel page: {r.status_code}")
            return pd.DataFrame()

        soup = BeautifulSoup(r.text, "html.parser")

        # Find all script tags with JSON data
        script_tags = soup.find_all("script")
        data_tag = None
        for tag in script_tags:
            if "window.__INITIAL_STATE__" in tag.text:
                data_tag = tag
                break

        if not data_tag:
            print("⚠️ Could not locate FanDuel data tag.")
            return pd.DataFrame()

        json_text = data_tag.text.split("window.__INITIAL_STATE__=")[-1].strip()
        if json_text.endswith(";"):
            json_text = json_text[:-1]

        data = json.loads(json_text)

        # Parse player props from nested structure
        markets = []
        for event_id, event in data.get("events", {}).items():
            competition = event.get("competitionName", "")
            markets_data = event.get("markets", {})
            for mid, m in markets_data.items():
                name = m.get("marketName", "")
                if not any(x in name for x in ["Points", "Rebounds", "Assists", "3PT", "PRA"]):
                    continue

                outcomes = m.get("outcomes", {})
                for oid, o in outcomes.items():
                    player_name = o.get("label", "").strip()
                    price = o.get("oddsAmerican", "")
                    line = o.get("line", "")
                    prop_type = "PTS" if "Points" in name else \
                                "REB" if "Rebounds" in name else \
                                "AST" if "Assists" in name else \
                                "PRA" if "PRA" in name else \
                                "3PM" if "3PT" in name else "Other"

                    markets.append({
                        "player": player_name,
                        "prop_type": prop_type,
                        "line": line,
                        "odds": price,
                        "market_name": name,
                        "game": competition
                    })

        if not markets:
            print("⚠️ No player props found in FanDuel JSON.")
            return pd.DataFrame()

        df = pd.DataFrame(markets)

        # Split over/under odds when both available
        df = df.pivot_table(index=["player", "prop_type", "line", "game"],
                            columns="market_name", values="odds", aggfunc="first").reset_index()

        df["timestamp"] = datetime.utcnow().isoformat()

        # Save snapshot
        df.to_json(ODDS_PATH, orient="records", indent=2)
        print(f"✅ Saved {len(df)} FanDuel props → {ODDS_PATH}")
        return df

    except Exception as e:
        print(f"⚠️ Error scraping FanDuel odds: {e}")
        return pd.DataFrame()


def load_fanduel_snapshot():
    """Load cached odds snapshot; fetch new if missing."""
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


if __name__ == "__main__":
    df = fetch_fanduel_data()
    print(df.head())
