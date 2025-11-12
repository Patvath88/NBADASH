# scripts/fetch_fanduel.py
# Option C — Real FanDuel NBA Player Props Scraper (XHR-based, no Selenium)

import requests, pandas as pd, time, json
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "fanduel_nba_props.json"
SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
}

def fetch_fanduel_props():
    """
    Fetches real NBA player props directly from FanDuel's internal JSON API.
    Works in Streamlit Cloud and returns a clean DataFrame of live props.
    """
    try:
        # Step 1: Fetch NBA event list
        events_url = (
            "https://sportsbook.fanduel.com/api/content-service/v1/"
            "sport/BASKETBALL/competition/NBA?regionCode=US&locale=en-US"
        )
        r = requests.get(events_url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print("⚠️  Failed to fetch NBA competition feed:", r.status_code)
            return pd.DataFrame()

        data = r.json()
        events = []
        for node in data.get("attachments", {}).get("events", {}).values():
            event_id = node.get("id")
            name = node.get("name")
            if event_id and "@" in name:
                events.append({"event_id": event_id, "matchup": name})

        if not events:
            print("⚠️  No NBA events found in FanDuel feed.")
            return pd.DataFrame()

        # Step 2: For each game, pull the event page JSON (contains markets)
        props = []
        for e in events:
            eid = e["event_id"]
            url = f"https://sportsbook.fanduel.com/api/event-page?_ak=FhMFpcPWXMeyZxOx&eventId={eid}"
            try:
                res = requests.get(url, headers=HEADERS, timeout=20)
                if res.status_code != 200:
                    continue
                payload = res.json()
                markets = payload.get("attachments", {}).get("markets", {})
                for m_id, m_data in markets.items():
                    title = m_data.get("name", "").strip()
                    if not any(x in title.lower() for x in ["points", "rebounds", "assists", "threes", "made"]):
                        continue  # skip non-player markets

                    outcomes = m_data.get("outcomes", [])
                    for o in outcomes:
                        player = o.get("label", "").strip()
                        line = o.get("line")
                        price = o.get("price")
                        props.append({
                            "player": player,
                            "prop_type": title,
                            "line": line,
                            "odds": price,
                            "game": e["matchup"],
                            "event_id": eid,
                            "bookmaker": "FanDuel",
                            "timestamp": time.time(),
                        })
            except Exception as inner_e:
                print(f"Error parsing event {eid}: {inner_e}")
                continue

        df = pd.DataFrame(props)
        if df.empty:
            print("⚠️  No player props found.")
            return pd.DataFrame()

        # Step 3: Save snapshot for debugging
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(df.to_dict(orient="records"), f, indent=2)

        print(f"✅  Retrieved {len(df)} player props from FanDuel.")
        return df

    except Exception as e:
        print("❌  Critical FanDuel fetch error:", e)
        return pd.DataFrame()
