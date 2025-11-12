import requests
import pandas as pd

def fetch_fanduel_props():
    """Fetch NBA player prop markets from FanDuel's internal API."""
    try:
        url = "https://sportsbook.fanduel.com/api/content/navigation/nba"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }

        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"FanDuel API error {r.status_code}")
            return pd.DataFrame()

        data = r.json()

        # Extract event IDs for NBA games
        event_ids = []
        for item in data.get("attachments", {}).get("events", {}).values():
            if item.get("state") == "open":
                event_ids.append(item["id"])

        all_props = []
        for eid in event_ids[:10]:  # limit to first 10 games to avoid overload
            ev_url = f"https://sportsbook.fanduel.com/api/content/v1/events/{eid}"
            ev = requests.get(ev_url, headers=headers, timeout=20).json()
            markets = ev.get("attachments", {}).get("markets", {})

            for mk in markets.values():
                name = mk.get("name", "")
                if "Points" in name or "Rebounds" in name or "Assists" in name:
                    outcomes = mk.get("outcomes", {})
                    for out in outcomes.values():
                        sel = out.get("label", "")
                        price = out.get("price", {}).get("americanDisplay", "")
                        line = out.get("terms", {}).get("total", "")

                        all_props.append({
                            "game": ev.get("attachments", {}).get("events", {}).get(str(eid), {}).get("name", ""),
                            "prop_type": name,
                            "player": sel,
                            "line": line,
                            "odds": price
                        })

        df = pd.DataFrame(all_props)
        print(f"✅ Loaded {len(df)} FanDuel props")
        return df

    except Exception as e:
        print("FanDuel fetch error:", e)
        return pd.DataFrame()
