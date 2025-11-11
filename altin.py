# -*- coding: utf-8 -*-
import requests
import urllib3
import time
import datetime as dt
import numpy as np
import pandas as pd
from requests.adapters import HTTPAdapter, Retry

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://finans.truncgil.com/v4/today.json"

# --- GLOBAL RETRY SESSION (5 tekrar, beklemeli) ---
session = requests.Session()
retries = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=2,           # 1s → 2s → 4s → 8s → 16s
    status_forcelist=[500, 502, 503, 504, 522, 524],
    allowed_methods=["GET"]
)
session.mount("http://", HTTPAdapter(max_retries=retries))
session.mount("https://", HTTPAdapter(max_retries=retries))


def log(text):
    print(f"[{dt.datetime.now()}] {text}")


# ✅ API'den fiyat çeken KUSURSUZ fonksiyon
def fetch_price():
    for attempt in range(5):
        try:
            # 1) Normal HTTPS denemesi
            r = session.get(API_URL, timeout=10)
            r.raise_for_status()
            j = r.json()

            gumus = float(j["GUMUS"]["Selling"])     # Gram gümüş
            altin = float(j["GRA"]["Selling"])       # Gram altın
            return gumus, altin

        except Exception as e:
            log(f"[secure fetch] Hata ({attempt+1}/5): {e}")

            # 2) SSL doğrulama kapalı fallback (GitHub Actions için şart)
            try:
                r = session.get(API_URL, timeout=10, verify=False)
                j = r.json()

                gumus = float(j["GUMUS"]["Selling"])
                altin = float(j["GRA"]["Selling"])
                return gumus, altin

            except Exception as e2:
                log(f"[insecure fetch] Hata ({attempt+1}/5): {e2}")

    # 5 defa da başarısız olursa
    return None, None



# ✅ RSI + EMA20/EMA50 SAT SİNYALİ
def calc_signal(price_list):
    if len(price_list) < 60:
        return False

    df = pd.DataFrame({"close": price_list})

    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = (-delta).clip(lower=0)

    rs = up.rolling(14).mean() / (down.rolling(14).mean() + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))

    df = df.dropna()

    # Son veriler
    ema20_prev, ema20 = df["ema20"].iloc[-2], df["ema20"].iloc[-1]
    ema50_prev, ema50 = df["ema50"].iloc[-2], df["ema50"].iloc[-1]
    rsi_prev, rsi = df["rsi"].iloc[-2], df["rsi"].iloc[-1]

    # SAT sinyali:
    cond1 = ema20_prev >= ema50_prev and ema20 < ema50
    cond2 = rsi_prev >= 70 and rsi < 70

    return cond1 or cond2



# ✅ ANA PROGRAM (sonsuz döngü — GitHub Actions her çalıştığında 1 kez döner)
def main():
    gumus_list = []
    altin_list = []

    # ❗ GitHub Actions sadece 1 defa çalıştırır, o yüzden tek ölçüm yapacağız
    gumus, altin = fetch_price()

    if gumus is None or altin is None:
        log("⚠ API YANIT VERMEDİ — bir sonraki çalıştırmada tekrar denenecek")
        return

    gumus_list.append(gumus)
    altin_list.append(altin)

    log(f"Gram Gümüş: {gumus}")
    log(f"Gram Altın: {altin}")

    gumus_sat = calc_signal(gumus_list)
    altin_sat = calc_signal(altin_list)

    if gumus_sat:
        log("🔔 GÜMÜŞ SAT SİNYALİ!")
    if altin_sat:
        log("🔔 ALTIN SAT SİNYALİ!")

    if not gumus_sat and not altin_sat:
        log("✅ Şu anda sat sinyali yok")



if __name__ == "__main__":
    main()
