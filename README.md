# ChartPilot V1.3 – kostenlose historische Kursdaten

Eigenstaendiges Streamlit-Dashboard, getrennt von ZYN0 Momentum Studio.

## Bereitstellung auf Streamlit Community Cloud

Repository: `Zyn0123/chartpilot-ai` · Branch: `main` · Startdatei: `app.py`

Aenderungen am main-Branch sollten automatisch ein neues Deployment ausloesen.
Falls die App nicht aktualisiert wird: Streamlit-App neu starten und Logs pruefen.

## Neu in V1.3

- **Historische Marktdaten**: kostenlose Yahoo-Finance-Abfrage ueber `yfinance` (kein API-Key).
- Verfuegbare Quellen: Gold-Future GC=F, S&P 500 Index ^GSPC, NASDAQ 100 Index ^NDX, E-Mini-Futures ES=F und NQ=F.
- Zeitrahmen: 1m, 2m, 5m, 15m, 30m, 1h und 1d; je nach Intervall ein begrenzter historischer Zeitraum.
- Daten werden maximal 5 Minuten zwischengespeichert, **nicht** automatisch sekundenaktuell aktualisiert.
- Kerzenzeitstempel und Hinweis auf die letzte verfuegbare Kerze.
- Bereits vorhandene CSV-Analyse, synthetische Demo und Screenshot-Vorschau bleiben erhalten.
- EMA20/EMA50/ATR14 und rein regelbasierte LONG/SHORT/NO-TRADE-Uebungssignale.

## Wichtige Einschraenkungen

Yahoo Finance ist **kein garantierter Live-Datenfeed**, es kann Kursverzoegerungen, Sperren oder Abruffehler geben. Private Nutzung und geltende Daten-/Nutzungsbedingungen beachten.
`GC=F` bezeichnet einen Gold-Future und ist **nicht** das TradingView-Symbol XAUUSD Spot.
`^GSPC` und `^NDX` sind Indizes, keine handelbaren Brokerinstrumente.
Abfragehistorien koennen durch Yahoo begrenzt sein (z. B. 1m ca. 7 Tage, andere intraday Intervalle max. 60 Tage). Technische Regeln sind nicht backgetestet.
Die App ist **keine** KI-Screenshotanalyse, hat **keine** Brokeranbindung und fuehrt **keine** Echtgeldorders aus.
CSV und Screenshot-Uploads bei Cloud-Betrieb werden auf Streamlit-Servern verarbeitet. Keine Kontodaten oder API-Schluessel hochladen.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tests lokal: `python -m unittest discover -s tests -v`.
