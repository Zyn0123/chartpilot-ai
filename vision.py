"""Opt-in Gemini image understanding. No API request without explicit user action.

On Google's free tier submitted content may be used for product improvement.
This module never calls broker APIs or saves keys.
"""
from __future__ import annotations
import base64
import requests

from engine import extract_json, normalize_analysis

MODEL = "gemini-2.5-flash"
ALLOWED_MIME = {"image/png","image/jpeg","image/webp"}
MAX_BYTES = 5_000_000
PROMPT = """
Du bist ein nüchterner Assistent für HISTORISCHE TradingView-Chart-Bilder.
Antworte NUR mit einem JSON-Objekt auf Deutsch (kein Markdown).
Kein Internet, keine aktuellen Nachrichten oder Live-Kurse; nur Bildinhalt bewerten.
Identifiziere sichtbare Marktstruktur und klassifiziere SETUP-TYP:
BREAKOUT, PULLBACK, RANGE oder NONE. Keine anderen Setups erfinden.
Wenn Symbol, Zeitrahmen, Preisachse oder jüngste Kerzen unscharf, verdeckt oder nicht sichtbar:
signal = "NO TRADE", data_quality = "schwach" und alle Preise = null.
Das gezeigte Bild kann älter als der aktuelle Marktstand sein. Nicht behaupten "jetzt kaufen".
Wenn ein Setup nur eventuell bevorsteht, wähle "NO TRADE", beschreibe Bedingung im Text.
Bei klaren Signalen sind Entry, Einstiegskorridor, SL, TP1 und TP2 lediglich
HYPOTHETISCHE, AUS DEM BILD GESCHÄTZTE PLANUNGSZONEN, nie garantierte Ausführung.
Wähle niemals willkürliche Preislevel; falls Zahlen nicht präzise ablesbar: NO TRADE.
Die Felder müssen vollständig sein:
signal: "LONG" | "SHORT" | "NO TRADE"
setup_type: "BREAKOUT" | "PULLBACK" | "RANGE" | "NONE"
trend: "aufwärts" | "abwärts" | "seitwärts" | "unklar"
market_regime: String
data_quality: "gut" | "mittel" | "schwach"
legible_price_scale: boolean
legible_recent_candles: boolean
summary: String
observations: Liste
supports: Liste lesbarer Preiszonen (Strings)
resistances: Liste lesbarer Preiszonen (Strings)
long_condition: String
short_condition: String
entry_trigger: String (präziser Bestätigungs-Trigger, z.B. Kerzenschluss)
proposed_entry: positive Zahl oder null
entry_zone_low: positive Zahl oder null
entry_zone_high: positive Zahl oder null
stop_loss: positive Zahl oder null
take_profit: positive Zahl oder null (TP1)
take_profit_2: positive Zahl oder null (TP2)
invalidation: String
risk_flags: Liste
detected_symbol: vollständiges lesbares Chart-Symbol, sonst "unbekannt"
detected_timeframe: lesbarer Zeitrahmen, sonst "unbekannt"
screenshot_time: sichtbarer Zeitpunkt, sonst "unbekannt"
Price ordering LONG: SL < EntryZoneLow <= Entry <= EntryZoneHigh < TP1 < TP2
Price ordering SHORT: TP2 < TP1 < EntryZoneLow <= Entry <= EntryZoneHigh < SL
Ausreichender Abstand für CRV erforderlich. Kein Zukunftswissen, keine erfundenen Gewinnquoten.
"""

def validate_vision_plan(raw: dict) -> dict:
    """Fail closed if the image model cannot establish a coherent price corridor."""
    from math import isfinite
    result=normalize_analysis(raw)
    setup=str(raw.get("setup_type", "NONE")).upper().strip()
    result["setup_type"]=setup if setup in ("BREAKOUT","PULLBACK","RANGE") else "NONE"
    result["entry_trigger"]=str(raw.get("entry_trigger", "")).strip()[:400]
    result["image_readable"]=(
        raw.get("legible_price_scale") is True and
        raw.get("legible_recent_candles") is True
    )
    for field in ("entry_zone_low","entry_zone_high","take_profit_2"):
        value=raw.get(field)
        try:
            num=float(value) if value is not None and not isinstance(value,bool) else None
        except (TypeError,ValueError):
            num=None
        result[field]=num if num is not None and isfinite(num) and num>0 else None
    valid_meta=(
        result["detected_symbol"].strip().lower() not in ("","unknown","unbekannt")
        and result["detected_timeframe"].strip().lower() not in ("","unknown","unbekannt")
    )
    if result["signal"] != "NO TRADE":
        side=result["signal"]
        entry=result["proposed_entry"]
        stop=result["stop_loss"]
        tp1=result["take_profit"]
        tp2=result["take_profit_2"]
        lo=result["entry_zone_low"]
        hi=result["entry_zone_high"]
        complete=all(v is not None for v in (entry,stop,tp1,tp2,lo,hi))
        ordered=False
        if complete:
            ordered=(stop < lo <= entry <= hi < tp1 < tp2) if side=="LONG" else (
                tp2 < tp1 < lo <= entry <= hi < stop
            )
        risk=abs(entry-stop) if complete else 0.
        rr1=abs(tp1-entry)/risk if risk else 0.
        rr2=abs(tp2-entry)/risk if risk else 0.
        if not all((result["image_readable"], valid_meta,
                    result["setup_type"] != "NONE", bool(result["entry_trigger"]),
                    complete, ordered, rr1 >= .65, rr2 >= 1.25)):
            result["signal"]="NO TRADE"
            result["risk_flags"].append(
                "Bild-, Setup- oder Preisprüfung unvollständig: kein belastbarer Plan, NO TRADE."
            )
    if result["signal"]=="NO TRADE":
        for field in ("proposed_entry","entry_zone_low","entry_zone_high",
                      "stop_loss","take_profit","take_profit_2","risk_reward"):
            result[field]=None
    result["risk_flags"].append(
        "Alle Bild-Preise sind visuelle Schätzwerte, nicht gegen OHLC/Live-Brokerkurse geprüft."
    )
    return result


def analyze_screenshot(image_bytes: bytes, mime_type: str, api_key: str) -> dict:
    if mime_type not in ALLOWED_MIME:
        raise ValueError("Unterstützt werden PNG, JPEG und WebP.")
    if not image_bytes or len(image_bytes) > MAX_BYTES:
        raise ValueError("Bild bitte kleiner als 5 MB halten.")
    if not api_key or len(api_key.strip()) < 15:
        raise ValueError("Bitte einen gültigen persönlichen Gemini-API-Key eingeben.")
    request = {
        "contents":[{
            "role":"user",
            "parts":[
                {"text":PROMPT},
                {"inline_data":{"mime_type":mime_type,
                                "data":base64.b64encode(image_bytes).decode("ascii")}}
            ],
        }],
        "generationConfig":{"temperature":0.1,"responseMimeType":"application/json"},
    }
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    try:
        res=requests.post(url,headers={"x-goog-api-key":api_key.strip(),
                                        "Content-Type":"application/json"},
                          json=request,timeout=35)
        if res.status_code in (401,403):
            raise ValueError("Key nicht akzeptiert oder der API-Zugang ist nicht freigeschaltet.")
        if res.status_code==429:
            raise ValueError("Gemini-Rate-Limit erreicht. Der kostenlose Tarif kann begrenzt sein.")
        res.raise_for_status()
        obj=res.json()
        candidates=obj.get("candidates",[])
        if not candidates:
            raise ValueError("Das Modell hat keine auswertbare Antwort geliefert.")
        parts=candidates[0].get("content",{}).get("parts",[])
        content="".join(p.get("text","") for p in parts if isinstance(p.get("text"),str))
        result=validate_vision_plan(extract_json(content))
        return result
    except requests.Timeout as exc:
        raise ValueError("Zeitüberschreitung beim KI-Anbieter.") from exc
    except requests.HTTPError as exc:
        raise ValueError("KI-Anbieter konnte die Anfrage nicht bearbeiten. Kontingent/Modell prüfen.") from exc
    except (KeyError,TypeError,IndexError) as exc:
        raise ValueError("Unerwartetes Antwortformat der Bild-KI.") from exc
