# scripts/fetch_fanduel.py
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def fetch_fanduel_props():
    """Scrape NBA player prop lines from FanDuel using headless Chrome."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    url = "https://sportsbook.fanduel.com/navigation/nba"
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)

    props_data = []
    try:
        prop_sections = driver.find_elements(By.CSS_SELECTOR, "section[data-testid='event']")
        for sec in prop_sections:
            try:
                teams = sec.find_element(By.CSS_SELECTOR, "div[class*='event-title']").text
                markets = sec.find_elements(By.CSS_SELECTOR, "a[data-testid*='player-prop']")
                for m in markets:
                    props_data.append({
                        "game": teams,
                        "player": m.text.split('\n')[0],
                        "prop_type": m.text.split('\n')[1] if len(m.text.split('\n')) > 1 else '',
                        "line": None,
                        "odds": None
                    })
            except Exception:
                continue
    except Exception as e:
        print("FanDuel scrape error:", e)

    driver.quit()

    df = pd.DataFrame(props_data)
    return df
