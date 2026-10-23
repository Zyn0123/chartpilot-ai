"""Three transparent historical setup hypotheses. Not a live signal service.

All conditions use only candles at or before the analysis candle. Entries/stops/targets
are hypothetical; they are *not* executable trade instructions.
"""
from __future__ import annotations

from math import isfinite
import pandas as pd
from offline import analyze_ohlc
from engine import normalize_analysis

SETUPS = ("BREAKOUT", "PULLBACK", "RANGE")


def _proposal(name: str, side: str, state: str, why: str, trigger: str,
              *, entry: float | None = None, stop: float | None = None,
              tp1: float | None = None, tp2: float | None = None,
              zone_low: float | None = None, zone_high: float | None = None) -> dict:
    """Reject inconsistent or unusable numerical plans rather than forcing a trade."""
    result = dict(setup=name, side=side, state=state, why=why, trigger=trigger,
                  entry=entry, stop=stop, tp1=tp1, tp2=tp2,
                  zone_low=zone_low, zone_high=zone_high, rr1=None, rr2=None)
    if state != "BESTÄTIGT" or side not in ("LONG", "SHORT"):
        return result
    values=(entry, stop, tp1, tp2, zone_low, zone_high)
    if any(x is None or not isfinite(x) or x <= 0 for x in values):
        result.update(state="BEOBACHTEN", why=why+" Kein vollständiger plausibler Preisplan.")
        return result
    coherent = (
        stop < zone_low <= entry <= zone_high < tp1 < tp2 if side == "LONG"
        else tp2 < tp1 < zone_low <= entry <= zone_high < stop
    )
    if not coherent:
        result.update(state="BEOBACHTEN", why=why+" Preise/Stop/Ziele nicht in korrekter Reihenfolge.")
        return result
    risk = abs(entry - stop)
    r1 = abs(tp1 - entry) / risk
    r2 = abs(tp2 - entry) / risk
    if r1 < .65 or r2 < 1.25:
        result.update(state="BEOBACHTEN", why=why+" Zu wenig rechnerisches Chance/Risiko.")
        return result
    result.update(rr1=round(r1,2), rr2=round(r2,2))
    return result


def _zone(entry: float, atr: float, side: str) -> tuple[float, float]:
    # Width capped by 0.15 ATR, avoids presenting a point prediction as exact.
    width = max(atr * .12, entry * .000005)
    return (max(.000001, entry-width), entry) if side=="LONG" else (entry, entry+width)


def evaluate_setups(enriched: pd.DataFrame, base: dict, meta: dict, style: str) -> list[dict]:
    """Compare a conservative breakout with a trend pullback and a bounded range bounce."""
    if len(enriched) < 60:
        raise ValueError("Für die Strategien werden mindestens 60 Kerzen benötigt.")
    row = enriched.iloc[-1]
    prev = enriched.iloc[-2]
    close=float(row.close)
    atr=float(meta["atr"])
    ema20=float(row.EMA20)
    ema50=float(row.EMA50)
    if not isfinite(atr) or atr <= 0:
        return [_proposal(s,"NONE","KEIN SETUP","ATR nicht auswertbar.","Neue vollständige Kursdaten laden.") for s in SETUPS]
    rsi=meta.get("rsi")
    rsi_ok=rsi is not None and isfinite(rsi)
    recent=enriched.iloc[-26:-1]
    low_25=float(recent.low.min())
    high_25=float(recent.high.max())

    # Breakout: reuses the original tested rule, but exposes its proposed zone/TP2.
    if base["signal"] in ("LONG","SHORT"):
        side=base["signal"]
        entry=base["proposed_entry"]
        stop=base["stop_loss"]
        tp1=base["take_profit"]
        risk=abs(entry-stop)
        tp2=entry + (3*risk if side=="LONG" else -3*risk)
        lo,hi=_zone(entry,atr,side)
        breakout=_proposal("BREAKOUT",side,"BESTÄTIGT",
            "EMA-Trend und zwei Ausbruchsschlüsse sind bestätigt.",
            "Nur nach abgeschlossener Bestätigungskerze; Folgekerze prüfen.",
            entry=entry,stop=stop,tp1=tp1,tp2=tp2,zone_low=lo,zone_high=hi)
    else:
        b=meta["checks"]
        side="LONG" if b["long_trend"] else ("SHORT" if b["short_trend"] else "NONE")
        breakout=_proposal("BREAKOUT",side,"BEOBACHTEN",
            "Ausbruch nicht bestätigt: LONG "+str(b["long_confirmations"])+
            "/2, SHORT "+str(b["short_confirmations"])+"/2 Schlusskerzen.",
            "Zwei Schlusskurse jenseits der 20-Kerzen-Spanne mit ATR-Puffer abwarten.")

    # Trend pullback: the previous candle touched the EMA zone; latest candle
    # closes back through the EMA and through the previous candle high/low.
    up=ema20>ema50 and close>ema20
    down=ema20<ema50 and close<ema20
    touched_long=float(prev.low) <= float(prev.EMA20)+atr*.20 and float(prev.low) >= ema20-2.4*atr
    touched_short=float(prev.high) >= float(prev.EMA20)-atr*.20 and float(prev.high) <= ema20+2.4*atr
    reclaim_long=close>float(prev.high) and close>float(prev.close)
    reclaim_short=close<float(prev.low) and close<float(prev.close)
    # Avoid taking pullbacks into extreme RSI conditions.
    viable_long=up and touched_long and reclaim_long and (not rsi_ok or rsi<75)
    viable_short=down and touched_short and reclaim_short and (not rsi_ok or rsi>25)
    if viable_long or viable_short:
        side="LONG" if viable_long else "SHORT"
        entry=close
        if side=="LONG":
            stop=min(float(prev.low),float(row.low),ema20-atr*.6)-atr*.2
            risk=entry-stop
            tp1=entry+1.25*risk
            tp2=entry+2.25*risk
        else:
            stop=max(float(prev.high),float(row.high),ema20+atr*.6)+atr*.2
            risk=stop-entry
            tp1=entry-1.25*risk
            tp2=entry-2.25*risk
        lo,hi=_zone(entry,atr,side)
        pullback=_proposal("PULLBACK",side,"BESTÄTIGT",
             "Rücksetzer an EMA20 mit bestätigtem Reclaim in EMA20/50-Trendrichtung.",
             "Reclaim-Schluss bestätigen, nicht direkt in eine offene Kerze springen.",
             entry=entry,stop=stop,tp1=tp1,tp2=tp2,zone_low=lo,zone_high=hi)
    else:
        side="LONG" if up else ("SHORT" if down else "NONE")
        pullback=_proposal("PULLBACK",side,"BEOBACHTEN",
            "Es fehlen EMA20-Berührung, bestätigter Reclaim oder passender Trend.",
            "Erst Rücksetzer an EMA20 und Schluss über/unter Vorkerzen-Extrem prüfen.")

    # Range: trend neutrality and a bounded prior 25-candle range.
    width=high_25-low_25
    neutral=abs(ema20-ema50) <= .55*atr
    bounded=2.0*atr <= width <= 12.*atr
    location=(close-low_25)/width if width>0 else .5
    bounce_long=(float(prev.low)<=low_25+.22*atr and
                 close>float(prev.close) and close>float(prev.open) and
                 0.0 <= location <= .38)
    bounce_short=(float(prev.high)>=high_25-.22*atr and
                  close<float(prev.close) and close<float(prev.open) and
                  .62 <= location <= 1.0)
    if neutral and bounded and (bounce_long or bounce_short):
        side="LONG" if bounce_long else "SHORT"
        entry=close
        if side=="LONG":
            stop=low_25-.3*atr
            tp1=(low_25+high_25)/2
            tp2=high_25-.25*atr
        else:
            stop=high_25+.3*atr
            tp1=(low_25+high_25)/2
            tp2=low_25+.25*atr
        lo,hi=_zone(entry,atr,side)
        range_setup=_proposal("RANGE",side,"BESTÄTIGT",
            "Seitwärtsfilter und Reaktion am Rand der historischen 25-Kerzen-Spanne.",
            "Bestätigte Umkehrkerze am Rand; beachten, dass ein Range-Ausbruch die Idee aufhebt.",
            entry=entry,stop=stop,tp1=tp1,tp2=tp2,zone_low=lo,zone_high=hi)
    else:
        range_setup=_proposal("RANGE","NONE","BEOBACHTEN",
            "Keine bestätigte Umkehrreaktion an einer begrenzten Seitwärtszone.",
            "Erst neutrale EMA-Struktur und bestätigte Umkehr am Spannenrand.")
    return [breakout,pullback,range_setup]


def analyze_strategies(df: pd.DataFrame, market: str, style: str, timeframe: str):
    """Combined result, indicators, and per-strategy transparency metadata."""
    base, enriched, meta = analyze_ohlc(df,market,style,timeframe)
    candidates=evaluate_setups(enriched,base,meta,style)
    confirmed=[x for x in candidates if x["state"]=="BESTÄTIGT"]
    sides={x["side"] for x in confirmed}
    selected = confirmed[0] if confirmed and len(sides)==1 else None
    if selected:
        updated=dict(base)
        updated.update(signal=selected["side"], proposed_entry=selected["entry"],
                       stop_loss=selected["stop"], take_profit=selected["tp1"],
                       summary=(
                           f"{selected['setup']} – historisch bestätigte Regelbedingungen. "
                           f"{selected['why']} Hypothetische Preiszone, keine Echtzeit-Ausführung."
                       ),
                       long_condition=selected["trigger"] if selected["side"]=="LONG" else base["long_condition"],
                       short_condition=selected["trigger"] if selected["side"]=="SHORT" else base["short_condition"])
        result=normalize_analysis(updated)
        if result["signal"]=="NO TRADE":
            selected=None
    if not selected:
        updated=dict(base)
        updated.update(signal="NO TRADE",proposed_entry=None,stop_loss=None,take_profit=None,
            summary=("Konflikt zwischen Strategien; keine klare Richtung." if len(sides)>1 else
                     "Keine der drei Strategien erfüllt momentan alle Bestätigungsbedingungen. "
                     "Mögliche Setups stehen unten als Beobachtungen."))
        result=normalize_analysis(updated)
    meta["strategies"]=candidates
    meta["selected_strategy"]=selected["setup"] if selected else None
    meta["plan"]=selected
    meta["conflict"]=len(sides)>1
    return result,enriched,meta
