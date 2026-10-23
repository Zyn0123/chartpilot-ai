"""ChartPilot AI V1.2: kostenfreier Offline-Modus; keine API-Abhaengigkeit, keine Orders."""
from __future__ import annotations

import csv
import io
from pathlib import Path

import streamlit as st

from offline import analyze_ohlc, load_ohlc

ROOT = Path(__file__).resolve().parent
DEMO_CSV = ROOT / 'sample' / 'demo_simuliert_5m.csv'

st.set_page_config(page_title='ChartPilot · kostenlos V1.2', page_icon='📈', layout='wide')
st.markdown("""<style>
.stApp { background:#0a101b; color:#e4ecf8; }
div[data-testid="stMetric"] { background:#111d30; border:1px solid #26374f; padding:12px; border-radius:12px; }
h1,h2,h3 {letter-spacing:-0.025em;}
.block-container {padding-top:2.1rem;}
.caption {color:#94a7bf;}
</style>""", unsafe_allow_html=True)


def bullets(items):
    for item in items:
        st.markdown(f'- {item}')


def show_analysis(a: dict, provenance: str):
    sign = a['signal']
    st.subheader({'NO TRADE': '🟡', 'LONG': '🟢', 'SHORT': '🔴'}.get(sign, '⚪') + ' ' + sign)
    st.caption(provenance)
    st.write(a['summary'])
    cols = st.columns(3)
    cols[0].metric('Trend', a['trend'].capitalize())
    cols[1].metric('Marktlage', a['market_regime'])
    cols[2].metric('Datenqualität', a['data_quality'].capitalize())
    st.caption('Datenqualität ist keine Gewinnwahrscheinlichkeit.')
    with st.expander('Erkannte Merkmale & Niveaus', expanded=True):
        bullets(a['observations'])
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('**Unterstützungen**')
            bullets(a['supports'])
        with c2:
            st.markdown('**Widerstände**')
            bullets(a['resistances'])
    with st.expander('Bedingungen für mögliche Setups'):
        st.markdown('**LONG:** ' + a['long_condition'])
        st.markdown('**SHORT:** ' + a['short_condition'])
        st.markdown('**Ungültig, wenn:** ' + a['invalidation'])
    if sign in ('LONG', 'SHORT'):
        st.warning('Nur hypothetisches **Regelsignal**, kein geprüfter Tradingvorteil. Keine Orderausführung.')
        a1, a2, a3, a4 = st.columns(4)
        a1.metric('Schlusskurs / Idee', f"{a['proposed_entry']:.3f}")
        a2.metric('Hypothetischer SL', f"{a['stop_loss']:.3f}")
        a3.metric('Hypothetischer TP', f"{a['take_profit']:.3f}")
        a4.metric('CRV ohne Kosten', f"1:{a['risk_reward']:.2f}")
    else:
        st.info('NO TRADE: Die festgelegten technischen Bedingungen sind nicht erfüllt.')
    with st.expander('Risiken / Grenzen', expanded=True):
        bullets(a['risk_flags'])
    st.caption(f"Quelle: {a['detected_symbol']} | Zeitrahmen: {a['detected_timeframe']} | letzter Zeitpunkt: {a['screenshot_time']}")


with st.sidebar:
    st.header('⚙️ Einstellungen')
    st.success('Kostenloser Regelmodus · **kein API-Key erforderlich**')
    st.info('Kein Echtgeldhandel, keine Brokerverbindung, keine automatischen Orders.')
    market = st.selectbox('Markt (manuelle Angabe)', ['Gold / XAUUSD', 'S&P 500', 'NASDAQ 100', 'EUR/USD', 'Anderer'])
    if market == 'Anderer':
        market = st.text_input('Symbol', value='Anderer Markt').strip() or 'Anderer Markt'
    style = st.radio('Trading-Stil', ['Scalping', 'Daytrading', 'Swingtrading'], index=0)
    timeframe = st.selectbox('Zeitrahmen (manuelle Angabe)', ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1D'], index=2)
    st.caption('Wichtig: Auswahl von Markt und Zeitraum ersetzt keine Verifikation der hochgeladenen Daten.')

st.caption('CHARTPILOT / V1.2 · KOSTENLOSER MODUS')
st.title('Dein Chart. Klare Bedingungen. Keine API-Kosten.')
st.write('Bilder hier ansehen – oder OHLC-Kursdaten mit transparenten Regeln auswerten, ohne API-Kosten.')

tab_csv, tab_img = st.tabs(['📊 Kostenlose Kursdaten-Analyse', '📸 Screenshot ansehen'])

with tab_csv:
    st.write('**CSV-Datei mit mindestens 60 Kerzen hochladen.** Die Auswertung läuft im Streamlit-Prozess: lokal auf deinem PC oder bei Veröffentlichung auf dem Cloud-Server.')
    st.caption('Benötigte Spalten: Open, High, Low, Close. Optional: Time/Date und Volume. Komma- und Semikolon-CSV möglich.')
    up_csv = st.file_uploader('OHLC-Kursdaten als CSV', type=['csv'], key='ohlc_csv')
    use_demo = st.checkbox('Simulierte Übungsdaten verwenden (keine echten Goldkurse)', value=up_csv is None)
    file_bytes = up_csv.getvalue() if up_csv is not None else (DEMO_CSV.read_bytes() if use_demo and DEMO_CSV.exists() else None)
    if use_demo and up_csv is None:
        st.warning('**DEMO:** Künstliche Kerzen zum Testen der Software, KEINE realen Marktkurse.')
        st.download_button('Demo-CSV ansehen/herunterladen', data=DEMO_CSV.read_bytes(), file_name='chartpilot_demo_simuliert.csv', mime='text/csv')
    if st.button('🔎 Kursdaten kostenlos analysieren', disabled=file_bytes is None, type='primary', use_container_width=True):
        try:
            prices = load_ohlc(file_bytes)
            analysis, enriched, meta = analyze_ohlc(prices, market, style, timeframe)
        except Exception as exc:
            st.error(f'Kursdaten konnten nicht analysiert werden: {exc}')
        else:
            st.session_state['csv_result'] = analysis
            st.session_state['csv_history'] = enriched
            st.session_state['csv_meta'] = meta
            st.session_state['csv_demo'] = up_csv is None
            st.session_state['csv_file'] = up_csv.name if up_csv else 'DEMO simuliert'
    if 'csv_result' in st.session_state:
        st.divider()
        if st.session_state['csv_demo']:
            st.warning('Simulationsergebnis – nicht für echte Handelsentscheidungen verwenden.')
        st.markdown(f"**Ausgewertete Datei:** {st.session_state['csv_file']}")
        history = st.session_state['csv_history']
        st.line_chart(history[['close', 'EMA20', 'EMA50']].tail(150), x_label='Kerze (Reihenfolge)', y_label='Preis / Punkte')
        show_analysis(st.session_state['csv_result'], 'Automatische Offline-Regeln auf OHLC-Kursdaten – keine Bild-KI, kein Live-Signal')
        a = st.session_state['csv_result']
        export = {k: a[k] for k in ('signal','trend','summary','proposed_entry','stop_loss','take_profit','risk_reward','screenshot_time')}
        text = io.StringIO()
        csvwriter = csv.DictWriter(text, fieldnames=list(export))
        csvwriter.writeheader(); csvwriter.writerow(export)
        st.download_button('📥 Analyse als CSV exportieren', data=text.getvalue().encode('utf-8-sig'), file_name='chartpilot_offline_analyse.csv', mime='text/csv')

with tab_img:
    uploaded = st.file_uploader('TradingView-Bild hochladen', type=['png','jpg','jpeg','webp'], key='image')
    if uploaded is not None:
        st.image(uploaded, caption='Bildvorschau – noch keine automatische Bildanalyse', use_container_width=True)
        st.warning('Der Screenshot wird in dieser kostenlosen Version **nicht automatisch analysiert**. ChartPilot liest keine Preise aus dem Bild aus.')
        st.info('Für die visuelle Einschätzung kannst du mir den Screenshot im Chat schicken. Berechnete Regeln benötigen eine OHLC-CSV.')
    else:
        st.info('Hier kannst du deinen eigenen TradingView-Screenshot hochladen. Die V1.2 zeigt ihn nur an; sie erzeugt daraus keine Signale.')

st.divider()
st.caption('V1.2: Kein API-Key, kein Live-Feed, kein geprüfter Handelsalgorithmus. Auf Streamlit Community Cloud werden Uploads vom Cloud-Server verarbeitet, nicht ausschließlich auf deinem PC. Keine dauerhafte Speicherung im Projektcode vorgesehen. Nur Lernen und Paper-Trading.')
