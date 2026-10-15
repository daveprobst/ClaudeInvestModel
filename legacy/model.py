"""
Crash-deployment strategy backtest, CHF base currency.
Equity: S&P 500 total return (Shiller monthly averages, dividends reinvested), converted to CHF unhedged.
Dry powder: CHF cash earning an approximate historical Swiss short rate.
"""
import pandas as pd, numpy as np

# ---------- data ----------
sp = pd.read_csv('sp.csv', parse_dates=['Date'])
sp = sp[sp.Date >= '1900-01-01'].reset_index(drop=True)
sp['Dividend'] = sp['Dividend'].replace(0, np.nan).ffill()
p = sp.SP500.values
dy = sp.Dividend.values / p / 12
tr_usd = np.cumprod(np.r_[1, (p[1:] / p[:-1]) * (1 + dy[1:])])

fx = pd.read_csv('fx.csv', parse_dates=['Date'])
fx = fx[fx.Country.str.strip() == 'Switzerland'].set_index('Date')['Exchange rate']
def chf_per_usd(dt):
    if dt >= pd.Timestamp('1971-01-01'):
        return fx.asof(dt)
    # pre-1971 approximations (gold standard / Bretton Woods)
    if dt < pd.Timestamp('1933-04-01'): return 5.18
    if dt < pd.Timestamp('1934-02-01'):          # USD floats down vs gold-backed CHF
        f = (dt - pd.Timestamp('1933-04-01')).days / 306
        return 5.18 + f * (3.08 - 5.18)
    if dt < pd.Timestamp('1936-10-01'): return 3.08
    if dt < pd.Timestamp('1949-10-01'): return 4.32
    return 4.37
usdchf = np.array([chf_per_usd(x) for x in sp.Date])
tr_chf = tr_usd * usdchf / usdchf[0]

# approximate Swiss short-term (cash) rate, % p.a.
def chf_rate(y):
    table = [(1914,3.5),(1946,2.5),(1960,1.5),(1973,3.0),(1980,3.0),(1989,4.5),(1994,7.5),
             (2001,2.5),(2009,1.5),(2015,0.1),(2022,-0.75),(2023,0.5),(2024,1.5),(2025,1.0),(9999,0.0)]
    for end, r in table:
        if y < end: return r / 100
cash_m = np.array([(1 + chf_rate(x.year)) ** (1/12) for x in sp.Date])

ma10 = pd.Series(p).rolling(10).mean().values
dates = sp.Date

# ---------- strategies ----------
V1 = dict(first=0.20, cps={.3:.25,.4:.25,.5:.25,.6:.25,.7:.25}, months=24, trend=False, deadline=None)
V2 = dict(first=0.15, cps={.3:.15,.4:.20,.5:.25,.6:.35,.7:.50}, months=36, trend=True,  deadline=36)

def deploy(t, ref_peak, cfg, tr, horizon=180):
    """Start with 1.0 cash at trigger month t. Returns value path (len horizon+1)."""
    cash, units, done, bank = 1.0, 0.0, set(), 0.0
    def buy(a, i):
        nonlocal cash, units
        a = min(a, cash); units += a / tr[i]; cash -= a
    buy(cfg['first'], t); M = cash / cfg['months']; path = [cash + units * tr[t]]
    for k in range(1, horizon + 1):
        i = t + k
        if i >= len(p): break
        cash *= cash_m[i]
        for c, f in cfg['cps'].items():
            if c not in done and p[i] / ref_peak - 1 <= -c:
                done.add(c); buy(cash * f, i)
        bank += M
        if (not cfg['trend']) or p[i] > ma10[i] or (cfg['deadline'] and k >= cfg['deadline']):
            buy(bank, i); bank = 0
        if cfg['deadline'] and k >= cfg['deadline']: buy(cash, i)
        path.append(cash + units * tr[i])
    return np.array(path)

# ---------- 1) event study: every 20% drawdown from all-time high ----------
ath = np.maximum.accumulate(p); dd = p / ath - 1
events, armed = [], True
for i in range(len(p)):
    if dd[i] == 0: armed, peak = True, i
    if armed and dd[i] <= -0.2: events.append((peak, i)); armed = False

def months_to_profit(path):
    """first month value >= 1 after having been below, and months until it stays >= 1"""
    first = next((k for k in range(1, len(path)) if path[k] >= 1), None)
    below = [k for k in range(len(path)) if path[k] < 1]
    last = (below[-1] + 1) if below else 0
    if below and last >= len(path): last = None
    return first, last

def event_table():
    rows, paths = [], {}
    for pk, t in events:
        j = t
        while j < len(p) and dd[j] < 0: j += 1
        r = dict(peak=dates[pk].strftime('%Y-%m'), trigger=dates[t].strftime('%Y-%m'),
                 maxDD_usd=round(100*dd[t:j].min()))
        for name, cfg in (('V1', V1), ('V2', V2)):
            path = deploy(t, ath[t], cfg, tr_chf)
            if name == 'V2': paths[dates[t].year] = path
            for h in (12, 36, 60, 120):
                r[f'{name}_{h//12}y'] = round(100*(path[h]-1)) if h < len(path) else None
            r[f'{name}_trough'] = round(100*(path.min()-1))
            r[f'{name}_mo_profit'] = months_to_profit(path)[1]
        pu = deploy(t, ath[t], V2, tr_usd)
        r['V2usd_3y'] = round(100*(pu[36]-1)) if len(pu) > 36 else None
        r['V2usd_mo_profit'] = months_to_profit(pu)[1]
        ls = tr_chf[t:t+181] / tr_chf[t]
        r['LS_3y'] = round(100*(ls[36]-1)) if len(ls) > 36 else None
        r['LS_mo_profit'] = months_to_profit(ls)[1]
        rows.append(r)
    return pd.DataFrame(rows), paths

# ---------- 2) rolling start: begin waiting in cash in every month ----------
def rolling(cfg, H=120):
    out = []
    for s in range(0, len(p) - H):
        run_peak, t = p[s], None
        for i in range(s, s + H):
            run_peak = max(run_peak, p[i])
            if p[i] / run_peak - 1 <= -0.2: t = i; break
        if t is None:                      # never triggered: stayed in cash
            v = np.prod(cash_m[s+1:s+H+1]); wait = None
        else:
            cash0 = np.prod(cash_m[s+1:t+1])
            path = deploy(t, run_peak, cfg, tr_chf, horizon=s + H - t)
            v = cash0 * path[-1]; wait = t - s
        bh = tr_chf[s + H] / tr_chf[s]
        out.append(dict(start=dates[s], strat=v**(12/H)-1, bh=bh**(12/H)-1, wait=wait))
    return pd.DataFrame(out)

if __name__ == '__main__':
    tab, paths = event_table()
    pd.set_option('display.width', 250)
    print(tab.to_string())
    for name, cfg in (('V1', V1), ('V2', V2)):
        rl = rolling(cfg); rl['diff'] = rl.strat - rl.bh
        nt = rl.wait.isna().mean()
        print(f"\n{name} rolling 10y (CHF): lagged buy&hold in {100*(rl['diff']<0).mean():.0f}% of start months; "
              f"median diff {100*rl['diff'].median():.2f}%/yr; worst {100*rl['diff'].min():.2f}%/yr "
              f"(start {rl.start[rl['diff'].idxmin()]:%Y-%m}); best {100*rl['diff'].max():.2f}%/yr; "
              f"never triggered within 10y: {100*nt:.0f}%; median wait {rl.wait.median():.0f} mo")
        rl.to_csv(f'rolling_{name}.csv', index=False)
    np.save('paths.npy', paths, allow_pickle=True)
