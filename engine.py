"""Sicherheitsvalidierung für Analyseergebnisse; keinerlei Broker-Orders."""
from __future__ import annotations
import json
import re
from typing import Any

SIGNALS = {"LONG", "SHORT", "NO TRADE"}
TRENDS = {"aufwärts", "abwärts", "seitwärts", "unklar"}
QUALITY = {"gut", "mittel", "schwach"}

def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        num = float(value)
    except (ValueError, TypeError):
        return None
    if num != num or num in (float("inf"), float("-inf")):
        return None
    return num

def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip()[:400] for v in value if str(v).strip()][:12]

def extract_json(text: str) -> dict[str, Any]:
    source = text.strip()
    source = re.sub(r'^```(?:json)?\s*', '', source, flags=re.IGNORECASE)
    source = re.sub(r'\s*```$', '', source)
    parsed = json.loads(source)
    if not isinstance(parsed, dict):
        raise ValueError('Keine JSON-Objekt-Antwort.')
    return parsed

def normalize_analysis(raw: dict[str, Any]) -> dict[str, Any]:
    signal = str(raw.get('signal', 'NO TRADE')).upper().strip()
    signal = signal if signal in SIGNALS else 'NO TRADE'
    trend = str(raw.get('trend', 'unklar')).lower().strip()
    if trend not in TRENDS:
        trend = 'unklar'
    quality = str(raw.get('data_quality', 'schwach')).lower().strip()
    if quality not in QUALITY:
        quality = 'schwach'
    entry = _to_float(raw.get('proposed_entry'))
    stop = _to_float(raw.get('stop_loss'))
    take = _to_float(raw.get('take_profit'))
    flags = _strings(raw.get('risk_flags'))
    if signal in ('LONG', 'SHORT'):
        coherent = all(v is not None and v > 0 for v in (entry, stop, take))
        if coherent:
            coherent = (stop < entry < take) if signal == 'LONG' else (take < entry < stop)
        if not coherent:
            flags.append('Ungültiges Entry/SL/TP-Setup: auf NO TRADE zurückgesetzt.')
            signal = 'NO TRADE'
    if quality == 'schwach' and signal != 'NO TRADE':
        flags.append('Unzureichende Datenqualität: auf NO TRADE zurückgesetzt.')
        signal = 'NO TRADE'
    if signal == 'NO TRADE':
        entry = stop = take = None
    rr = None
    if signal in ('LONG', 'SHORT'):
        risk = abs(entry-stop)
        rr = round(abs(take-entry)/risk, 2) if risk > 0 else None
    return {
        'signal': signal, 'trend': trend,
        'market_regime': str(raw.get('market_regime','unklar'))[:60],
        'data_quality': quality,
        'summary': str(raw.get('summary','Nicht genügend Informationen.'))[:1200],
        'observations': _strings(raw.get('observations')),
        'supports': _strings(raw.get('supports')),
        'resistances': _strings(raw.get('resistances')),
        'long_condition': str(raw.get('long_condition',''))[:600],
        'short_condition': str(raw.get('short_condition',''))[:600],
        'proposed_entry': entry,
        'stop_loss': stop,
        'take_profit': take,
        'risk_reward': rr,
        'invalidation': str(raw.get('invalidation',''))[:600],
        'risk_flags': flags,
        'detected_symbol': str(raw.get('detected_symbol','unbekannt'))[:40],
        'detected_timeframe': str(raw.get('detected_timeframe','unbekannt'))[:40],
        'screenshot_time': str(raw.get('screenshot_time','unbekannt'))[:80],
    }
