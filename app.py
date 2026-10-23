"""ChartPilot V2 · independent black/purple market research workstation.

Trading education and paper trading only. No automatic or real-money order routing.
"""
from __future__ import annotations

import io
import csv
from hashlib import sha256
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from backtest import run_backtest
from market_data import MARKETS, PERIODS, fetch_history
from offline import analyze_ohlc, load_ohlc
from strategies import analyze_strategies
from quality import inspect_candles
from theme import apply_theme, label
from vision import analyze_screenshot, MODEL

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "sample" / "demo_simuliert_5m.csv"
MENU = ["01  COCKPIT", "02  DATA HUB", "03  VISION AI", "04  STRATEGY LAB", "05  RISK DESK", "06  JOURNAL", "07  SOURCES"]
NAV_LABELS = {
    "01  COCKPIT": "01    MARKT-COCKPIT",
    "02  DATA HUB": "02    DATENZENTRALE",
    "03  VISION AI": "03    VISION AI",
    "04  STRATEGY LAB": "04    STRATEGIE-LABOR",
    "05  RISK DESK": "05    RISIKO-DESK",
    "06  JOURNAL": "06    TRADING-JOURNAL",
    "07  SOURCES": "07    DATEN & QUELLEN",
}

st.set_page_config(page_title="ChartPilot / Terminal V2", page_icon="◆", layout="wide", initial_sidebar_state="expanded")
apply_theme(st)

@st.cache_data(ttl=300, show_spinner=False, max_entries=24)
def cached_feed(symbol: str, interval: str) -> pd.DataFrame:
    return fetch_history(symbol, interval)

def fancy_chart(history: pd.DataFrame) -> None:
    """Candles/EMA in a genuinely data-scaled chart: no decorative fake chart lines."""
    frame = history.tail(170).copy().reset_index(drop=True)
    if not {"EMA20","EMA50"}.issubset(frame.columns):
        return
    frame["x"] = list(range(len(frame)))
    axis = alt.X("x:Q", title="Kerze – zeitlich aufsteigend", axis=alt.Axis(grid=False))
    price = alt.Y("low:Q", title="Preis / Punkte", scale=alt.Scale(zero=False))
    wick = alt.Chart(frame).mark_rule(strokeWidth=1.6).encode(
        x=axis, y=price, y2="high:Q",
        color=alt.condition("datum.close >= datum.open", alt.value("#b879ff"), alt.value("#ff4778")),
        tooltip=[alt.Tooltip("x:Q"),alt.Tooltip("open:Q",format=".3f"),alt.Tooltip("high:Q",format=".3f"),
                 alt.Tooltip("low:Q",format=".3f"),alt.Tooltip("close:Q",format=".3f")],
    )
    body = alt.Chart(frame).mark_bar(size=5).encode(
        x=axis, y=alt.Y("open:Q",scale=alt.Scale(zero=False)), y2="close:Q",
        color=alt.condition("datum.close >= datum.open", alt.value("#b879ff"), alt.value("#ff4778")),
    )
    ema20 = alt.Chart(frame).mark_line(color="#f5ecff",strokeWidth=1.7).encode(
        x=axis,y=alt.Y("EMA20:Q",scale=alt.Scale(zero=False)))
    ema50 = alt.Chart(frame).mark_line(color="#7140ad",strokeWidth=1.8).encode(
        x=axis,y=alt.Y("EMA50:Q",scale=alt.Scale(zero=False)))
    chart = (wick + body + ema20 + ema50).properties(height=400).configure_view(
        stroke="#332244",fill="#100b18"
    ).configure_axis(
        labelColor="#b3a6c5",titleColor="#c9b6de",gridColor="#2a1b3c",domainColor="#563374"
    ).configure(background="#100b18")
    st.altair_chart(chart, use_container_width=True)
    st.caption("◆ Lila: steigende Kerze   ◆ Pink: fallende Kerze   ◆ Weiß: EMA20   ◆ Dunkellila: EMA50  ·  Kerzenfarben sind keine Handlungsempfehlung.")
    if "RSI14" in frame.columns and frame["RSI14"].notna().any():
        rsi_line = alt.Chart(frame).mark_line(color="#b568ff",strokeWidth=2).encode(
            x=alt.X("x:Q",title="Kerze",axis=alt.Axis(grid=False)),
            y=alt.Y("RSI14:Q",title="RSI 14",scale=alt.Scale(domain=[0,100])),
            tooltip=[alt.Tooltip("x:Q"),alt.Tooltip("RSI14:Q",format=".1f")])
        thresholds = alt.Chart(pd.DataFrame({"level":[30.,70.]})).mark_rule(
            color="#76519c",strokeDash=[5,5],strokeWidth=1).encode(y="level:Q")
        rsi_chart = (rsi_line + thresholds).properties(height=110).configure_view(
            stroke="#332244",fill="#100b18").configure_axis(
            labelColor="#b3a6c5",titleColor="#c9b6de",gridColor="#24142f")
        st.altair_chart(rsi_chart,use_container_width=True)
        st.caption("RSI 14: 30 / 70 sind Orientierungszonen, keine automatisch gültigen Kauf-/Verkaufssignale.")

def bullets(items):
    for x in items:
        st.markdown("- " + str(x))

def show_result(a: dict, *, is_vision: bool=False) -> None:
    sign = a["signal"]
    name = {"LONG":"LONG / HYPOTHESE","SHORT":"SHORT / HYPOTHESE","NO TRADE":"NO TRADE"}[sign]
    st.markdown('<div class="cp-signal"><span class="cp-kicker">ANALYSE / NICHT LIVE</span><div><strong>'+
                escape(name)+'</strong></div><div class="cp-tiny">Keine automatische Order • Kein geprüftes Gewinnsignal</div></div>',
                unsafe_allow_html=True)
    st.write(a["summary"])
    met = st.columns(3)
    met[0].metric("Trendfilter",a["trend"].upper())
    met[1].metric("Marktphase",a["market_regime"])
    met[2].metric("Datenqualität",a["data_quality"].upper())
    with st.expander("MARKTSTRUKTUR & NIVEAUS",expanded=True):
        st.markdown("**Beobachtungen**")
        bullets(a["observations"] or ["Keine verlässlichen Merkmale vorhanden."])
        l,r=st.columns(2)
        with l:
            st.markdown("**Unterstützung**")
            bullets(a["supports"])
        with r:
            st.markdown("**Widerstand**")
            bullets(a["resistances"])
    if sign!="NO TRADE":
        cs=st.columns(4)
        cs[0].metric("Entry-Idee",f"{a['proposed_entry']:.3f}")
        cs[1].metric("Stop-Loss",f"{a['stop_loss']:.3f}")
        cs[2].metric("Take-Profit",f"{a['take_profit']:.3f}")
        cs[3].metric("CRV (ohne Kosten)",f"1 : {a['risk_reward']:.2f}")
        st.warning("Hypothetische Werte ohne Orderbuch, Spread oder Broker-Ausführung. Vor Nutzung im Paper-Trading prüfen.")
    else:
        st.info("Kein bestätigter Einstieg. Die KI bzw. Regelprüfung darf ausdrücklich NO TRADE ausgeben.")
    if is_vision:
        st.markdown("### ◆ BILD-KI / PREISZONEN")
        if sign != "NO TRADE":
            lo=a.get("entry_zone_low")
            hi=a.get("entry_zone_high")
            tp2=a.get("take_profit_2")
            st.warning("Visuelle Preis-Schätzungen aus dem Screenshot – nicht gegen OHLC- oder Brokerkurse geprüft.")
            parts=st.columns(4)
            parts[0].metric("ENTRY-ZONE",f"{lo:.3f} – {hi:.3f}" if lo is not None and hi is not None else "NICHT LESBAR")
            parts[1].metric("TP1",f"{a['take_profit']:.3f}")
            parts[2].metric("TP2",f"{tp2:.3f}" if tp2 is not None else "NICHT LESBAR")
            parts[3].metric("SETUP",a.get("setup_type","NONE"))
            st.write("**Bestätigung vor einem möglichen Trade:** "+(a.get("entry_trigger") or "Keine bestätigt"))
        else:
            st.info("Kein belastbarer Preisplan aus dem Bild ableitbar.")
    with st.expander("BEDINGUNGEN & RISIKEN",expanded=True):
        st.markdown("**LONG nur falls**")
        st.write(a["long_condition"] or "Nicht bekannt")
        st.markdown("**SHORT nur falls**")
        st.write(a["short_condition"] or "Nicht bekannt")
        st.markdown("**Ungültig sobald**")
        st.write(a["invalidation"])
        bullets(a["risk_flags"])
    st.caption(("Bild-KI-Vorschlag" if is_vision else "Transparente Kursdaten-Regeln")
               +" · "+a["detected_symbol"]+" · "+a["detected_timeframe"]+" · "+a["screenshot_time"])

def set_dataset(df: pd.DataFrame, source: str, symbol: str, interval: str, is_demo=False):
    result, enriched, diagnostics = analyze_strategies(df,symbol,style,interval)
    st.session_state.dataset = {
        "df":df, "enriched":enriched,"result":result, "diagnostics":diagnostics,
        "source":source, "symbol":symbol, "interval":interval, "is_demo":is_demo,
        "style":style,
    }

def active():
    return st.session_state.get("dataset")

def show_strategy_board(diagnostics: dict | None) -> None:
    if not diagnostics or not diagnostics.get("strategies"):
        return
    strategies = diagnostics["strategies"]
    st.markdown("### ◆ SETUP RADAR / DREI STRATEGIEN")
    st.caption("Historische Regelbedingungen – keine Live-Handelsanweisung. "
               "BEOBACHTEN ist ausdrücklich kein bestätigter Einstieg.")
    cols=st.columns(3)
    names={"BREAKOUT":"01 / BREAKOUT","PULLBACK":"02 / TREND-PULLBACK","RANGE":"03 / RANGE"}
    for col, candidate in zip(cols,strategies):
        with col:
            st.markdown("**"+names[candidate["setup"]]+"**")
            st.write(candidate["side"]+" · "+candidate["state"] if candidate["state"]=="BESTÄTIGT" else "BEOBACHTEN / KEIN ENTRY")
            st.caption(candidate["why"])
            with st.expander("Trigger / Bedingung"):
                st.write(candidate["trigger"])
    plan=diagnostics.get("plan")
    if not plan:
        st.info("Keine bestätigte Entry-Zone. Details zu den drei Beobachtungen stehen oben.")
        return
    st.markdown("#### HYPOTHETISCHER PREISPLAN / "+plan["setup"]+" "+plan["side"])
    cs=st.columns(5)
    cs[0].metric("ENTRY-ZONE",f"{plan['zone_low']:.3f} – {plan['zone_high']:.3f}")
    cs[1].metric("ENTRY-REFERENZ",f"{plan['entry']:.3f}")
    cs[2].metric("STOP-LOSS",f"{plan['stop']:.3f}")
    cs[3].metric("TP1",f"{plan['tp1']:.3f}")
    cs[4].metric("TP2",f"{plan['tp2']:.3f}")
    st.caption(f"Rechnerisches CRV TP1 1:{plan['rr1']:.2f}, TP2 1:{plan['rr2']:.2f}"
               " – ohne Gebühren, Spread, Slippage und Gaps.")
    st.write("**Bestätigung:** "+plan["trigger"])


def show_entry_diagnostics(diagnostics: dict | None) -> None:
    """Why the strict current rules say NO TRADE (also useful if LONG/SHORT appears)."""
    if not diagnostics or not diagnostics.get("checks"):
        return
    checks = diagnostics["checks"]
    long_trend = checks["long_trend"]
    short_trend = checks["short_trend"]
    long_count = checks["long_confirmations"]
    short_count = checks["short_confirmations"]
    with st.expander("◆ WARUM LONG / SHORT / NO TRADE? / BREAKOUT-CHECK", expanded=False):
        st.caption(
            "Dieses Feld erklärt nur BREAKOUT: EMA20/50-Trend und zwei Schlüsse "
            "außerhalb der alten 20-Kerzen-Spanne mit ATR-Abstand. "
            "Pullback und Range werden oben eigenständig geprüft."
        )
        left, right = st.columns(2)
        with left:
            st.markdown("**LONG-CHECK**")
            st.write(("✅" if long_trend else "❌") + " EMA20 über EMA50 und Kurs über EMA20")
            st.write(("✅" if long_count == 2 else "❌") +
                     f" Ausbruch: {long_count}/2 Kerzen bestätigt")
            st.caption(f"Preisgrenze für die zwei Schlüsse: über {checks['long_threshold']:.3f}")
        with right:
            st.markdown("**SHORT-CHECK**")
            st.write(("✅" if short_trend else "❌") + " EMA20 unter EMA50 und Kurs unter EMA20")
            st.write(("✅" if short_count == 2 else "❌") +
                     f" Ausbruch: {short_count}/2 Kerzen bestätigt")
            st.caption(f"Preisgrenze für die zwei Schlüsse: unter {checks['short_threshold']:.3f}")
        if long_trend and long_count < 2:
            st.info("Beobachtung LONG: Der Trendfilter passt, aber der Ausbruch ist noch nicht vollständig bestätigt.")
        elif short_trend and short_count < 2:
            st.info("Beobachtung SHORT: Der Trendfilter passt, aber der Ausbruch ist noch nicht vollständig bestätigt.")
        elif not long_trend and not short_trend:
            st.info("Weder der LONG- noch der SHORT-Trendfilter ist derzeit bestätigt.")
        st.caption(
            "RSI ist im Pullback ein Überdehnungsfilter; MACD dient als Zusatzinformation. "
            "Die Strategien sind nicht auf Profitabilität validiert."
        )


def display_dataset(ds: dict, show_full=True):
    audit=inspect_candles(ds["df"],ds["source"],ds["interval"],is_demo=ds["is_demo"])
    st.markdown('<div class="cp-strip"><b>DATENQUELLE:</b> '+escape(ds["source"])+
        ' &nbsp; • &nbsp; <b>INSTRUMENT:</b> '+escape(ds["symbol"])+
        ' &nbsp; • &nbsp; <b>KERZEN:</b> '+str(audit.candle_count)+
        ' &nbsp; • &nbsp; <b>STATUS:</b> '+escape(audit.state)+'</div>',unsafe_allow_html=True)
    st.caption("Letzte Kerze: "+audit.last_timestamp+" · Vergangene Minuten: "+
               (str(audit.age_minutes) if audit.age_minutes is not None else "nicht bestimmbar"))
    if audit.issues:
        st.warning("Datenprüfung: "+" | ".join(audit.issues))
    if ds["is_demo"]:
        st.error("DEMO: Künstliche Übungsdaten, KEIN reales Marktinstrument.")
    fancy_chart(ds["enriched"])
    if show_full:
        show_result(ds["result"])
        show_strategy_board(ds.get("diagnostics"))
        show_entry_diagnostics(ds.get("diagnostics"))
    return audit

def save_journal(ds):
    st.session_state.setdefault("journal",[])
    a=ds["result"]
    st.session_state.journal.append({
        "Zeit des Speicherns (UTC)":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "Quelle":ds["source"],"Instrument":ds["symbol"],"Zeitrahmen":ds["interval"],
        "Entscheidung":a["signal"],"Trend":a["trend"],"Bemerkung":"Beobachtung, keine ausgeführte Order",
    })

with st.sidebar:
    st.markdown(
        '<div class="cp-sidebar-brand">'
        '<div class="cp-sidebar-brand-row">'
        '<div class="cp-sidebar-monogram">CP<span>◆</span></div>'
        '<div><div class="cp-sidebar-name">CHART<span>PILOT</span></div>'
        '<div class="cp-sidebar-tagline">MARKET RESEARCH TERMINAL</div></div>'
        '</div>'
        '<div class="cp-sidebar-version"><span class="cp-status-dot"></span> TERMINAL V2.1 '
        '<span class="cp-version-right">PAPER MODE</span></div>'
        '</div>', unsafe_allow_html=True
    )
    st.markdown(
        '<div class="cp-side-section"><span class="cp-side-section-number">01</span>'
        '<span>WORKSPACE</span></div>', unsafe_allow_html=True
    )
    # Native buttons prevent the default radio dots from leaking through Streamlit CSS.
    st.session_state.setdefault("cp_page", MENU[0])
    with st.container(key="cp_navigation"):
        for position, destination in enumerate(MENU, start=1):
            selected = st.session_state.cp_page == destination
            if st.button(
                NAV_LABELS[destination], key=f"cp_nav_{position}",
                type="primary" if selected else "secondary",
                use_container_width=True,
            ):
                if not selected:
                    st.session_state.cp_page = destination
                    st.rerun()
    page = st.session_state.cp_page
    st.markdown(
        '<div class="cp-side-section cp-side-section-market">'
        '<span class="cp-side-section-number">02</span><span>MARKTKONTEXT</span></div>',
        unsafe_allow_html=True
    )
    with st.container(key="cp_market_controls"):
        symbol_label = st.selectbox("INSTRUMENT", list(MARKETS), index=0, key="symbol")
        interval = st.selectbox("ZEITRAHMEN", list(PERIODS), index=2, key="interval")
        style = st.selectbox("TRADING-STIL", ["Scalping", "Daytrading", "Swingtrading"], index=0, key="style")
    st.markdown(
        '<div class="cp-side-section cp-side-section-status">'
        '<span class="cp-side-section-number">03</span><span>DATENSTATUS</span></div>',
        unsafe_allow_html=True
    )
    sidebar_data = st.session_state.get("dataset")
    if sidebar_data:
        status_label = "DEMO / NICHT REAL" if sidebar_data.get("is_demo") else "HISTORISCHE DATEN"
        source_name = str(sidebar_data.get("source", "Unbekannte Quelle"))
        if len(source_name) > 52:
            source_name = source_name[:49] + "..."
        st.markdown(
            '<div class="cp-side-status-card">'
            '<div class="cp-side-status-title"><span class="cp-status-dot"></span>' + escape(status_label) + '</div>'
            '<div class="cp-side-status-main">' + escape(str(sidebar_data.get("symbol", "–"))) + '</div>'
            '<div class="cp-side-status-sub">' + escape(source_name) + '</div>'
            '<div class="cp-side-status-bottom">INTERVALL <b>' + escape(str(sidebar_data.get("interval", "–"))) +
            '</b><span>KERZEN <b>' + str(len(sidebar_data.get("df", []))) + '</b></span></div>'
            '</div>', unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="cp-side-status-card">'
            '<div class="cp-side-status-title"><span class="cp-status-dot cp-status-inactive"></span>KEINE DATEN GELADEN</div>'
            '<div class="cp-side-status-sub">Lade historische Kurse oder importiere eine CSV im Data Hub.</div>'
            '</div>', unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="cp-side-footer">'
        '<div class="cp-side-footer-line"><span>◆ SYSTEM</span><strong>RESEARCH ONLY</strong></div>'
        '<div>Kein Live-Feed garantiert. Keine Broker-Verbindung oder Echtgeld-Orders.</div>'
        '</div>', unsafe_allow_html=True
    )

label(st,"CHARTPILOT / SYSTEM V2","MARKET CONTROL TERMINAL","Eigenständige Analyseplattform · Flaches Schwarz-Lila-Design · Keine Echtgeld-Orderfunktion")
st.markdown('<div class="cp-rule"></div>',unsafe_allow_html=True)

ds=active()
if ds and ds.get("style") != style:
    # A change of trading style must never display an out-of-date analysis.
    result, enriched, diagnostics = analyze_strategies(ds["df"], ds["symbol"], style, ds["interval"])
    ds["result"] = result
    ds["enriched"] = enriched
    ds["diagnostics"] = diagnostics
    ds["style"] = style
if ds and ds["interval"] != interval:
    st.caption("Hinweis: Der geladene Datensatz bleibt auf " + ds["interval"] +
               ". Die neue Zeitrahmen-Auswahl wirkt erst beim nächsten Import/Abruf.")

if page.startswith("01"):
    st.subheader("MARKET COCKPIT")
    c1,c2,c3=st.columns([2.3,1.2,1.2])
    with c1:
        st.markdown('<div class="cp-slab"><div class="cp-kicker">AUSGEWÄHLTER MARKT</div><h2>'+
                    escape(symbol_label)+'</h2><div class="cp-tiny">Quelle: Yahoo Finance historisch · kein Spot-Ersatz</div></div>',
                    unsafe_allow_html=True)
    with c2:
        st.metric("KERZENINTERVALL",interval)
    with c3:
        st.metric("FOKUS",style.upper())
    if st.button("📡 Historische Kurse laden / aktualisieren",type="primary",use_container_width=True):
        try:
            with st.spinner("Lade historische Kerzen..."):
                df=cached_feed(MARKETS[symbol_label],interval)
                set_dataset(df,"Yahoo Finance (historisch)",symbol_label,interval)
        except Exception as exc:
            st.error(str(exc))
            st.info("Alternative: DATA HUB → eigene TradingView-CSV hochladen.")
    ds=active()
    if ds:
        display_dataset(ds)
        if st.button("Beobachtung im Journal merken",key="journal_cockpit"):
            save_journal(ds);st.success("Für diese Sitzung im Journal vorgemerkt.")
    else:
        st.info("Starte mit 'Historische Kurse laden' oder importiere echte TradingView-Kerzen im DATA HUB. Noch keine Daten – deshalb keine Signale.")
        st.markdown('<div class="cp-slab"><div class="cp-kicker">WAS CHARTPILOT PRÜFT</div>'
                    '<h3>EMA20 / EMA50 &nbsp; • &nbsp; ATR14 &nbsp; • &nbsp; Ausbruchsbestätigung</h3>'
                    '<div class="cp-tiny">Kostenlos, regelbasiert, ohne garantierte Prognose. Vision AI separat opt-in.</div></div>',
                    unsafe_allow_html=True)
    st.markdown("### MULTI-TIMEFRAME WATCH")
    st.caption("Vergleicht historische Trends auf mehreren Zeitfenstern; kein kontinuierliches Monitoring.")
    if st.button("5m / 15m / 1h vergleichen",key="multitf"):
        rows=[]
        for tf in ["5m","15m","1h"]:
            try:
                df=cached_feed(MARKETS[symbol_label],tf)
                result,_,_=analyze_strategies(df,symbol_label,style,tf)
                aud=inspect_candles(df,"Yahoo Finance",tf)
                rows.append({"Zeitrahmen":tf,"Trend":result["trend"],"Historisches Setup":result["signal"],
                             "Letzte Kerze":aud.last_timestamp,"Status":aud.state})
            except Exception:
                rows.append({"Zeitrahmen":tf,"Trend":"Daten fehlen","Historisches Setup":"—","Letzte Kerze":"—","Status":"Abruf fehlgeschlagen"})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

elif page.startswith("02"):
    st.subheader("DATA HUB  /  ECHTE KERZEN")
    st.markdown("#### 01 — TradingView-Export / Eigene CSV")
    st.caption("Open, High, Low, Close; optional Time, Volume. TradingView exportiert die im Chart geladenen Kerzen.")
    user_symbol=st.text_input("Bezeichnung der CSV-Quelle / Symbol (wird NICHT automatisch geprüft)",value="XAUUSD (manuell angegeben)")
    csv_file=st.file_uploader("CSV-Datei auswählen",type=["csv"],key="csvupload")
    if st.button("CSV validieren und analysieren",disabled=csv_file is None,type="primary"):
        try:
            df=load_ohlc(csv_file.getvalue())
            set_dataset(df,"CSV: "+csv_file.name,user_symbol,interval)
            st.success("CSV auf OHLC-Konsistenz und Zeitstempel geprüft.")
        except Exception as exc:
            st.error("Import fehlgeschlagen: "+str(exc))
    st.markdown("#### 02 — Historische Online-Daten")
    st.caption("Yahoo Finance (nicht garantiert live). Symbolbezeichnung links wählen, dann im Cockpit abrufen.")
    st.markdown("#### 03 — Testdatensatz (SYNTHETISCH)")
    if st.button("Simulierte Demo laden",key="demo"):
        df=load_ohlc(DEMO.read_bytes())
        set_dataset(df,"Synthetische Demo", "SIMULIERT / kein echter Kurs",interval,True)
    st.download_button("Demo-CSV herunterladen",data=DEMO.read_bytes(),file_name="chartpilot_demo.csv")
    ds=active()
    if ds:
        st.markdown("### AKTIVER DATENSATZ")
        display_dataset(ds)
        st.download_button("Aktive OHLC-Daten als CSV exportieren",
            data=ds["df"].to_csv(index=False).encode("utf-8-sig"),file_name="chartpilot_ohlc.csv",mime="text/csv")
    st.info("Quelle und Instrument sind **nie** automatisch gleichgesetzt. Gold-Future ≠ XAUUSD Spot ≠ Gold-ETF. Markt- und Zeitskala bei CSV werden vom Benutzer angegeben.")

elif page.startswith("03"):
    st.subheader("VISION AI  /  SCREENSHOT ANALYSIS")
    st.caption("Screenshot → Setup (Breakout / Pullback / Range), Entry-Zone, Stop-Loss, TP1/TP2 und Bestätigungsbedingung.")
    st.markdown('<div class="cp-strip"><b>FREE BY DEFAULT</b> · Du brauchst keine API für den DATA HUB. Bild-KI ist eine freiwillige Zusatzfunktion.</div>',
                unsafe_allow_html=True)
    image=st.file_uploader("TradingView-Chart als PNG / JPG / WEBP hochladen",type=["png","jpg","jpeg","webp"],key="vision_image")
    if image:
        current_image_digest=sha256(image.getvalue()).hexdigest()
        if st.session_state.get("vision_digest") != current_image_digest:
            st.session_state.pop("vision_result",None)
            st.session_state.pop("vision_name",None)
        if len(image.getvalue()) > 5_000_000:
            st.error("Bild maximal 5 MB.")
        else:
            st.image(image,caption="Bildvorschau (noch keine Analyse)",use_container_width=True)
        st.markdown("#### 01 — Optionale externe Bild-KI")
        st.caption("Provider: Google Gemini ("+MODEL+"). Nur auf Knopfdruck. Ein persönlicher AI-Studio-API-Key wird benötigt; kostenlose Kontingente hängen vom Konto und Tarif ab.")
        st.info("Im kostenlosen Gemini-Tarif können eingereichte Inhalte zur Produktverbesserung verwendet werden. Bitte keine persönlichen Daten im Screenshot zeigen.")
        gemini_key=st.text_input("Gemini API-Key (nur für diese Sitzung, nicht in GitHub)",type="password",key="gemini_key")
        allow_send=st.checkbox("Ich möchte das Bild bewusst an den externen KI-Anbieter senden.",key="allow_vision")
        valid_image=len(image.getvalue()) <= 5_000_000
        if st.button("◆ Screenshot mit Vision AI prüfen",type="primary",disabled=not(gemini_key and allow_send and valid_image)):
            try:
                with st.spinner("Bild-KI analysiert – kein Live-Feed..."):
                    result=analyze_screenshot(image.getvalue(),image.type,gemini_key)
                st.session_state.vision_result=result
                st.session_state.vision_name=image.name
                st.session_state.vision_digest=current_image_digest
            except Exception as exc:
                st.error(str(exc))
        if ("vision_result" in st.session_state
            and st.session_state.get("vision_digest")==current_image_digest):
            st.markdown("### AUSWERTUNG / EXTERNES KI-MODELL")
            show_result(st.session_state.vision_result,is_vision=True)
    else:
        st.info("Lade ein Chartbild hoch. Ohne API-Zugang bleibt die kostenlose Bildvorschau verfügbar.")
    st.markdown("#### 02 — Wie wir falsche Signale vermeiden")
    st.write("Die Bild-KI muss Markt, Zeitraum, Preisachse und jüngste Kerzen sicher lesen. Stimmen Entry-Zone, Stop und zwei Ziele nicht zusammen, zeigt ChartPilot NO TRADE. Die kostenlosen OHLC-Daten prüfen drei Strategien separat.")
    st.caption("Optionaler KI-Anbieter, keine Verbindung zum Broker. Vertrauliche Screenshots nur hochladen, wenn du der externen Verarbeitung zustimmst.")

elif page.startswith("04"):
    st.subheader("STRATEGY LAB  /  WALK-FORWARD CHECK")
    st.warning("Ein kurzer Backtest beweist keinen Trading-Vorteil. Historische Resultate sind keine Echtzeit-Prognose.")
    if not ds:
        st.info("Bitte erst Kursdaten im COCKPIT oder DATA HUB laden.")
    else:
        st.markdown("Aktiver Datensatz: **"+ds["source"]+" / "+ds["symbol"]+"**")
        c1,c2=st.columns(2)
        with c1:
            cost=st.number_input("Kosten für Ein- und Ausstieg zusammen (in Preis-/Punkteeinheiten)",min_value=0.,value=0.,step=.05,format="%.3f")
        with c2:
            max_candles=st.slider("Anzahl getesteter Kerzen",min_value=90,max_value=min(600,max(90,len(ds["df"]))),value=min(320,max(90,len(ds["df"]))),step=10)
        if st.button("Backtest ohne Lookahead ausführen",type="primary"):
            try:
                stats,trades=run_backtest(ds["df"],ds["symbol"],style,ds["interval"],cost,max_candles)
                st.session_state.bt_stats=stats;st.session_state.bt_trades=trades
            except Exception as exc:
                st.error(str(exc))
        if "bt_stats" in st.session_state:
            s=st.session_state.bt_stats
            cols=st.columns(4)
            cols[0].metric("Abgeschlossene Trades",s["trades"])
            cols[1].metric("Trefferquote",f"{s['win_rate']} %" if s["win_rate"] is not None else "—")
            cols[2].metric("Summe R",f"{s['total_r']} R")
            cols[3].metric("Max. Drawdown",f"{s['max_drawdown_r']} R")
            st.caption("R = Risiko pro Trade; modellhafte Fill-Annahmen, ohne garantierte Ausführung. Trefferquote allein bewertet keine Profitabilität.")
            tr=st.session_state.bt_trades
            if not tr.empty:
                st.dataframe(tr,hide_index=True,use_container_width=True)
                st.download_button("Backtest-Ergebnisse exportieren",data=tr.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="chartpilot_backtest.csv")
            else:
                st.info("Für diesen Datensatz wurden keine gültigen regelbasierten Setups gefunden.")
        st.markdown("**Testregeln:** Signal nach abgeschlossener Kerze, hypothetischer Einstieg am nächsten Open, pessimistische Stop-Ausführung falls Stop und Ziel in derselben Kerze erreicht werden, keine überlappenden Trades. Kein Walk-forward-Training und keine Broker-Simulation.")

elif page.startswith("05"):
    st.subheader("RISK DESK / POSITION PLAN")
    st.caption("Rechenhilfe für Paper-Trading. Diese Werte bestimmen **keine echte Kontraktgröße**.")
    l,r=st.columns(2)
    with l:
        account=st.number_input("Virtuelles Kontokapital",min_value=0.,value=1000.,step=100.)
        percentage=st.slider("Risiko je hypothetischem Trade (%)",min_value=.1,max_value=2.,value=.5,step=.1)
    with r:
        distance=st.number_input("Stop-Abstand (Preis-/Punkteeinheiten)",min_value=.00001,value=5.,step=.5,format="%.4f")
        point=st.number_input("Wert je Preiseinheit einer hypothetischen Einheit",min_value=.00001,value=1.,step=.5,format="%.4f")
    allowed=account*percentage/100
    units=allowed/(distance*point)
    m1,m2,m3=st.columns(3)
    m1.metric("Virtuelles Risikobudget",f"{allowed:.2f}")
    m2.metric("Hypothetische Einheiten",f"{units:.3f}")
    m3.metric("Kapitalrisiko in %",f"{percentage:.1f}%")
    st.warning("Wichtig: Gold-Futures, CFDs und ETFs haben **verschiedene** Kontraktgrößen, Margin-Anforderungen, Tick-Werte und Gebühren. Der angenommene Punktwert hier ist **nur ein Beispiel**. Nicht ungeprüft für Echtgeld-Orders verwenden.")
    if ds and ds["result"]["signal"]!="NO TRADE":
        a=ds["result"]
        st.markdown("**Aktuelle historische Setup-Idee:** "+
                    f"{a['signal']} | Entry {a['proposed_entry']:.3f} | Stop {a['stop_loss']:.3f} | Ziel {a['take_profit']:.3f}")

elif page.startswith("06"):
    st.subheader("JOURNAL / SESSION LOG")
    st.caption("Einträge bleiben ausschließlich während deiner Streamlit-Sitzung gespeichert; kein Account, keine Datenbank, keine Trades.")
    if ds:
        st.markdown("Aktuelle Beobachtung: **"+ds["symbol"]+" / "+ds["result"]["signal"]+"**")
        if st.button("Aktuelle Analyse zum Journal hinzufügen"):
            save_journal(ds);st.success("Gespeichert – nur temporär in dieser Sitzung.")
    entries=st.session_state.get("journal",[])
    if entries:
        table=pd.DataFrame(entries)
        st.dataframe(table,hide_index=True,use_container_width=True)
        st.download_button("Journal als CSV sichern",table.to_csv(index=False).encode("utf-8-sig"),
                           file_name="chartpilot_journal.csv",mime="text/csv")
        if st.button("Sitzungs-Journal leeren"):
            st.session_state.journal=[];st.rerun()
    else:
        st.info("Noch keine Beobachtungen. Lade Kurse im COCKPIT und speichere eine Analyse.")

else:
    st.subheader("SOURCE CENTER / TRANSPARENZ")
    st.markdown("#### QUELLEN & KOMPATIBILITÄT")
    sources=pd.DataFrame([
        {"Quelle":"Yahoo Finance (via yfinance)","Instrumente":"Futures GC=F / ES=F / NQ=F, Indizes ^GSPC / ^NDX, ETFs GLD / SPY / QQQ","Einsatz":"Historische Daten; verzögert/möglicherweise nicht erreichbar","API-Key":"Nein"},
        {"Quelle":"TradingView CSV-Export","Instrumente":"Was im Quellchart tatsächlich geladen wurde","Einsatz":"Manueller Import mit sichtbarem Datei-/Zeitstempel","API-Key":"Nein"},
        {"Quelle":"Synthetische Demo","Instrumente":"Keine","Einsatz":"Oberflächentest und Programm-Checks","API-Key":"Nein"},
        {"Quelle":"Google Gemini (optional)","Instrumente":"Screenshots, nicht OHLC-Live-Feed","Einsatz":"Bildverständnis per ausdrücklichem Opt-in","API-Key":"Ja – eigener"},
    ])
    st.dataframe(sources,hide_index=True,use_container_width=True)
    st.markdown("#### ANALYSE-ENGINE")
    st.write("EMA20/EMA50, ATR14, strukturierter 20-Kerzen-Ausbruch; keine rückwirkenden Vorwärtsdaten für historische Backtests. V2 führt einen separaten Datenqualitäts-Check und einen optionalen Bild-KI-Test ein.")
    st.markdown("#### BEKANNTE GRENZEN")
    bullets([
        "Weder Yahoo-Daten noch Chart-Screenshots garantieren Echtzeit. Es gibt keine automatische Orderausführung.",
        "S&P-500- und NASDAQ-100-Indizes sind keine direkt handelbaren Produkte; Future-/ETF-Preise weichen ab.",
        "Keine automatische Broker-/TradingView-API-Verbindung und kein KI-Modelltraining aus Nutzerdaten.",
        "Kostenfreie Datenfeeds und KI-Kontingente können sich ändern oder ausfallen.",
        "Screenshot-Uploads und CSV-Dateien werden in Streamlit Community Cloud auf dem Server verarbeitet.",
        "TradingView- und andere Fremddaten unterliegen den Nutzungs-/Lizenzbedingungen des jeweiligen Anbieters.",
    ])
    st.markdown("#### SOURCE LINKS")
    st.markdown("[TradingView Chartdaten exportieren](https://de.tradingview.com/support/solutions/43000537255/) · [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) · [Gemini Free-Tier-Preise](https://ai.google.dev/gemini-api/docs/pricing)")

st.markdown('<div class="cp-footer">CHARTPILOT V2 · BLACK / PURPLE · PRIVATE RESEARCH TERMINAL · ANALYSE ≠ GEWINNGARANTIE · KEINE ECHTGELD-ORDERS</div>',
            unsafe_allow_html=True)
