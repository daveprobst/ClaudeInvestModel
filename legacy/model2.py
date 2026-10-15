"""Crash strategy v3: trigger-level sweep, CAPE-adaptive pacing, currency hedge. CHF base."""
import pandas as pd, numpy as np
exec(open('model.py').read().split("# ---------- strategies")[0])   # data: p, tr_usd, tr_chf, usdchf, cash_m, dates

cape = sp.PE10.replace(0, np.nan).ffill().values
ma10 = pd.Series(p).rolling(10).mean().values
ath = np.maximum.accumulate(p); dd = p / ath - 1

# approximate US 3-month T-bill rate (for hedging cost), % p.a.
def usd_rate(y):
    table=[(1930,4.0),(1950,0.7),(1960,2.0),(1970,4.0),(1980,6.5),(1985,11.0),(1990,7.0),(2000,5.0),(2002,5.0),
           (2005,1.5),(2008,4.5),(2016,0.1),(2020,1.5),(2022,0.1),(2023,2.0),(2025,5.0),(9999,4.0)]
    for end,r in table:
        if y < end: return r/100
usd_m = np.array([(1+usd_rate(x.year))**(1/12) for x in dates])
# hedged CHF return = USD total return + (CHF rate - USD rate)
tr_hedged = np.cumprod(np.r_[1, (tr_usd[1:]/tr_usd[:-1]) * cash_m[1:] / usd_m[1:]])

CP_DEFAULT = {.3:.15,.4:.20,.5:.25,.6:.35,.7:.50}

def make(trig=0.20, first=0.15, months=36, trend=True, deadline=36, cape_adapt=False,
         hedge=0.0, pre=0.0, cps=CP_DEFAULT, wait_limit=None):
    return dict(trig=trig, first=first, months=months, trend=trend, deadline=deadline,
                cape_adapt=cape_adapt, hedge=hedge, pre=pre, cps=cps, wait_limit=wait_limit)

def params_at(cfg, peak_i):
    """CAPE-adaptive: expensive market at the peak -> deeper trigger, slower deployment"""
    trig, months, first = cfg['trig'], cfg['months'], cfg['first']
    if cfg['cape_adapt']:
        c = cape[peak_i]
        if c >= 35:   trig, months, first = max(trig, 0.30), 48, 0.10
        elif c >= 25: trig, months, first = max(trig, 0.25), 42, 0.15
    return trig, months, first

def run(cfg, s, H, peak_mode='running'):
    """Start at month s with capital 1. Returns value path of length H+1 (CHF)."""
    h = cfg['hedge']
    eq = (1-h)*tr_chf/tr_chf[s] + h*tr_hedged/tr_hedged[s]     # equity index in CHF, rebased
    units = cfg['pre'] / eq[s]; cash = 1 - cfg['pre']
    trig_i = None; bank = 0; done = set(); peak_p = p[s]; peak_i = s
    if peak_mode == 'ath': peak_p = ath[s]; peak_i = int(np.where(p[:s+1] == ath[s])[0][-1])
    path = []
    for k in range(H+1):
        i = s + k
        if i >= len(p): break
        if k > 0: cash *= cash_m[i]
        if trig_i is None:
            if p[i] > peak_p: peak_p, peak_i = p[i], i
            trig, months, first = params_at(cfg, peak_i)
            limit_hit = cfg['wait_limit'] and k >= cfg['wait_limit']
            if p[i]/peak_p - 1 <= -trig or limit_hit:
                trig_i = i; a = cash*first; units += a/eq[i]; cash -= a
                M = cash/months; done = {c for c in cfg['cps'] if c <= trig + 1e-9}
                if limit_hit and not p[i]/peak_p - 1 <= -trig: done = set(cfg['cps'])  # plain DCA
        else:
            kk = i - trig_i
            for c, f in cfg['cps'].items():
                if c not in done and p[i]/peak_p - 1 <= -c:
                    done.add(c); a = cash*f; units += a/eq[i]; cash -= a
            bank += M
            if (not cfg['trend']) or p[i] > ma10[i] or kk >= cfg['deadline']:
                a = min(bank, cash); units += a/eq[i]; cash -= a; bank = 0
            if kk >= cfg['deadline']: units += cash/eq[i]; cash = 0
        path.append(cash + units*eq[i])
    global LAST_TRIG; LAST_TRIG = trig_i
    return np.array(path)

# crash episodes: month the S&P first hits -20% from an all-time high
events, armed = [], True
for i in range(len(p)):
    if dd[i] == 0: armed = True
    if armed and dd[i] <= -0.2: events.append(i); armed = False

def breakeven(path):
    m = int(np.argmin(path))
    if path[m] >= 1: return 0.0
    k = next((k for k in range(m, len(path)) if path[k] >= 1), None)
    return None if k is None else k/12

def event_stats(cfg, H=180):
    rows = []
    for t in events:
        path = run(cfg, t, H, peak_mode='ath')
        g = lambda h: 100*(path[h]-1) if h < len(path) else np.nan
        rows.append(dict(crash=dates[t].year, r1=g(12), r3=g(36), r5=g(60), r10=g(120),
                         trough=100*(path.min()-1), be=breakeven(path[:H+1])))
    return pd.DataFrame(rows)

def rolling_stats(cfg, H=120):
    out = []
    for s in range(0, len(p)-H):
        v = run(cfg, s, H)[-1]; bh = tr_chf[s+H]/tr_chf[s]
        out.append((dates[s], v**(12/H)-1, bh**(12/H)-1))
    return pd.DataFrame(out, columns=['start','strat','bh'])
