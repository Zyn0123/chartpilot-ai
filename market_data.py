"""Kostenlose historische Yahoo-Finance-Daten für Lernzwecke, keine Echtzeit-/Brokerdaten."""
from __future__ import annotations

import pandas as pd
from offline import load_ohlc

# Gold ist bewusst GC=F (COMEX-Future), NICHT TradingView XAUUSD-Spot!
MARKETS = {
    "Gold-Future (GC=F) · nicht XAUUSD Spot": "GC=F",
    "S&P 500 Index (^GSPC) · kein handelbares Produkt": "^GSPC",
    "NASDAQ 100 Index (^NDX) · kein handelbares Produkt": "^NDX",
    "S&P 500 E-mini-Future (ES=F)": "ES=F",
    "NASDAQ 100 E-mini-Future (NQ=F)": "NQ=F",
}
PERIODS = {
    "1m": "5d", "2m": "5d", "5m": "5d",
    "15m": "1mo", "30m": "1mo",
    "1h": "1mo", "1d": "6mo",
}

def prepare_history(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Normalisiere von yfinance gelieferte Kerzen und prüfe OHLC-Konsistenz."""
    if raw is None or raw.empty:
        raise ValueError("Keine historischen Kurse zurückgegeben. Börse geschlossen, Rate-Limit oder Quelle nicht verfügbar.")
    frame = raw.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        if ticker in frame.columns.get_level_values(-1):
            frame = frame.xs(ticker, axis=1, level=-1)
        elif ticker in frame.columns.get_level_values(0):
            frame = frame.xs(ticker, axis=1, level=0)
        else:
            raise ValueError("Unerwartetes Format der Kursdaten.")
    needed = ["Open", "High", "Low", "Close"]
    if not set(needed).issubset(frame.columns):
        raise ValueError("Kursquelle lieferte unvollständige OHLC-Daten.")
    frame = frame.dropna(subset=needed).copy()
    if frame.empty:
        raise ValueError("Nur leere Kerzen empfangen.")
    frame = frame.sort_index()
    frame = frame.reset_index()
    first_col = frame.columns[0]
    frame = frame.rename(columns={first_col: "Time"})
    frame = frame[["Time"] + needed + (["Volume"] if "Volume" in frame.columns else [])]
    # Index enthält Timestamps mit Börsenzeitzone, bewahre absoluten Zeitpunkt.
    frame["Time"] = pd.to_datetime(frame["Time"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return load_ohlc(frame.tail(5000).to_csv(index=False).encode("utf-8"))

def fetch_history(ticker: str, interval: str) -> pd.DataFrame:
    """Lädt historische Kurse; kann bei Yahoo-Limits/Cloud-Sperren scheitern."""
    if ticker not in MARKETS.values():
        raise ValueError("Nicht unterstütztes Symbol.")
    if interval not in PERIODS:
        raise ValueError("Intervall nicht unterstützt. Wähle 1m, 2m, 5m, 15m, 30m, 1h oder 1d.")
    try:
        import yfinance as yf
        history = yf.Ticker(ticker).history(
            period=PERIODS[interval], interval=interval,
            auto_adjust=False, actions=False, timeout=12,
            raise_errors=True,
        )
        return prepare_history(history, ticker)
    except ValueError:
        raise
    except Exception as exc:
        # Keine geheimen Request-Details in der UI ausgeben.
        raise RuntimeError(
            "Kostenlose Yahoo-Finance-Abfrage fehlgeschlagen oder gedrosselt. "
            "Versuch es später erneut oder nutze den CSV-Upload."
        ) from exc

def age_notice(df: pd.DataFrame) -> str:
    """Transparenz über Zeitpunkt der zuletzt verfügbaren Kerze."""
    if "time" not in df.columns:
        return "Zeitstempel fehlt. Datenaktualität nicht bestimmbar."
    last = pd.Timestamp(df["time"].iloc[-1])
    now = pd.Timestamp.now(tz="UTC")
    age = (now - last).total_seconds()
    if age < 0:
        return f"Letzte Kerze {last:%d.%m.%Y %H:%M} UTC; Zeitstempel liegt in der Zukunft – Quelle prüfen."
    if age > 86400:
        return f"Letzte Kerze {last:%d.%m.%Y %H:%M} UTC – mehr als 24 Stunden alt (auch bei geschlossenen Märkten möglich)."
    if age > 3600:
        return f"Letzte Kerze {last:%d.%m.%Y %H:%M} UTC – ca. {age/3600:.1f} Stunden alt."
    return f"Letzte Kerze {last:%d.%m.%Y %H:%M} UTC – ca. {age/60:.0f} Minuten alt. Keine Echtzeitgarantie."
