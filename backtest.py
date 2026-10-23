"""Konservativer, rein historischer Mini-Backtest – nie ein Ausführungs-/Live-Signal."""
from __future__ import annotations
import pandas as pd
from strategies import analyze_strategies

def run_backtest(df: pd.DataFrame, market: str, style: str, timeframe: str,
                 cost_points: float = 0., max_bars: int = 320) -> tuple[dict, pd.DataFrame]:
    if cost_points < 0 or cost_points > 1e6:
        raise ValueError('Kosten in Preiseinheiten müssen positiv und plausibel sein.')
    prices = df.tail(max(90,min(int(max_bars),600))).reset_index(drop=True)
    if len(prices) < 85:
        raise ValueError('Mindestens 85 Kerzen für diesen Backtest benötigt.')
    duration = {'Scalping':8,'Daytrading':24,'Swingtrading':48}.get(style,12)
    deals: list[dict] = []
    i=65
    while i < len(prices)-2:
        # Only use candles through i, decide AFTER bar i closes.
        context=prices.iloc[:i+1].copy()
        a, _, info=analyze_strategies(context,market,style,timeframe)
        if a['signal'] not in ('LONG','SHORT'):
            i+=1
            continue
        side=a['signal']
        planned_sl=a['stop_loss']
        planned_tp=a['take_profit']
        entry=float(prices.open.iloc[i+1])
        atr=info['atr']
        # Reject large opening gaps and invalid distance; avoid retroactively moving risk.
        if abs(entry-float(prices.close.iloc[i])) > max(.25*atr,1e-8):
            i+=1
            continue
        if side=='LONG' and not (planned_sl < entry < planned_tp):
            i+=1
            continue
        if side=='SHORT' and not (planned_tp < entry < planned_sl):
            i+=1
            continue
        risk=abs(entry-planned_sl)
        if risk <= 1e-12 or cost_points >= risk*4:
            i+=1
            continue
        exit_price=None
        reason=None
        last_index=min(i+duration,len(prices)-1)
        for j in range(i+1,last_index+1):
            candle=prices.iloc[j]
            if side=='LONG':
                hit_stop=float(candle.low) <= planned_sl
                hit_take=float(candle.high) >= planned_tp
            else:
                hit_stop=float(candle.high) >= planned_sl
                hit_take=float(candle.low) <= planned_tp
            if hit_stop:
                # Pessimistic rule: if target and stop hit in same candle, assume stop first.
                exit_price=planned_sl
                reason='SL (auch bei beidem in derselben Kerze)'
                break
            if hit_take:
                exit_price=planned_tp
                reason='TP'
                break
        else:
            j=last_index
            exit_price=float(prices.close.iloc[j])
            reason='Zeitlimit'
        gross=(exit_price-entry)*(1 if side=='LONG' else -1)
        realized_r=round((gross-cost_points)/risk,4)
        deals.append({'Setup':info.get('selected_strategy','UNBEKANNT'),'Einstieg Kerze':i+1,'Ausstieg Kerze':j,'Richtung':side,
                      'Entry':round(entry,5),'Exit':round(exit_price,5),
                      'Stop':round(planned_sl,5),'Target':round(planned_tp,5),
                      'Grund':reason,'Ergebnis (R)':realized_r})
        i=j+1  # no overlapping trades
    history=pd.DataFrame(deals)
    if history.empty:
        return ({'trades':0,'wins':0,'win_rate':None,'avg_r':None,
                 'total_r':0.,'max_drawdown_r':0.,'profit_factor':None}, history)
    r=history['Ergebnis (R)']
    equity=r.cumsum()
    prior_peak=pd.concat([pd.Series([0.]),equity]).cummax().iloc[1:].reset_index(drop=True)
    dd=equity.reset_index(drop=True)-prior_peak
    positives=r[r>0].sum()
    negatives=-r[r<0].sum()
    return ({
        'trades':len(history),
        'wins':int((r>0).sum()),
        'win_rate':round(float((r>0).mean()*100),1),
        'avg_r':round(float(r.mean()),3),
        'total_r':round(float(r.sum()),3),
        'max_drawdown_r':round(float(dd.min()),3),
        'profit_factor':round(float(positives/negatives),3) if negatives>0 else None,
    },history)
