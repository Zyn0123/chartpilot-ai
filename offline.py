"""Kostenlose OHLC-Analyse. Keine Bild-KI, keine Netzwerkaufrufe, keine Trades."""
from __future__ import annotations

import io
import re
from typing import Any

import pandas as pd

from engine import normalize_analysis

_REQUIRED = ('open', 'high', 'low', 'close')
_ALIASES = {
    'date': 'time', 'datetime': 'time', 'timestamp': 'time', 'zeit': 'time',
    'datum': 'time', 'time': 'time',
    'open': 'open', 'eroeffnung': 'open', 'openingprice': 'open',
    'high': 'high', 'hoch': 'high',
    'low': 'low', 'tief': 'low',
    'close': 'close', 'schluss': 'close', 'closingprice': 'close',
    'volume': 'volume', 'volumen': 'volume', 'vol': 'volume',
}


def _normalize_column(col: Any) -> str:
    cleaned = str(col).strip().lower().replace('ö', 'oe').replace('ü', 'ue')
    cleaned = re.sub(r'[^a-z]', '', cleaned)
    return _ALIASES.get(cleaned, str(col).strip().lower())


def _number(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors='coerce')
    source = series.astype(str).str.strip().str.replace(r'\s', '', regex=True)
    use_comma = source.str.contains(',', regex=False).sum() > source.str.contains(r'\.', regex=True).sum()
    if use_comma:
        source = source.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    else:
        source = source.str.replace(',', '', regex=False)
    return pd.to_numeric(source, errors='coerce')


def load_ohlc(content: bytes) -> pd.DataFrame:
    if not content or len(content) > 10_000_000:
        raise ValueError('Bitte eine CSV-Datei bis 10 MB hochladen.')
    try:
        raw = pd.read_csv(io.BytesIO(content), sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='error')
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError('CSV nicht lesbar. Nutze UTF-8 mit Spalten Time, Open, High, Low, Close.') from exc
    raw.columns = [_normalize_column(name) for name in raw.columns]
    if any(raw.columns.duplicated()):
        raise ValueError('CSV enthält doppelte Spaltennamen.')
    missing = [name for name in _REQUIRED if name not in raw.columns]
    if missing:
        raise ValueError(f'Fehlende Kurs-Spalten: {", ".join(missing)}. Erwartet: Open, High, Low, Close.')
    df = raw.copy()
    for name in (*_REQUIRED, 'volume'):
        if name in df.columns:
            df[name] = _number(df[name])
    if 'time' in df.columns:
        times = df['time']
        numeric = pd.to_numeric(times, errors='coerce')
        if numeric.notna().all():
            maximum = float(numeric.abs().median())
            unit = 'us' if maximum > 1e14 else ('ms' if maximum > 1e11 else 's')
            date = pd.to_datetime(numeric, unit=unit, errors='coerce', utc=True)
        else:
            date = pd.to_datetime(times, errors='coerce', utc=True, format='mixed')
        if date.isna().any():
            raise ValueError('Ungültige Zeitstempel im CSV-Export – Time-Spalte prüfen.')
        df['time'] = date
        if not df['time'].is_monotonic_increasing:
            raise ValueError('Zeitstempel sind nicht aufsteigend sortiert.')
        if df['time'].duplicated().any():
            raise ValueError('Doppelte Zeitstempel – ungültige Kerzendatei.')
    if len(df) < 60:
        raise ValueError('Mindestens 60 Kerzen nötig, damit EMA50 und Vergleichsfenster sinnvoll sind.')
    if df[list(_REQUIRED)].isna().any().any():
        raise ValueError('Einige OHLC-Preise fehlen oder sind nicht numerisch.')
    if (df[list(_REQUIRED)] <= 0).any().any():
        raise ValueError('OHLC-Preise müssen positiv sein.')
    if ((df['high'] < df[['open', 'close', 'low']].max(axis=1)) |
            (df['low'] > df[['open', 'close', 'high']].min(axis=1))).any():
        raise ValueError('Ungültige Kerze: High/Low stimmen nicht mit Open/Close überein.')
    df = df.tail(5000).reset_index(drop=True)
    return df


def analyze_ohlc(df: pd.DataFrame, market: str, style: str, timeframe: str) -> tuple[dict, pd.DataFrame, dict]:
    if len(df) < 60:
        raise ValueError('Mindestens 60 Kerzen erforderlich.')
    enriched = df.copy()
    enriched['EMA20'] = enriched.close.ewm(span=20, adjust=False).mean()
    enriched['EMA50'] = enriched.close.ewm(span=50, adjust=False).mean()
    prev_close = enriched.close.shift(1)
    true_range = pd.concat([
        enriched.high - enriched.low,
        (enriched.high - prev_close).abs(),
        (enriched.low - prev_close).abs()
    ], axis=1).max(axis=1)
    enriched['ATR14'] = true_range.rolling(14, min_periods=14).mean()
    last = enriched.iloc[-1]
    before = enriched.iloc[-21:-1]
    support = float(before.low.min())
    resistance = float(before.high.max())
    close = float(last.close)
    ema20, ema50 = float(last.EMA20), float(last.EMA50)
    atr = float(last.ATR14)
    fast_above = ema20 > ema50 and close > ema20
    fast_below = ema20 < ema50 and close < ema20
    trend = 'aufwärts' if fast_above else ('abwärts' if fast_below else 'seitwärts')
    buffer = atr * .15
    prev2_high = float(enriched.iloc[-22:-2].high.max())
    prev2_low = float(enriched.iloc[-22:-2].low.min())
    last2 = enriched.close.iloc[-2:]
    confirmed_long = fast_above and bool((last2 > prev2_high + buffer).all())
    confirmed_short = fast_below and bool((last2 < prev2_low - buffer).all())
    signal = 'NO TRADE'
    entry = stop = take = None
    reason = 'Kein bestätigter Ausbruch in Trendrichtung; Regeln liefern derzeit kein Setup.'
    if confirmed_long:
        signal = 'LONG'
        entry = close
        stop = max(0.00001, close - max(atr * 1.5, close - min(support, ema20)))
        take = close + (close - stop) * 2
        reason = 'Zwei Schlusskurse oberhalb der vorangegangenen Handelsspanne und EMA20 über EMA50.'
    elif confirmed_short:
        signal = 'SHORT'
        entry = close
        stop = close + max(atr * 1.5, max(resistance, ema20) - close)
        take = close - (stop - close) * 2
        if take <= 0:
            signal = 'NO TRADE'
            entry = stop = take = None
            reason = 'Short-Ziel wäre nicht plausibel positiv; deshalb NO TRADE.'
        else:
            reason = 'Zwei Schlusskurse unterhalb der vorangegangenen Handelsspanne und EMA20 unter EMA50.'
    raw = {
        'signal': signal, 'trend': trend,
        'market_regime': 'Trendfilter EMA20/EMA50' if trend != 'seitwärts' else 'Keine klare Trendbestätigung',
        'data_quality': 'gut',
        'summary': f'{reason} Offline-Regeln für {market} ({style}, {timeframe}); letzter CSV-Schlusskurs {close:.3f}.',
        'observations': [
            f'EMA20: {ema20:.3f} | EMA50: {ema50:.3f}',
            f'ATR(14): {atr:.3f} Preiseinheiten (Volatilität, keine Prognose)',
            f'Letzter CSV-Schluss: {close:.3f}; {len(df)} verwendete Kerzen',
        ],
        'supports': [f'Tief der vorherigen 20 Kerzen: {support:.3f}'],
        'resistances': [f'Hoch der vorherigen 20 Kerzen: {resistance:.3f}'],
        'long_condition': 'EMA20 > EMA50, Schlusskurs über EMA20, zwei aufeinanderfolgende Schlüsse oberhalb des vorherigen 20-Kerzen-Hochs plus 0,15 ATR.',
        'short_condition': 'EMA20 < EMA50, Schlusskurs unter EMA20, zwei aufeinanderfolgende Schlüsse unterhalb des vorherigen 20-Kerzen-Tiefs minus 0,15 ATR.',
        'proposed_entry': entry, 'stop_loss': stop, 'take_profit': take,
        'invalidation': 'Gegenausbruch, Wechsel des Trendfilters oder Kurs durch hypothetischen Stop-Loss.',
        'risk_flags': [
            'Rein regelbasierte Kursdatenanalyse, KEINE KI-Bilderkennung und keine validierte Strategie.',
            'CSV kann alt, falsch skaliert oder unvollständig sein; kein Live-Markt.',
            'Keine Prüfung von News, Slippage, Spread, Kommissionen oder Marktliquidität.',
            'Historische Kursmuster gewährleisten keine Gewinne; erst im Demokonto prüfen.',
        ],
        'detected_symbol': market + ' (manuell gewählt)',
        'detected_timeframe': timeframe + ' (manuell gewählt)',
        'screenshot_time': str(df.time.iloc[-1]) if 'time' in df else 'Zeitstempel nicht vorhanden',
    }
    result = normalize_analysis(raw)
    meta = {'close': close, 'atr': atr, 'ema20': ema20, 'ema50': ema50, 'support': support, 'resistance': resistance}
    return result, enriched, meta
