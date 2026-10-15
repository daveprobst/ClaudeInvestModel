"""v6: adds (a) a fast 'logarithmic' sell transition to 0% stocks and (b) per-market valuation signals."""
exec(open('portfolio2.py').read())

# ---------- per-market valuation proxy: price index / nominal GDP (local currency) ----------
gdp = pd.read_csv('gdp.csv')
fx_year = lambda arr: pd.Series(arr, index=D).groupby(D.year).mean()
chf_usd_y = fx_year(chf_usd); eur_usd_y = fx_year(eur_per_usd)
def gdp_local(code, fx_y, g_after):
    s = gdp[gdp['Country Code']==code].set_index('Year')['Value']
    s = s[s.index >= 1970]
    loc = pd.Series({y: s[y]*fx_y.get(y, np.nan) for y in s.index}).dropna()
    for y in (2024, 2025, 2026): loc[y] = loc[y-1]*(1+g_after)          # extend with assumed nominal growth
    t = D.year + (D.month-1)/12 - 0.5 + 1/24
    return np.exp(np.interp(t, loc.index.values.astype(float), np.log(loc.values)))
dem_usd_y = eur_usd_y*1.95583
gdp_ch = gdp_local('CHE', chf_usd_y, 0.02)
gdp_emu = gdp_local('EMU', eur_usd_y, 0.035); gdp_de = gdp_local('DEU', eur_usd_y, 0.03)
i87 = int(np.where(D == pd.Timestamp('1986-12-01'))[0][0])
r_eu = np.where(np.arange(N) <= i87, P_eu/gdp_de * (gdp_de[i87]/gdp_emu[i87]), P_eu/gdp_emu)   # chain DE -> EMU
VAL = {'CH': P_ch/gdp_ch, 'EU': r_eu}
def exp_pct(x, min_hist=120):
    out = np.full(len(x), np.nan)
    for i in range(min_hist, len(x)): out[i] = (x[:i+1] <= x[i]).mean()
    return out
PCT = {k: exp_pct(v) for k, v in VAL.items()}
# US for reference: expanding percentile of CAPE and of the Buffett proxy since 1971
PCT_US_CAPE = exp_pct(CAPE, 0); PCT_US_BI = exp_pct(BI, 0)

def trig_params_v6(k, peak_i, decoupled):
    if k == 'US':
        c = CAPE[peak_i]
        if c >= 35: return 0.30, 48, 0.10
        if c >= 25: return 0.25, 42, 0.15
        return 0.20, 36, 0.15
    if decoupled and not np.isnan(PCT[k][peak_i]):
        q = PCT[k][peak_i]
        if q >= 0.90: return 0.30, 48, 0.10
        if q >= 0.75: return 0.25, 42, 0.15
    return 0.20, 36, 0.15

def log_path(t, T=6, kk=30):
    """share of the planned sale completed after t months (t=1 is the first month)"""
    return min(1.0, np.log(1+kk*t)/np.log(1+kk*T))

def run_sleeve3(k, eq, s, e, start_cash, sell_sig=None, floor=0.5, sell_months=12, wait_cap=36, bond_share=0.5,
                shape='linear', T=6, kk=30, decoupled=False, cooldown=12, tc=0.001, log=None):
    P, ma = PRICE[k], MA[k]
    units = 0.0 if start_cash else 1/eq[s]; cash = (1-bond_share) if start_cash else 0.0; bond = bond_share if start_cash else 0.0
    dep = None; ep = None; last_sale = s if start_cash else None; cool_until = s
    peak_p = ATH[k][s]; peak_i = int(np.where(P[:s+1] == peak_p)[0][-1]); H = np.zeros((e-s+1, 3)); COST = np.zeros(e-s+1)
    reserve = lambda: cash + bond
    def take(a):
        nonlocal cash, bond
        r = reserve(); a = min(a, r)
        if r > 0: cash -= a*cash/r; bond -= a*bond/r
        return a
    def put(a):
        nonlocal cash, bond
        cash += a*(1-bond_share); bond += a*bond_share
    rec = lambda i, what, a: log.append((D[i], k, what, round(a, 4))) if log is not None else None
    for i in range(s, e+1):
        if i > s:
            cash *= cash_g[i]; bond *= bond_g[i]; r_ = cash+bond; cash, bond = r_*(1-bond_share), r_*bond_share
        if P[i] >= peak_p: peak_p, peak_i = P[i], i
        eqv = units*eq[i]; tot = eqv + reserve(); w = eqv/tot
        sig = sell_sig is not None and bool(sell_sig[i])
        # ----- SELL: stocks -> reserve -----
        if dep is None and sig and w > floor + 1e-9 and i >= cool_until:
            if ep is None: ep = dict(t0=i, w0=w); rec(i, 'SELL signal on', w)
            t = i - ep['t0'] + 1
            if shape == 'log': target = floor + (ep['w0']-floor)*(1-log_path(t, T, kk))
            else:              target = max(floor, ep['w0'] - t/sell_months)
            a = max(0.0, eqv - target*tot)
            if a > 1e-12: units -= a/eq[i]; put(a*(1-tc)); COST[i-s] += a*tc; last_sale = i; rec(i, 'sell', a)
        elif not sig: ep = None
        # ----- BUY -----
        if dep is None and reserve() > 0.01*tot:
            trig, months, first = trig_params_v6(k, peak_i, decoupled)
            ddn = P[i]/peak_p - 1; crash = ddn <= -trig
            capped = wait_cap and last_sale is not None and i - last_sale >= wait_cap and not sig
            if crash or capped:
                a = take(reserve()*first); units += a*(1-tc)/eq[i]; COST[i-s] += a*tc
                rec(i, 'TRIGGER crash %.0f%%' % (100*ddn) if crash else 'TRIGGER wait-cap DCA', a)
                dep = dict(t=i, M=reserve()/months, bank=0.0, ref=peak_p, trend=crash, dl=36 if crash else 24,
                           done={c for c in CP if c <= trig+1e-9} if crash else set(CP))
        elif dep is not None:
            kk_ = i - dep['t']
            for c, f in CP.items():
                if c not in dep['done'] and P[i]/dep['ref'] - 1 <= -c:
                    dep['done'].add(c); a = take(reserve()*f); units += a*(1-tc)/eq[i]; COST[i-s] += a*tc; rec(i, f'checkpoint -{int(c*100)}%', a)
            dep['bank'] += dep['M']
            if (not dep['trend']) or P[i] > ma[i] or kk_ >= dep['dl']:
                a = take(dep['bank']); units += a*(1-tc)/eq[i]; COST[i-s] += a*tc; dep['bank'] = 0
            if kk_ >= dep['dl'] or reserve() < 1e-9:
                a = take(reserve()); units += a*(1-tc)/eq[i]; COST[i-s] += a*tc; rec(i, 'deployment complete', a)
                dep = None; last_sale = None; cool_until = i + cooldown; ep = None
        H[i-s] = (units*eq[i], bond, cash)
    run_sleeve3.cost = COST
    return H

EU_CH_PCT = 0.90
def signals(k, decoupled, us_rule=(30,120)):
    trend = PRICE[k] < MA[k]
    if k == 'US' or not decoupled: return (CAPE >= us_rule[0]) & (BI >= us_rule[1]) & trend
    return (np.nan_to_num(PCT[k]) >= EU_CH_PCT) & trend

COSTS3 = {}
def portfolio3(h=1.0, s=0, e=None, mode='cycle', floor=0.5, shape='linear', decoupled=False, log=None, **kw):
    e = N-1 if e is None else e; out = {}
    for k, wk in W.items():
        eq = sleeve_index(k, 0.0 if k == 'CH' else h)
        if mode == 'bh': v = eq[s:e+1]/eq[s]; Hk = np.c_[v, 0*v, 0*v]
        else:
            Hk = run_sleeve3(k, eq, s, e, start_cash=(mode=='crash'), sell_sig=signals(k, decoupled) if mode=='cycle' else None,
                             floor=floor, shape=shape, decoupled=decoupled, log=log, **kw)
            COSTS3[k] = wk*run_sleeve3.cost
        out[k] = wk*Hk
    Ht = sum(out.values()); return Ht.sum(1), Ht, out
