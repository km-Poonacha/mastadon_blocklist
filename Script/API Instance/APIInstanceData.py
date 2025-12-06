# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mastodon instance data (minimal):

- /api/v2/instance          -> instance_snapshot (flattened)
- /api/v1/instance/activity -> activity_weekly
- /api/v1/instance/peers    -> peers

Outputs: one Excel file with three sheets.
"""

import requests
import pandas as pd
from pathlib import Path

# -----------------------------
# CONFIG
# -----------------------------
INSTANCE = "mastodon.social"   # <-- change if needed
TIMEOUT = 30
OUT_XLSX = Path("mastodon_instance_minimal.xlsx")

# -----------------------------
# HELPERS
# -----------------------------
def get_json(url: str):
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def collect_instance_snapshot(instance: str) -> dict:
    url = f"https://{instance}/api/v2/instance"
    return get_json(url)

def collect_activity_weekly(instance: str) -> pd.DataFrame:
    """
    GET /api/v1/instance/activity
    Returns ~12 weeks of data with columns:
    week_start (datetime), statuses, logins, registrations
    """
    url = f"https://{instance}/api/v1/instance/activity"
    data = get_json(url)

    if not isinstance(data, list) or not data:
        return pd.DataFrame(columns=["week_start", "statuses", "logins", "registrations"])

    df = pd.DataFrame(data)

    # 'week' is seconds since epoch (often as string) -> numeric -> datetime
    df["week"] = pd.to_numeric(df["week"], errors="coerce")
    df = df.dropna(subset=["week"])
    df["week_start"] = pd.to_datetime(
        df["week"].astype("int64"), unit="s", utc=True
    ).dt.tz_convert(None)

    # Coerce metrics to numeric
    for col in ["statuses", "logins", "registrations"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[["week_start", "statuses", "logins", "registrations"]]
    df = df.sort_values("week_start").reset_index(drop=True)
    return df

def collect_peers(instance: str) -> pd.DataFrame:
    url = f"https://{instance}/api/v1/instance/peers"
    data = get_json(url)
    if not isinstance(data, list):
        return pd.DataFrame(columns=["peer"])
    return pd.DataFrame({"peer": data})

# -----------------------------
# MAIN
# -----------------------------
def main():
    print(f"Collecting data from: {INSTANCE}")

    # 1) Snapshot
    snapshot = collect_instance_snapshot(INSTANCE)
    snapshot_flat = pd.json_normalize(snapshot, sep=".")
    print("✓ instance snapshot")

    # 2) Weekly activity
    weekly = collect_activity_weekly(INSTANCE)
    print(f"✓ weekly activity: {len(weekly)} rows")

    # 3) Peers
    peers = collect_peers(INSTANCE)
    print(f"✓ peers: {len(peers)} domains")

    # Save everything to one Excel
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as xw:
        snapshot_flat.to_excel(xw, index=False, sheet_name="instance_snapshot")
        weekly.to_excel(xw, index=False, sheet_name="activity_weekly")
        peers.to_excel(xw, index=False, sheet_name="peers")

    print(f"\n✅ Excel written: {OUT_XLSX.resolve()}")

if __name__ == "__main__":
    main()
