"""Dukascopy historical XAUUSD BID minute candles (free public archive).

NOT TradingView/OANDA, NOT a live quote. The historical file may be published
with a delay; missing current-day bars must not be filled with fictional data.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import lzma
import math
import struct

import pandas as pd
import requests

from offline import load_ohlc

URL_BASE = "https://datafeed.dukascopy.com/datafeed"
DECODER = struct.Struct(">IIIIIf")  # offset seconds; open,close,low,high; volume
GOLD_SCALE = 1000
SUPPORTED = {"1m":"1min", "5m":"5min", "15m":"15min", "30m":"30min"}
SOURCE = "Dukascopy XAUUSD Spot (historische BID-Kerzen, nicht OANDA/TradingView)"


def daily_url(day: datetime, side: str = "BID") -> str:
    if side not in ("BID", "ASK"):
        raise ValueError("Nur BID und ASK zulässig.")
    return (f"{URL_BASE}/XAUUSD/{day.year}/{day.month-1:02d}/{day.day:02d}/"
            f"{side}_candles_min_1.bi5")


def decode_day(blob: bytes, day: datetime) -> pd.DataFrame:
    """Read untrusted, size-limited LZMA candles using exact official binary layout."""
    cols=["time","open","high","low","close","volume"]
    if not blob:
        return pd.DataFrame(columns=cols)
    if len(blob) > 5_000_000:
        raise ValueError("Historische Tagesdatei ungewöhnlich groß.")
    try:
        raw=lzma.decompress(blob)
    except (lzma.LZMAError,EOFError) as exc:
        raise ValueError("Historische Tagesdatei beschädigt (LZMA).") from exc
    if len(raw) > 20_000_000 or len(raw) % DECODER.size:
        raise ValueError("Ungültige Länge des Dukascopy-Kerzenformats.")
    origin=pd.Timestamp(day.date(),tz="UTC")
    rows=[]
    prior=-1
    for offset,o,c,l,h,v in DECODER.iter_unpack(raw):
        if offset >= 86400 or offset <= prior:
            raise ValueError("Ungültige Zeitstempel-Reihenfolge im BID-Archiv.")
        prior=offset
        op,cl,lo,hi=(o/GOLD_SCALE,c/GOLD_SCALE,l/GOLD_SCALE,h/GOLD_SCALE)
        if (not all(math.isfinite(n) and 200<n<20000 for n in (op,cl,lo,hi)) or
            lo > min(op,cl) or hi < max(op,cl) or hi < lo or
            not math.isfinite(v) or v < 0):
            raise ValueError("BID-Kerzen enthalten ungültige Preise/Volumen.")
        rows.append((origin+pd.Timedelta(seconds=offset),op,hi,lo,cl,v))
    return pd.DataFrame(rows,columns=cols)


def aggregate(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    if interval not in SUPPORTED:
        raise ValueError("Für Dukascopy sind 1m, 5m, 15m und 30m vorgesehen.")
    if df.empty:
        raise ValueError("Keine historischen XAUUSD-Daten gefunden.")
    df=df.sort_values("time").drop_duplicates(subset=["time"],keep="last")
    frame=df.set_index("time")
    grouped=frame.resample(SUPPORTED[interval],label="left",closed="left")
    out=grouped.agg({"open":"first","high":"max","low":"min",
                     "close":"last","volume":"sum"})
    counts=grouped["close"].count()
    # Drop partial aggregated candles, including the first/last incomplete interval
    # and around daily session breaks; only closed complete intervals remain.
    wanted=int(pd.Timedelta(SUPPORTED[interval])/pd.Timedelta("1min"))
    out=out[counts==wanted].dropna(subset=["open","high","low","close"])
    if len(out)<60:
        raise ValueError(
            "Dukascopy hat zu wenige vollständige Kerzen für diesen Zeitraum geliefert. "
            "Handelspausen und verzögerte Tagesarchive sind möglich."
        )
    out=out.reset_index().tail(5000)
    out["time"]=pd.to_datetime(out["time"],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return load_ohlc(out.to_csv(index=False).encode("utf-8"))


def fetch_spot_gold(interval: str = "5m", *, today: datetime | None=None,
                    days_back: int = 8, request_get=None) -> pd.DataFrame:
    """Fetch up to 8 recent day files, a small bounded batch; not continuous polling."""
    if interval not in SUPPORTED:
        raise ValueError("Dukascopy unterstützt hier nur 1m/5m/15m/30m.")
    if not 1 <= days_back <= 10:
        raise ValueError("Ungültige Anzahl historischer Tage.")
    now=today or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("UTC-Zeitzone erforderlich.")
    now=now.astimezone(timezone.utc)
    getter=request_get or requests.get
    frames=[]
    had_error=False
    for n in range(days_back-1,-1,-1):
        day=now-timedelta(days=n)
        url=daily_url(day)
        try:
            response=getter(url,timeout=12,headers={
                "User-Agent":"ChartPilotResearch/2.3 (historical data; no live orders)",
                "Accept":"application/octet-stream"})
        except requests.RequestException:
            had_error=True
            continue
        if response.status_code in (404,204) or not response.content:
            continue
        if response.status_code in (429,503):
            raise RuntimeError(
                "Dukascopy begrenzt gerade die historischen Abrufe (429/503). "
                "Versuch es später; kein automatisches Nachladen."
            )
        if response.status_code != 200:
            had_error=True
            continue
        frames.append(decode_day(response.content,day))
    valid=[f for f in frames if not f.empty]
    if not valid:
        suffix="; einzelne Abrufe fehlgeschlagen." if had_error else "."
        raise RuntimeError("Kein verfügbares Dukascopy-XAUUSD-Archiv im gewählten Zeitraum"+suffix)
    try:
        return aggregate(pd.concat(valid,ignore_index=True),interval)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
