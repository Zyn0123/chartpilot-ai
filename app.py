"""ChartPilot AI V1.3: kostenfreier Offline-Modus; keine API-Abhaengigkeit, keine Orders."""
from __future__ import annotations

import csv
import io
from pathlib import Path

import streamlit as st
import altair as alt

from offline import analyze_ohlc, load_ohlc
from market_data import MARKETS, PERIODS, age_notice, fetch_history

ROOT = Path(__file__).resolve().parent
DEMO_CSV = ROOT / 'sample' / 'demo_simuliert_5m.csv'

st.set_page_config(page_title='ChartPilot · kostenlos V1.3', page_icon='📈', layout='wide')
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


@st.cache_data(ttl=300, show_spinner=False, max_entries=20)
def cached_market_history(ticker: str, interval: str):
    return fetch_history(ticker, interval)


def price_chart(history):
    """Zeige kleine Kursbewegungen ohne erzwungenen Nullpunkt."""
    frame = history[['close', 'EMA20', 'EMA50']].tail(150).reset_index(drop=True)
    frame['kerze'] = range(len(frame))
    long_frame = frame.melt(id_vars='kerze', var_name='Linie', value_name='Preis')
    price_plot = (
        alt.Chart(long_frame)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X('kerze:Q', title='Kerze (Reihenfolge)'),
            y=alt.Y('Preis:Q', title='Preis / Punkte', scale=alt.Scale(zero=False)),
            color=alt.Color('Linie:N', title=''),
            tooltip=[
                alt.Tooltip('kerze:Q', title='Kerze'),
                alt.Tooltip('Linie:N'),
                alt.Tooltip('Preis:Q', format='.3f')
            ],
        )
        .properties(height=360)
        .interactive()
    )
    st.altair_chart(price_plot, use_container_width=True)


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

st.caption('CHARTPILOT / V1.3 · HISTORISCHE MARKTDATEN')
st.title('Dein Chart. Klare Bedingungen. Keine API-Kosten.')
st.write('Bilder hier ansehen – oder OHLC-Kursdaten mit transparenten Regeln auswerten, ohne API-Kosten.')

tab_market, tab_csv, tab_img = st.tabs(['🌍 Historische Marktdaten', '📊 Eigene CSV-Analyse', '📸 Screenshot ansehen'])

with tab_market:
    st.subheader('Echte historische Marktkerzen – ohne API-Key')
    st.info('Quelle: Yahoo Finance über yfinance. **Kein garantierter Echtzeitfeed**; Kurse können verzögert, lückenhaft oder vorübergehend nicht abrufbar sein. Für Lernen und Paper-Trading.')
    st.warning('**Wichtig:** Gold-Futures (GC=F) unterscheiden sich von XAU/USD Spot auf TradingView. Indizes wie ^GSPC und ^NDX sind nicht direkt handelbar. Keine Echtgeld-Signale!')
    m1, m2 = st.columns([2, 1])
    with m1:
        selected_market = st.selectbox('Historischer Markt', options=list(MARKETS), index=0, key='selected_market')
    with m2:
        selected_interval = st.selectbox('Kerzen-Zeitrahmen', options=list(PERIODS), index=2, key='selected_interval')
    st.caption('Abrufzeitraum: ' + PERIODS[selected_interval] + ' | Datenquelle kann zeitlich verzögert sein und ist nicht identisch mit deinem Brokerchart.')
    if st.button('📈 Historische Kerzen laden und analysieren', type='primary', use_container_width=True):
        with st.spinner('Historische Marktdaten werden abgerufen...'):
            try:
                data = cached_market_history(MARKETS[selected_market], selected_interval)
                a, enriched, _ = analyze_ohlc(data, selected_market, style, selected_interval)
                st.session_state['market_result'] = a
                st.session_state['market_history'] = enriched
                st.session_state['market_label'] = selected_market
                st.session_state['market_interval'] = selected_interval
                st.session_state['market_age'] = age_notice(data)
            except Exception as exc:
                st.error(str(exc))
                st.info('Wenn Yahoo Finance gerade nicht erreichbar ist, kannst du im zweiten Tab eine OHLC-CSV hochladen.')
    if 'market_result' in st.session_state:
        st.divider()
        st.markdown('**Datensatz:** ' + st.session_state['market_label'] + ' · ' + st.session_state['market_interval'])
        st.warning(st.session_state['market_age'])
        price_chart(st.session_state['market_history'])
        show_analysis(st.session_state['market_result'], 'Regelbasierte Analyse historischer Yahoo-Kerzen – keine KI, kein Echtzeit-Signal, kein Broker-Feed')

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
        price_chart(history)
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
st.caption('V1.3: Historische Yahoo-Daten (nicht Echtzeit), kein API-Key, kein Brokerhandel, kein geprüfter Handelsalgorithmus. Auf Streamlit Community Cloud werden Uploads vom Cloud-Server verarbeitet, nicht ausschließlich auf deinem PC. Keine dauerhafte Speicherung im Projektcode vorgesehen. Nur Lernen und Paper-Trading.')
