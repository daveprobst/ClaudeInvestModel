"""v7: committed switches. Sell trigger -> log transition to 0% stocks (completes no matter what),
stay 100% in the block's reserve until a crash trigger or valuation all-clear, then buy back.
Reserves: SPI block -> CHF cash; S&P block -> US Treasuries; Europe block -> German Bunds (hedged to CHF).
Valuation percentiles over a moving window."""
exec(open('portfolio3.py').read())
exec(open('bonddata.py').read())

# ---------- reserve instruments ----------
us_y_full = sp['Long Interest Rate'].values.astype(float)          # Shiller file (GS10), from 1900 rows
us10 = us_y_full[iu].copy(); j = int(np.where(D == pd.Timestamp('2023-10-01'))[0][0]); us10[j:] = num(US10Y_TAIL)
de10 = num(DE10Y)
def bond_growth(y, dur=7.0, conv=60.0):
    dy = np.r_[0, np.diff(y)]/100
    return np.r_[1, 1 + y[:-1]/1200 - dur*dy[1:] + 0.5*conv*dy[1:]**2]
bond_us_local = bond_growth(us10); bond_de_local = bond_growth(de10)
def reserve_growth(k, h_bond=1.0):
    if k == 'CH': return cash_g
    if k == 'US': return h_bond*bond_us_local*chf_m/us_m + (1-h_bond)*bond_us_local*fxg(chf_usd)
    return h_bond*bond_de_local*chf_m/eu_m + (1-h_bond)*bond_de_local*fxg(chf_eur)
RES_NAME = {'CH': 'CHF cash', 'US': 'US Treasuries', 'EU': 'German Bunds'}

# ---------- moving-window percentiles ----------
cape_full = cape.astype(float); bi_full = bi.astype(float)        # US arrays on the long (1900+) grid
def roll_pct(x, win, min_hist=120):
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        if np.isnan(x[i]): continue
        lo = 0 if win is None else max(0, i-win+1); w = x[lo:i+1]; w = w[~np.isnan(w)]
        if len(w) >= min_hist: out[i] = (w <= x[i]).mean()
    return out
_cache = {}
def pct_series(k, win):
    key = (k, win)
    if key not in _cache:
        if k == 'US':
            _cache[key] = (roll_pct(cape_full, win)[iu], roll_pct(bi_full, win)[iu])
        else:
            _cache[key] = (roll_pct(VAL[k], win),)
    return _cache[key]

def val_level(k, win, us_mode):
    """one number per month: the (lower) valuation percentile that must exceed the threshold"""
    if k == 'US' and us_mode == 'abs':
        return None
    s = pct_series(k, win)
    return np.fmin(s[0], s[1]) if k == 'US' else s[0]

# ---------- the engine ----------
def run_block(k, s, e, h=1.0, win=300, q=0.90, q_mid=0.75, q_clear=0.70, us_mode='pct', T=6, kk=30,
              reentry_months=24, cooldown=12, tc=0.001, h_bond=1.0, log=None):
    eq = sleeve_index(k, 0.0 if k == 'CH' else h); rg = reserve_growth(k, h_bond)
    P, ma = PRICE[k], MA[k]; V = val_level(k, win, us_mode)
    if V is None:   # US absolute thresholds
        hi = (CAPE >= 30) & (BI >= 120); clear = (CAPE < 25) & (P > ma); depth_lvl = CAPE
    else:
        hi = np.nan_to_num(V) >= q; clear = (np.nan_to_num(V, nan=1) < q_clear) & (P > ma); depth_lvl = V
    def depth(pi):
        if V is None:
            c = CAPE[pi]; return (0.30,48,0.10) if c >= 35 else (0.25,42,0.15) if c >= 25 else (0.20,36,0.15)
        v = depth_lvl[pi]
        if np.isnan(v): return (0.20,36,0.15)
        return (0.30,48,0.10) if v >= q else (0.25,42,0.15) if v >= q_mid else (0.20,36,0.15)
    units = 1/eq[s]; res = 0.0; state = 'IN'; cool = s; st = {}
    peak_p = ATH[k][s]; peak_i = int(np.where(P[:s+1] == peak_p)[0][-1])
    H = np.zeros((e-s+1, 2)); S = []; COST = np.zeros(e-s+1)
    def rec(i, what, x=0.0):
        if log is not None: log.append(dict(date=D[i], block=k, event=what, value=round(float(x), 4)))
    def buy(i, a):
        nonlocal units, res
        a = min(a, res); units += a*(1-tc)/eq[i]; res -= a; COST[i-s] += a*tc
    def sell(i, a):
        nonlocal units, res
        a = min(a, units*eq[i]); units -= a/eq[i]; res += a*(1-tc); COST[i-s] += a*tc
    for i in range(s, e+1):
        lab = None
        if i > s: res *= rg[i]
        if P[i] >= peak_p: peak_p, peak_i = P[i], i
        tot = units*eq[i] + res
        sig = bool(hi[i]) and P[i] < ma[i]
        if state == 'IN' and sig and i >= cool:
            state = 'SELLING'; st = dict(t0=i, w0=units*eq[i]/tot); rec(i, 'SELL TRIGGER', st['w0'])
        if state == 'SELLING':
            t = i - st['t0'] + 1
            target = st['w0']*(1 - log_path(t, T, kk)) if t < T else 0.0
            eqv = units*eq[i]; tot = eqv + res
            sell(i, max(0.0, eqv - target*tot))
            if t >= T:
                sell(i, units*eq[i]); units = 0.0; state = 'OUT'; lab = 'SELLING'; st = dict(since=i); rec(i, 'reached 0% stocks')
        elif state == 'OUT':
            trig, months, first = depth(peak_i); dd = P[i]/peak_p - 1
            if dd <= -trig:
                buy(i, res*first); state = 'DEPLOY'
                st = dict(t=i, M=res/months, bank=0.0, ref=peak_p, done={c for c in CP if c <= trig+1e-9})
                rec(i, f'CRASH BUY TRIGGER ({dd*100:.0f}% from high, trigger {trig*100:.0f}%)')
            elif clear[i]:
                state = 'REENTRY'; st = dict(t=i, M=res/reentry_months); rec(i, 'ALL-CLEAR re-entry (valuation normal + uptrend)')
        elif state == 'DEPLOY':
            kk_ = i - st['t']
            for c, f in CP.items():
                if c not in st['done'] and P[i]/st['ref'] - 1 <= -c:
                    st['done'].add(c); buy(i, res*f); rec(i, f'checkpoint -{int(c*100)}%')
            st['bank'] += st['M']
            if P[i] > ma[i] or kk_ >= 36: buy(i, st['bank']); st['bank'] = 0.0
            if kk_ >= 36 or res < 1e-12:
                buy(i, res); res = 0.0; state = 'IN'; cool = i + cooldown; rec(i, 'fully re-invested')
        elif state == 'REENTRY':
            buy(i, st['M'])
            if i - st['t'] >= reentry_months-1 or res < 1e-12:
                buy(i, res); res = 0.0; state = 'IN'; cool = i + cooldown; rec(i, 'fully re-invested')
        H[i-s] = (units*eq[i], res); S.append(lab or state)
    return H, S, COST

def portfolio4(s=0, e=None, mode='cycle', log=None, **kw):
    e = N-1 if e is None else e; out, states, costs = {}, {}, {}
    for k, wk in W.items():
        if mode == 'bh':
            eq = sleeve_index(k, 0.0 if k == 'CH' else kw.get('h', 1.0)); v = eq[s:e+1]/eq[s]
            Hk = np.c_[v, 0*v]; Sk = ['IN']*len(v); Ck = 0*v
        else:
            Hk, Sk, Ck = run_block(k, s, e, log=log, **kw)
        out[k] = wk*Hk; states[k] = Sk; costs[k] = wk*Ck
    Ht = sum(out.values()); return Ht.sum(1), Ht, out, states, costs
