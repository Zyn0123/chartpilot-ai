# ChartPilot AI V1.2 — kostenloses Streamlit-Dashboard

Eigenständiges Projekt, unabhängig von ZYN0 Momentum Studio.

## Veröffentlichung auf Streamlit Community Cloud

1. https://share.streamlit.io/ aufrufen und mit GitHub anmelden.
2. **Create app** → **Deploy a public app from GitHub**.
3. Repository: `Zyn0123/chartpilot-ai`; Branch: `main`; Main file path: `app.py`.
4. App-Adresse festlegen und **Deploy** klicken. Für die aktuelle Version ist kein API-Key erforderlich.

## Funktionen

- Chart-Dashboard im Browser ohne lokalen Python-Start.
- Regelbasierte CSV-Analyse von Open, High, Low, Close (optional Time/Volume).
- EMA20, EMA50, ATR14, vorangegangene 20-Kerzen-Hochs/Tiefs; hypothetische LONG/SHORT/NO-TRADE-Bewertung.
- Screenshot-Upload nur zur **Bildvorschau**; noch **keine** KI-Screenshot-Auswertung.
- Simulierte Übungsdaten (keine echten Goldkurse) inklusive Download.
- Ergebnis mit Erklärungen, Einstiegs-Idee/SL/TP nur bei validem Regelsignal und CSV-Export.
- Kein API-Key, keine laufende API-Abrechnung, keine Brokerverbindung oder Echtgeld-Orders.

## Grenzen

Die Cloud-App verarbeitet hochgeladene Dateien auf Streamlit-Servern. Lade keine Zugangsdaten hoch.
Das öffentliche Repository enthält ausschließlich Code und synthetische Demonstrationsdaten.
Die Auswahl von Symbol und Zeitrahmen wird nicht anhand der CSV verifiziert.
Das System ist kein Live-Marktdatenfeed und die Strategie wurde nicht auf ihre Profitabilität geprüft.
Zuerst nur mit simulierten Daten bzw. Paper-Trading testen.

## Lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tests: `python -m unittest discover -s tests -v`
