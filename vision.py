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
Du analysierst EIN HISTORISCHES Chart-Screenshot für ein edukatives Trading-Journal.
Gib NUR valides JSON-Objekt ohne markdown aus, in Deutsch.
Das Bild kann unvollständig oder unlesbar sein. Erfinde KEINE Preise oder Daten.
Wenn Kursachse, Symbol, Zeitrahmen oder letzte Kerzen nicht zweifelsfrei lesbar sind:
signal NO TRADE, data_quality schwach, sämtliche drei Zahlen null.
Du hast KEINEN Live-Feed, keine News, keinen Broker und keine Garantie.
Wähle lieber NO TRADE, wenn der Kontext fehlt.
Felder:
signal: LONG | SHORT | NO TRADE
trend: aufwärts | abwärts | seitwärts | unklar
market_regime: String
data_quality: gut | mittel | schwach
summary: kurze Erklärung
observations: Liste konkreter sichtbarer Fakten
supports: Liste geschätzter sichtbarer Preiszonen als Strings
resistances: Liste geschätzter sichtbarer Preiszonen als Strings
long_condition: String (Bestätigung, nicht Gewissheit)
short_condition: String
proposed_entry: Zahl oder null
stop_loss: Zahl oder null
take_profit: Zahl oder null
invalidation: String
risk_flags: Liste Datenrisiken
detected_symbol: Chart-Symbol, sonst 'unbekannt'
detected_timeframe: Chart-Zeitrahmen, sonst 'unbekannt'
screenshot_time: sichtbare Zeit falls vorhanden, sonst 'unbekannt'
Sehr wichtig: Trade-Richtung nur wenn konkretes Setup sichtbar und Zahlen logisch lesbar;
sonst NO TRADE. Keine Gewinnwahrscheinlichkeiten erfinden.
"""

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
        result=normalize_analysis(extract_json(content))
        if result['detected_symbol'].lower() in ('unbekannt','unknown','') or (
            result['detected_timeframe'].lower() in ('unbekannt','unknown','')
        ):
            result['signal']='NO TRADE'
            result['proposed_entry']=result['stop_loss']=result['take_profit']=result['risk_reward']=None
            result['risk_flags'].append("Symbol oder Zeitrahmen nicht sicher erkennbar; NO TRADE.")
        result['risk_flags'].append("Bild-KI kann Kerzen und Preisachsen falsch lesen; kein Live-Feed und keine Order.")
        return result
    except requests.Timeout as exc:
        raise ValueError("Zeitüberschreitung beim KI-Anbieter.") from exc
    except requests.HTTPError as exc:
        raise ValueError("KI-Anbieter konnte die Anfrage nicht bearbeiten. Kontingent/Modell prüfen.") from exc
    except (KeyError,TypeError,IndexError) as exc:
        raise ValueError("Unerwartetes Antwortformat der Bild-KI.") from exc
