"""Datenherkunft, Alter und Plausibilität für transparente Analyseanzeigen."""
from __future__ import annotations
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import pandas as pd

PERIOD_MINUTES = {'1m':1,'2m':2,'3m':3,'5m':5,'15m':15,'30m':30,'1h':60,'4h':240,'1d':1440,'1D':1440}

@dataclass
class Audit:
    label: str
    last_timestamp: str
    age_minutes: float | None
    candle_count: int
    state: str
    issues: list[str]

def inspect_candles(df: pd.DataFrame, label: str, timeframe: str, *,
                    now: datetime | None = None, is_demo: bool = False) -> Audit:
    """Market-closed gaps are informational, never assumed to be feed errors."""
    issues = []
    if len(df) < 80:
        issues.append('Kurze Historie: Indikatoren sind wenig stabil.')
    if 'volume' not in df.columns or df['volume'].fillna(0).sum() == 0:
        issues.append('Kein verwertbares Volumen in dieser Datenreihe.')
    age = None
    last_ts = 'Nicht vorhanden'
    state = 'DEMO' if is_demo else 'ZEIT UNBEKANNT'
    if 'time' in df.columns and len(df):
        when = pd.to_datetime(df['time'].iloc[-1], utc=True, errors='coerce')
        if not pd.isna(when):
            last_ts = when.strftime('%Y-%m-%d %H:%M UTC')
            clock = now or datetime.now(timezone.utc)
            age = round((clock - when.to_pydatetime()).total_seconds()/60, 1)
            if age < -5:
                state = 'ZEITFEHLER'
                issues.append('Zeitstempel liegt in der Zukunft; Zeitzone/Datenquelle prüfen.')
            elif not is_demo:
                expected = PERIOD_MINUTES.get(timeframe, 5)
                # Conservative age thresholds: closed markets may legitimately be stale.
                if age > max(45, expected * 4):
                    state = 'HISTORISCH'
                    issues.append('Letzte Kerze ist älter als der gewählte Zeitrahmen. Kein aktuelles Signal.')
                else:
                    state = 'VERZÖGERT / UNBESTÄTIGT'
            if age is not None and age < -5:
                issues.append('Mögliche falsche Sekunden/Millisekunden-Zeitstempel.')
    if is_demo:
        issues.insert(0, 'Synthetische Demo-Kerzen, keine echten Marktpreise.')
    if 'time' in df.columns and len(df)>1:
        series = pd.to_datetime(df['time'], utc=True, errors='coerce')
        if series.duplicated().any():
            issues.append('Doppelte Kerzen-Zeitstempel erkannt.')
        if not series.is_monotonic_increasing:
            issues.append('Kerzen sind nicht aufsteigend sortiert.')
    if len(df) > 1 and (df['close'].pct_change().abs() > .2).any():
        issues.append('Extreme Kurslücke >20 % – Datenquelle und Instrument prüfen.')
    return Audit(label=label, last_timestamp=last_ts, age_minutes=age,
                 candle_count=len(df), state=state, issues=issues)

def freshness_blocks_live(audit: Audit) -> bool:
    """An unverified screenshot or historical series must not be presented as 'live'."""
    return audit.state != 'VERZÖGERT / UNBESTÄTIGT'
