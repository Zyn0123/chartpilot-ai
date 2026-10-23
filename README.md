# ◆ ChartPilot — Terminal V2.2 · Setup Radar + Trade-Zonen

**Eigenständiges Trading-Research-Tool** mit flachem Schwarz-Lila-Design, geschrieben in Python und gehostet über **Streamlit Community Cloud**. Komplett unabhängig vom ZYN0 Momentum Studio.

## Deploy

- Repository: `Zyn0123/chartpilot-ai`
- Branch: `main`
- Startdatei: `app.py`
- Python 3.11+; `pip install -r requirements.txt && streamlit run app.py`

Für Streamlit Cloud genügt die bestehende GitHub-Anbindung: Updates auf `main` werden automatisch deployed. Nach einem Update ggf. die Streamlit-App neu starten, falls ein Fehler oder eine alte Version angezeigt wird.

## Workspace

| Seite | Funktionen | Datenquelle |
|---|---|---|
| 01 Cockpit | historische OHLC-Kerzen, 3 getrennte Strategien (Breakout, Trend-Pullback, Range), hypothetische Entry-Zone, SL und TP1/TP2, optional 5m/15m/1h-Vergleich | Yahoo Finance (yfinance) |
| 02 Data Hub | TradingView-CSV importieren, Time in Sekunden/Millisekunden/ISO, OHLC validieren, synthetischer Testdatensatz, CSV exportieren | Benutzer-CSV, Demo |
| 03 Vision AI | Screenshot mit passender OHLC-CSV kostenlos auswerten (Kurse nur aus CSV); alternativ **optionale** Gemini-Bild-KI mit Preiszonen nach Einwilligung | CSV ohne Key / Gemini mit eigenem Key |
| 04 Strategy Lab | historischer Mini-Backtest über die drei Setup-Typen, modellhafte Kosten, nächste Open als Entry, bei Doppelberührung Stop zuerst, Trades exportieren | aktiver OHLC-Datensatz |
| 05 Risk Desk | rein hypothetische Einheiten/virtuelles Risikobudget, ohne echte Brokerkontrakte | Nutzerwerte |
| 06 Journal | Sitzungs-Log, CSV-Export; keine persistierte Datenbank | Streamlit session_state |
| 07 Sources | Quellen, Annahmen, Einschränkungen, Links | Dokumentation |

## Neu: Drei Setup-Typen und Preiszonen

- **Breakout:** EMA20/EMA50-Trend und 2 bestätigte Schlusskurse jenseits der älteren Spanne.
- **Trend-Pullback:** Rücksetzer zu EMA20 mit bestätigtem Reclaim in Trendrichtung; RSI gegen extreme Überdehnung.
- **Range:** Seitwärtsfilter (nahe EMAs), definierter historischer 25-Kerzen-Korridor und Umkehr am Rand.
- **Zwei Zustände:** BESTÄTIGT (historische Kriterien) oder BEOBACHTEN. Ohne gültige Bedingungen bleibt NO TRADE.
- Bei einem historisch bestätigten, logisch konsistenten Szenario: **Entry-Korridor, Stop-Loss, TP1 und TP2** und hypothetisches Chance/Risiko, ohne Handelskosten und Slippage.
- Bei widersprüchlichen Long-/Short-Kandidaten: NO TRADE; keine automatische Echtgeldorder.
- Für Screenshot-KI: Preisachse und letzte Kerzen müssen lesbar sein; Felder und Preisreihenfolge werden lokal geprüft. **Die App kann die im Bild geschätzten Preise nicht gegen einen Live-Feed verifizieren.**

### Komplett kostenloser Weg ohne API-Key

1. Screenshot im Bereich **VISION AI** hochladen.
2. Auf TradingView im selben Markt und Zeitrahmen eine OHLC-CSV exportieren.
3. **Kostenlose Kurszonen aus passender CSV berechnen** öffnen, CSV hochladen, Symbol manuell prüfen.
4. **Kostenlosen Drei-Strategien-Check** starten.
5. Entry-Zone, SL, TP1/TP2 sind Berechnungen **aus CSV-Daten**, niemals aus den Bildpixeln. Ohne passende CSV und ohne API-Key funktioniert die automatische Screenshot-Bildinterpretation noch nicht.

### Optionale Bild-KI

Erst nach eigener, ausdrücklicher Freigabe wird ein Bild mit einem eigenen Gemini-API-Key an Google übermittelt. Dann verlangt die Ausgabe zusätzlich Setup-Typ (Breakout/Pullback/Range), Entry-Zone, Stop-Loss, TP1/TP2 und eine Bestätigungsbedingung. Wenn Preisachse, Kerzen, Richtung oder Preisreihenfolge unklar sind, wird NO TRADE erzwungen. **Visuell geschätzte Level sind nicht brokerverifiziert und kein Ausführungsauftrag.** Kostenfreie Kontingente hängen vom Anbieter-Tarif und der Verfügbarkeit ab.

## Historische Märkte (Yahoo Finance)

- **GC=F**: Gold-Future, **NICHT** XAUUSD Spot
- **^GSPC**: S&P 500 Index, **kein** direkt handelbares Produkt
- **^NDX**: NASDAQ 100 Index, **kein** direkt handelbares Produkt
- **ES=F** und **NQ=F**: E-mini-Futures
- **GLD**, **SPY**, **QQQ**: ETFs (nicht die zugrunde liegenden Spot-/Index-Kurse)

Intervallwahl: 1m/2m/5m/15m/30m/1h/1d, jeweils begrenzte abrufbare Historie. Aktualisierung manuell per Button, mit fünfminütigem Cache. **Keine Echtzeitgarantie.** Öffentliche Yahoo-Daten können verzögert, lückenhaft, eingeschränkt oder zeitweise nicht verfügbar sein. Nutzung/Lizenzbestimmungen beachten; für automatische Echtgeld-Orders wären lizenzierte Broker-Datenfeeds, zuverlässige Ausführung und deutlich mehr Tests erforderlich.

## TradingView als präzisere Quelle bereitstellen

1. In TradingView **genau den Chart und das Symbol** öffnen, das später untersucht werden soll (z. B. OANDA:XAUUSD 5m). 
2. Möglichst viele zusammenhängende Kerzen im Chart laden.
3. Chartmenü → **Chartdaten exportieren** (falls im Account verfügbar).
4. Im **DATA HUB** die CSV-Datei laden und manuell das genaue Symbol angeben.
5. Zeitrahmen links auf den tatsächlichen Kerzenzeitraum einstellen; die App kann diesen nicht automatisch gegen das Original verifizieren.

Akzeptierte Spalten: `Time`/`Date`, `Open`, `High`, `Low`, `Close`; `Volume` optional. Bis zu 10 MB, mindestens 60 Kerzen. Zeitzonen bitte kontrollieren. Die App ersetzt keine Lizenz zur Weitergabe fremder Kursdaten.

## Vision AI / Opt-in

Die App ist **ohne API-Key voll im Regelmodus nutzbar**. Echte automatische Screenshot-Bildanalyse läuft nur nach:
- Bild-Upload (max. 5 MB, PNG/JPG/WEBP).
- Eingabe eines eigenen **Gemini API-Keys** in ein Passwortfeld.
- Aktivierung der Einwilligung, das Bild an Gemini zu senden.
- Explizitem Klick auf **Screenshot mit Vision AI prüfen**.

Modell: `gemini-2.5-flash`. Die Google Gemini-API bietet je nach Konto/Region/Modell begrenzte Free-Tier-Nutzung; **Kostenfreiheit ist keine Garantie**, und bei Nutzung eines kostenpflichtigen Kontos können Gebühren entstehen. Im kostenlosen Tarif können eingereichte Inhalte zur Produktverbesserung verwendet werden. Keine personenbezogenen Daten, Trading-Account-Daten oder Geheimnisse im Screenshot zeigen. **API-Key niemals in GitHub oder in Chat-Nachrichten posten.** Der Key wird nicht dauerhaft im Repository gespeichert.

Die KI kann Preise, Zeitrahmen oder Kerzen fehlinterpretieren. Deshalb erzwingt die Software bei unklarem Symbol/Zeitrahmen bzw. widersprüchlichen Entry/SL/TP-Werten `NO TRADE`. Für konkrete Handelsentscheidungen OHLC-Daten und Brokerkurse unabhängig prüfen. Keine automatische Orderausführung.

## Modell- und Risiko-Grenzen

- **Kein geprüfter profitabler Algorithmus**: Test-Signale sind hypothesenbasierte Beispiele.
- **Keine Echtgeldorder**: kein Broker, kein Copy-Trading, kein Auto-Trading.
- **Backtest ist vereinfacht**: keine perfekte Tickabfolge, Ausführung am Stop bei SL/TP gleichzeitig, Preis-/Punktekosten sind nur manuell angenähert, keine Markttiefe/Margin/Echtzeit.
- **Aktualität wird ausgewiesen**: Letzte Kerze und Datenalter sind Pflichtangaben.
- **Session-Journal** bleibt nur bis zum Sitzungsende. Sichere es per CSV.
- In Streamlit Community Cloud verarbeiten Streamlit-Server deine Uploads. Keine privaten Schlüssel oder Kontoauszüge hochladen.
- Echtgeldhandel mit Hebel kann zu schnellen und erheblichen Verlusten führen.

## Tests und Qualität

GitHub Actions führt `python -m compileall` sowie `python -m unittest discover -s tests -v` bei jedem Push aus. UI-Smoketests laufen ohne Live-Zugangsschlüssel. Externe Yahoo-/Gemini-Aufrufe werden **nicht** durch diese automatischen Tests als verfügbar bestätigt.

## Projektstruktur

- `app.py` — neue Navigation, UI und Abläufe
- `theme.py` — Schwarz-Lila-Designsystem ohne Farbverläufe
- `market_data.py` — historische Daten, eindeutige Instrumente
- `offline.py` — CSV-Verarbeitung und Marktindikatoren
- `strategies.py` — getrennte Breakout-, Pullback- und Range-Logik sowie Preiszonen
- `engine.py` — Ergebnisvalidierung
- `quality.py` — Datenqualität, Quellen- und Zeitstempel
- `backtest.py` — konservativer Bar-Backtest
- `vision.py` — optionales Gemini-Bildverständnis (Opt-in)
- `tests/` — automatische Tests

**Quellen/Dokumentation:** [TradingView-CSV-Export](https://de.tradingview.com/support/solutions/43000537255/), [Gemini API-Preise](https://ai.google.dev/gemini-api/docs/pricing), [Gemini Bildverarbeitung](https://ai.google.dev/gemini-api/docs/image-understanding), [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).
