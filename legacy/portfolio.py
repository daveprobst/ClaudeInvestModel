"""30% S&P 500 / 30% Europe / 40% SPI — crash-buy and valuation-sell rules, CHF base, 1971-2026."""
exec(open('model3.py').read())          # US data: p, tr_usd, usdchf, cape, bi, cash_m (CHF), usd_m, dates
exec(open('eudata.py').read())
import pandas as pd, numpy as np

D = pd.date_range('1971-01-01', '2026-08-01', freq='MS'); N = len(D)
iu = np.array([np.where(dates == d)[0][0] for d in D])       # map to US arrays
num = lambda s: np.array([float(x) for x in s.split()])

# ---- price indices (local currency, monthly averages) ----
P_ch = num(CH_1971)
ez = pd.Series(num(EZ_1986_12), index=pd.date_range('1986-12-01', '2026-01-01', freq='MS'))
de = pd.Series(num(DE_1971_1986), index=pd.date_range('1971-01-01', '1986-12-01', freq='MS'))
de26 = pd.Series(num(DE_2026), index=pd.date_range('2026-01-01', '2026-08-01', freq='MS'))
eu = pd.concat([de[:-1] * ez.iloc[0] / de.iloc[-1], ez, (de26[1:] * ez.iloc[-1] / de26.iloc[0])])
P_eu = eu.reindex(D).values
P_us = p[iu]

# ---- FX: CHF per unit of foreign currency ----
fxd = pd.read_csv('fx.csv', parse_dates=['Date']); fxd['Country'] = fxd.Country.str.strip()
def ser(c): return fxd[fxd.Country == c].set_index('Date')['Exchange rate']
chf_usd = ser('Switzerland').reindex(D).ffill().values
eur_per_usd = pd.concat([ser('Germany')[:'1998-12-01'] / 1.95583, ser('Euro')['1999-01-01':]]).reindex(D).ffill().values
chf_eur = chf_usd / eur_per_usd

# ---- short rates (approx, % p.a.) ----
def eur_rate(y):
    tbl = [(1973,6),(1975,10),(1979,4.5),(1983,9),(1989,5.5),(1993,8.5),(1994,7),(1999,4.5),(2000,3),(2002,4.4),
           (2006,2.5),(2009,3.8),(2012,1.0),(2015,0.2),(2022,-0.3),(2023,0.5),(2024,3.4),(2025,3.6),(2026,2.2),(9999,2.0)]
    for e, r in tbl:
        if y < e: return r/100
chf_m = cash_m[iu]; us_m = usd_m[iu]
eu_m = np.array([(1+eur_rate(d.year))**(1/12) for d in D])

# ---- monthly total return factors (local), dividends: S&P actual, EU 3.0%, CH 2.5% ----
def tr_local(P, dy): return np.r_[1, (P[1:]/P[:-1]) * (1+dy)**(1/12)]
g_us = np.r_[1, tr_usd[iu][1:]/tr_usd[iu][:-1]]
g_eu = tr_local(P_eu, 0.030); g_ch = tr_local(P_ch, 0.025)
fxg = lambda fx: np.r_[1, fx[1:]/fx[:-1]]

def sleeve_index(name, h):
    """CHF total-return index for a sleeve with hedge ratio h (monthly rebalanced hedge)"""
    if name == 'CH': g = g_ch
    elif name == 'US': g = h*g_us*chf_m/us_m + (1-h)*g_us*fxg(chf_usd)
    else:              g = h*g_eu*chf_m/eu_m + (1-h)*g_eu*fxg(chf_eur)
    return np.cumprod(g)

PRICE = {'US': P_us, 'EU': P_eu, 'CH': P_ch}
W = {'US': .30, 'EU': .30, 'CH': .40}
MA = {k: pd.Series(v).rolling(10, min_periods=1).mean().values for k, v in PRICE.items()}
ATH = {k: np.maximum.accumulate(v) for k, v in PRICE.items()}
CAPE = cape[iu]; BI = bi[iu]
CP = {.3:.15,.4:.20,.5:.25,.6:.35,.7:.50}

def trig_params(k, peak_i, cape_all):
    """crash trigger depth: CAPE-adaptive for US (or for all sleeves if cape_all), else 20%"""
    if k == 'US' or cape_all:
        c = CAPE[peak_i]
        if c >= 35: return 0.30, 48, 0.10
        if c >= 25: return 0.25, 42, 0.15
    return 0.20, 36, 0.15

def run_sleeve(k, eq, s, e, start_cash, sell_sig=None, floor=0.5, sell_months=12, wait_cap=36, cape_all=False):
    """One sleeve. start_cash=True: begin in cash waiting for a crash; else begin invested.
    sell_sig: boolean array -> sell toward `floor` while True. Cash is redeployed by the crash rule."""
    P, ma, ath = PRICE[k], MA[k], ATH[k]
    units = 0.0 if start_cash else 1/eq[s]; cash = 1.0 if start_cash else 0.0
    dep = None; step = None; last_sale = s if start_cash else None; out = np.empty(e-s+1)
    peak_p, peak_i = (ath[s], int(np.where(P[:s+1] == ath[s])[0][-1]))
    for i in range(s, e+1):
        if i > s: cash *= chf_m[i]
        if P[i] >= peak_p: peak_p, peak_i = P[i], i
        tot = units*eq[i] + cash; w = units*eq[i]/tot
        sig = sell_sig is not None and sell_sig[i]
        if dep is None and sig and w > floor + 1e-6:                      # SELL
            if step is None: step = tot/sell_months
            a = min(step, units*eq[i] - floor*tot); units -= a/eq[i]; cash += a; last_sale = i
        elif not sig: step = None
        if dep is None and cash > 0.01*tot:                                 # BUY trigger
            trig, months, first = trig_params(k, peak_i, cape_all)
            crash = P[i]/peak_p - 1 <= -trig
            capped = wait_cap and last_sale is not None and i - last_sale >= wait_cap and not sig
            if crash or capped:
                a = cash*first; units += a/eq[i]; cash -= a
                dep = dict(t=i, M=cash/months, bank=0.0, ref=peak_p, trend=crash, dl=36 if crash else 24,
                           done={c for c in CP if c <= trig+1e-9} if crash else set(CP))
        elif dep is not None:                                               # deploying
            kk = i - dep['t']
            for c, f in CP.items():
                if c not in dep['done'] and P[i]/dep['ref'] - 1 <= -c:
                    dep['done'].add(c); a = cash*f; units += a/eq[i]; cash -= a
            dep['bank'] += dep['M']
            if (not dep['trend']) or P[i] > ma[i] or kk >= dep['dl']:
                a = min(dep['bank'], cash); units += a/eq[i]; cash -= a; dep['bank'] = 0
            if kk >= dep['dl'] or cash < 1e-9:
                units += cash/eq[i]; cash = 0; dep = None; last_sale = None
        out[i-s] = units*eq[i] + cash
    return out

def portfolio(h=0.5, s=0, e=None, mode='bh', rule=None, sell_scope='US', cape_all=False, wait_cap=36):
    """mode: 'bh' buy&hold, 'crash' start in cash + crash-buy, 'cycle' start invested + sell rule + crash-buy"""
    e = N-1 if e is None else e; tot = np.zeros(e-s+1); parts = {}
    for k, wk in W.items():
        eq = sleeve_index(k, 0.0 if k == 'CH' else h)
        if mode == 'bh': v = eq[s:e+1]/eq[s]
        else:
            sig = None
            if mode == 'cycle' and (k == 'US' or sell_scope == 'all'):
                C, B, trend, floor = rule
                sig = (CAPE >= C) & (BI >= B) & ((PRICE[k] < MA[k]) if trend else True)
            v = run_sleeve(k, eq, s, e, start_cash=(mode == 'crash'), sell_sig=sig,
                           floor=(rule[3] if rule else 0.5), wait_cap=wait_cap, cape_all=cape_all)
        parts[k] = wk*v; tot += wk*v
    return tot, parts

def stats(v):
    yrs = (len(v)-1)/12; return dict(cagr=100*(v[-1]**(1/yrs)-1), maxdd=100*(v/np.maximum.accumulate(v)-1).min())
