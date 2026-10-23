"""ChartPilot V2 · independent black/purple market research workstation.

Trading education and paper trading only. No automatic or real-money order routing.
"""
from __future__ import annotations

import io
import csv
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from backtest import run_backtest
from market_data import MARKETS, PERIODS, fetch_history
from offline import analyze_ohlc, load_ohlc
from quality import inspect_candles
from theme import apply_theme, label
from vision import analyze_screenshot, MODEL

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "sample" / "demo_simuliert_5m.csv"
MENU = ["01  COCKPIT", "02  DATA HUB", "03  VISION AI", "04  STRATEGY LAB", "05  RISK DESK", "06  JOURNAL", "07  SOURCES"]

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
    result, enriched, _ = analyze_ohlc(df,symbol,style,interval)
    st.session_state.dataset = {
        "df":df, "enriched":enriched,"result":result,
        "source":source, "symbol":symbol, "interval":interval, "is_demo":is_demo,
    }

def active():
    return st.session_state.get("dataset")

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
    st.markdown('<div class="cp-brand">◆ CHART<b>PILOT</b></div><div class="cp-kicker">INDEPENDENT MARKET TERMINAL</div>',
                unsafe_allow_html=True)
    st.markdown("---")
    page=st.radio("WORKSPACE",MENU,key="nav")
    st.markdown("---")
    st.markdown('<div class="cp-kicker">MARKET CONTEXT</div>',unsafe_allow_html=True)
    symbol_label=st.selectbox("Instrument",list(MARKETS),index=0,key="symbol")
    interval=st.selectbox("Kursintervall",list(PERIODS),index=2,key="interval")
    style=st.selectbox("Trading-Stil",["Scalping","Daytrading","Swingtrading"],index=0,key="style")
    st.success("KOSTENLOSER REGELMODUS AKTIV")
    st.caption("Echte Marktdaten können verzögert sein. Kein Broker, keine Orders, kein automatisches Echtgeld-Trading.")
    st.markdown('<div class="cp-pill">V2.0 / BUILD</div> <div class="cp-pill">PURPLE/BLACK</div>',unsafe_allow_html=True)

label(st,"CHARTPILOT / SYSTEM V2","MARKET CONTROL TERMINAL","Eigenständige Analyseplattform · Flaches Schwarz-Lila-Design · Keine Echtgeld-Orderfunktion")
st.markdown('<div class="cp-rule"></div>',unsafe_allow_html=True)

ds=active()

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
                result,_,_=analyze_ohlc(df,symbol_label,style,tf)
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
    st.markdown('<div class="cp-strip"><b>FREE BY DEFAULT</b> · Du brauchst keine API für den DATA HUB. Bild-KI ist eine freiwillige Zusatzfunktion.</div>',
                unsafe_allow_html=True)
    image=st.file_uploader("TradingView-Chart als PNG / JPG / WEBP hochladen",type=["png","jpg","jpeg","webp"],key="vision_image")
    if image:
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
            except Exception as exc:
                st.error(str(exc))
        if "vision_result" in st.session_state and st.session_state.get("vision_name")==image.name:
            st.markdown("### AUSWERTUNG / EXTERNES KI-MODELL")
            show_result(st.session_state.vision_result,is_vision=True)
    else:
        st.info("Lade ein Chartbild hoch. Ohne API-Zugang bleibt die kostenlose Bildvorschau verfügbar.")
    st.markdown("#### 02 — Wie wir falsche Signale vermeiden")
    st.write("Die Bild-KI muss Unsicherheit offen nennen und darf bei unlesbaren Preisachsen oder unbekanntem Zeitrahmen keine Einstiegspreise erfinden. Der Regelmodus arbeitet unabhängig davon ausschließlich mit OHLC-Kerzen.")
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
