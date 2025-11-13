# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import time
import requests
from urllib.parse import urlparse

# -----------------------------
# CONFIG
# -----------------------------
URL = "https://social.freysa.ai/public/local"
OUTFILE = "freysa_toots.xlsx"
SCROLLS = 5
SLEEP = 3
API_SLEEP = 0.2  # polite delay between API calls

# -----------------------------
# HELPERS
# -----------------------------
def instance_from_url(public_local_url: str) -> str:
    return urlparse(public_local_url).netloc  # e.g., social.freysa.ai

def fetch_counts_via_api(instance: str, status_id: str):
    """
    GET https://{instance}/api/v1/statuses/{id}
    Returns replies_count, reblogs_count, favourites_count (or None if not available).
    """
    try:
        api_url = f"https://{instance}/api/v1/statuses/{status_id}"
        r = requests.get(api_url, timeout=15)
        r.raise_for_status()
        j = r.json()
        return (
            j.get("replies_count"),
            j.get("reblogs_count"),
            j.get("favourites_count"),
        )
    except Exception:
        return (None, None, None)

def extract_basic_fields(article_el):
    """Grab id, permalink, datetime, username, display name, content (text/html) from an <article>."""
    # permalink + id
    try:
        link = article_el.find_element(By.CSS_SELECTOR, "a.status__relative-time, a.detailed-status__datetime")
        permalink = link.get_attribute("href")
        status_id = permalink.rstrip("/").split("/")[-1] if permalink else None
    except:
        permalink = None
        status_id = None

    # datetime
    try:
        time_el = article_el.find_element(By.CSS_SELECTOR, "time")
        dt_iso = time_el.get_attribute("datetime")
    except:
        dt_iso = None

    # username/login + display name
    try:
        user_el = article_el.find_element(By.CSS_SELECTOR, ".display-name__account, .status__display-name strong")
        username = user_el.text.strip()
    except:
        username = None

    try:
        disp_el = article_el.find_element(By.CSS_SELECTOR, ".display-name__html, .status__display-name strong")
        display_name = disp_el.text.strip()
    except:
        display_name = None

    # content
    try:
        content_el = article_el.find_element(By.CSS_SELECTOR, ".status__content, .detailed-status__text")
        content_text = content_el.text
        content_html = content_el.get_attribute("innerHTML")
    except:
        content_text = None
        content_html = None

    return {
        "id": status_id,
        "permalink": permalink,
        "datetime": dt_iso,
        "username": username,
        "display_name": display_name,
        "content_text": content_text,
        "content_html": content_html,
    }

# -----------------------------
# MAIN
# -----------------------------
driver = webdriver.Chrome()
driver.get(URL)
time.sleep(5)

collected = {}  # id -> record
for i in range(SCROLLS):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(SLEEP)

    # collect after each scroll
    articles = driver.find_elements(By.CSS_SELECTOR, "article")
    for el in articles:
        rec = extract_basic_fields(el)
        tid = rec.get("id")
        if tid and tid not in collected:
            collected[tid] = rec
    print(f"Scroll {i+1}/{SCROLLS} — collected {len(collected)} toots")

driver.quit()

# Fill counts via API
instance = instance_from_url(URL)
for tid, rec in collected.items():
    if not tid:
        continue
    replies, reblogs, favs = fetch_counts_via_api(instance, tid)
    rec["replies_count"] = replies
    rec["reblogs_count"] = reblogs
    rec["favourites_count"] = favs
    time.sleep(API_SLEEP)

# Save to Excel
df = pd.DataFrame(list(collected.values()))
df.to_excel(OUTFILE, index=False)
print(f"✅ Saved {len(df)} toots to {OUTFILE}")
