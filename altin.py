# -*- coding: utf-8 -*-
import requests
import urllib3
import time
import datetime as dt
import numpy as np
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://finans.truncgil.com/v4/today.json"

def log(msg):
    print(f"[{dt.datetime.now()}] {msg}")

def fetch_price():
    try:
        r = requests.get(API_URL, timeout=10)
        r.raise_for_status()
        j = r.json()
        return float(j["GUMUS"]["Selling"]), float(j["GRA"]["Selling"])
    except:
        # SSL fallback
        r = requests.get(API_URL, timeout=10, verify=False)
        j = r.json()
        return float(j["GUMUS"]["Selling"]), float(j["GRA"]["Selling"])

def calc_signal(price_list):
    df = pd.DataFrame({"close": price_list})
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = (-delta).clip(lower=0)

    rs = up.rolling(14).mean() / (down.rolling(14).mean() + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    df = df.dropna()
    if len(df) < 5:
        return False

    ema20_p, ema20 = df["ema20"].iloc[-2], df["ema20"].iloc[-1]
    ema50_p, ema50 = df["ema50"].iloc[-2], df["ema50"].iloc[-1]
    rsi_p, rsi     = df["rsi"].iloc[-2], df["rsi"].iloc[-1]

    cond1 = ema20_p >= ema50_p and ema20 < ema50
    cond2 = rsi_p >= 70 and rsi < 70

    return cond1 or cond2

def main():
    gum_list = []
    alt_list = []

    while True:
        gum, alt = fetch_price()
        gum_list.append(gum)
        alt_list.append(alt)

        # keep last 200 samples
        gum_list = gum_list[-200:]
        alt_list = alt_list[-200:]

        log(f"Gram Gümüş: {gum} | Gram Altın: {alt}")

        gum_sat = calc_signal(gum_list)
        alt_sat = calc_signal(alt_list)

        if gum_sat:
            log("🔔 SİNYAL → GÜMÜŞ SAT!")
        if alt_sat:
            log("🔔 SİNYAL → ALTIN SAT!")

        time.sleep(10)

if __name__ == "__main__":
    main()
