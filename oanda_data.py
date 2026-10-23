"""Optional read-only OANDA v20 Practice candle adapter.

Only GET /v3/instruments/XAU_USD/candles on the PRACTICE host.
No account orders, no live-account URLs, no logging or persistence of tokens.
"""
from __future__ import annotations

import requests
import pandas as pd
from offline import load_ohlc

PRACTICE_API="https://api-fxpractice.oanda.com"
FRAMES={"1m":"M1","5m":"M5","15m":"M15","30m":"M30","1h":"H1","1d":"D"}
SOURCE="OANDA v20 Practice · XAU_USD · historische MID-Kerzen (kein Live-Feed)"


def parse_oanda_candles(payload: dict, granularity: str) -> pd.DataFrame:
    if not isinstance(payload,dict) or payload.get("instrument")!="XAU_USD":
        raise ValueError("OANDA lieferte kein XAU_USD-Instrument.")
    if payload.get("granularity")!=granularity:
        raise ValueError("OANDA lieferte einen unerwarteten Zeitraum.")
    rows=[]
    for candle in payload.get("candles",[]):
        # Never include the latest still-open bar in strategy analysis.
        if candle.get("complete") is not True:
            continue
        mid=candle.get("mid")
        if not isinstance(mid,dict):
            continue
        try:
            rows.append({
                "time":candle["time"],
                "open":float(mid["o"]), "high":float(mid["h"]),
                "low":float(mid["l"]), "close":float(mid["c"]),
                "volume":float(candle.get("volume",0)),
            })
        except (TypeError,ValueError,KeyError):
            continue
    if len(rows)<60:
        raise ValueError("OANDA lieferte weniger als 60 vollständige MID-Kerzen.")
    df=pd.DataFrame(rows)
    return load_ohlc(df.to_csv(index=False).encode("utf-8"))


def fetch_oanda_practice(token: str, timeframe: str, *, request_get=None) -> pd.DataFrame:
    if timeframe not in FRAMES:
        raise ValueError("Für OANDA bitte 1m/5m/15m/30m/1h/1d wählen.")
    if not token or not isinstance(token,str) or len(token.strip())<20:
        raise ValueError("Ein persönlicher v20 Practice API-Token ist erforderlich.")
    # Fixed endpoint and host – caller input cannot choose any order route.
    request=request_get or requests.get
    try:
        response=request(
            f"{PRACTICE_API}/v3/instruments/XAU_USD/candles",
            headers={"Authorization":"Bearer "+token.strip(),
                     "Accept":"application/json",
                     "Accept-Datetime-Format":"RFC3339"},
            params={"price":"M","granularity":FRAMES[timeframe],
                    "count":400,"smooth":"false"},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise RuntimeError("OANDA Practice ist nicht erreichbar. Später erneut probieren.") from exc
    if response.status_code in (401,403):
        raise ValueError("OANDA Practice Token fehlt, ist ungültig oder dieser Zugang ist nicht berechtigt.")
    if response.status_code in (404,405):
        raise ValueError("XAU_USD oder der OANDA Candle-Zugang ist für dieses Demo-Konto nicht verfügbar.")
    if response.status_code==429:
        raise RuntimeError("OANDA begrenzt gerade die Abfragen – keine automatischen Wiederholungen.")
    if response.status_code!=200:
        raise RuntimeError("OANDA konnte keine Daten liefern (HTTP-Status "+str(response.status_code)+").")
    try:
        payload=response.json()
    except ValueError as exc:
        raise ValueError("OANDA lieferte kein gültiges JSON.") from exc
    return parse_oanda_candles(payload,FRAMES[timeframe])
