"""On-demand indicative XAUUSD OHLC from TickerLayer Free REST.

Provider: https://tickerlayer.com/docs/products/commodities
Free limits are provider-defined; not an official OANDA/TradingView broker feed.
Never stores API keys, submits orders, or uses a trading endpoint.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

import pandas as pd
import requests

from offline import load_ohlc

HOST = "https://api.tickerlayer.com"
INSTRUMENT = "XAUUSD"
INTERVALS = {"1m": (1, "minute"), "5m": (5, "minute"), "15m": (15, "minute"),
             "1h": (1, "hour")}
SOURCE = "TickerLayer XAUUSD · indikative CFD-basierte Referenzkerzen, NICHT OANDA"


def parse_commodity_bars(payload: dict, interval: str, now: datetime | None = None) -> pd.DataFrame:
    if interval not in INTERVALS:
        raise ValueError("TickerLayer unterstützt hier 1m, 5m, 15m und 1h.")
    if not isinstance(payload,dict) or payload.get("symbol") != INSTRUMENT:
        raise ValueError("TickerLayer hat nicht XAUUSD geliefert.")
    bars=payload.get("results")
    if not isinstance(bars,list) or not bars:
        raise ValueError("Keine XAUUSD-Kerzen verfügbar. Börse eventuell geschlossen oder Datensatz leer.")
    clock=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    interval_minutes=INTERVALS[interval][0]*(60 if INTERVALS[interval][1]=="hour" else 1)
    rows=[]
    for bar in bars:
        if not isinstance(bar,dict):
            continue
        try:
            stamp=pd.to_datetime(bar["t"],unit="ms",utc=True)
            op,hi,lo,cl=(float(bar[k]) for k in ("o","h","l","c"))
            raw_volume=bar.get("v")
            volume=float(raw_volume) if raw_volume is not None else 0.
        except (ValueError,TypeError,KeyError,OverflowError):
            continue
        if not all(math.isfinite(q) for q in (op,hi,lo,cl,volume)):
            continue
        if (min(op,hi,lo,cl) <= 0 or lo>min(op,cl) or hi<max(op,cl)
                or volume<0):
            continue
        # Only use completed candles: bar start plus interval must already have passed,
        # and apply 30s extra settlement safety.
        finished=stamp.to_pydatetime()+timedelta(minutes=interval_minutes,seconds=30)
        if finished > clock:
            continue
        rows.append({"time":stamp,"open":op,"high":hi,"low":lo,
                     "close":cl,"volume":volume})
    if len(rows)<60:
        raise ValueError("Weniger als 60 vollständige XAUUSD-Kerzen verfügbar – kein Trading-Setup.")
    frame=pd.DataFrame(rows).sort_values("time").drop_duplicates("time",keep="last").tail(5000)
    if len(frame)<60:
        raise ValueError("Nach Entfernen doppelter Kerzen zu wenige Daten.")
    frame["time"]=frame["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return load_ohlc(frame.to_csv(index=False).encode("utf-8"))


def fetch_xauusd(api_key: str, interval: str, *, now: datetime | None = None, request_get=None) -> pd.DataFrame:
    """Latest completed indicative bars. Read-only API, no credentials in URL/logs."""
    if interval not in INTERVALS:
        raise ValueError("Für diese Quelle bitte 1m, 5m, 15m oder 1h wählen.")
    if not isinstance(api_key,str) or len(api_key.strip())<12:
        raise ValueError("Bitte einen kostenlosen TickerLayer-API-Key eingeben.")
    time_now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start=(time_now-timedelta(days=3)).date().isoformat()
    end=time_now.date().isoformat()
    multiplier,unit=INTERVALS[interval]
    url=f"{HOST}/commodities/agg/{INSTRUMENT}/{multiplier}/{unit}/{start}/{end}"
    req=request_get or requests.get
    try:
        response=req(
            url,headers={"x-api-key":api_key.strip(),"Accept":"application/json"},
            params={"limit":500,"sort":"desc","offset":0},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise RuntimeError("TickerLayer ist derzeit nicht erreichbar. Prüfe deine Verbindung.") from exc
    if response.status_code in (401,403):
        raise ValueError("TickerLayer-API-Key ist ungültig oder XAUUSD ist in deinem Tarif nicht verfügbar.")
    if response.status_code==429:
        raise RuntimeError("Kostenloses Abfragelimit erreicht. Keine automatische Wiederholung.")
    if response.status_code != 200:
        raise RuntimeError(
            f"TickerLayer-Abruf fehlgeschlagen (HTTP {response.status_code}). "
            "Historische Yahoo-/Dukascopy-Daten sind kein Ersatz für einen aktuellen Preis."
        )
    try:
        payload=response.json()
    except ValueError as exc:
        raise ValueError("TickerLayer lieferte keine lesbare JSON-Antwort.") from exc
    return parse_commodity_bars(payload,interval,now=time_now)
