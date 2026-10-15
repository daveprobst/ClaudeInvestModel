"""v5: 30/30/40 (S&P/Europe/SPI), US+EU hedged, reserve = CHF cash + CHF govt bonds.
Engine tracks holdings explicitly and logs every trade so the mechanics can be audited."""
exec(open('portfolio.py').read())
exec(open('chbond.py').read())
y10 = num(CH10Y)
DUR, CONV = 7.0, 60.0                    # Swiss govt bond index proxy: duration ~7y
dy_ = np.r_[0, np.diff(y10)]/100
bond_g = np.r_[1, (1 + y10[:-1]/1200 - DUR*dy_[1:] + 0.5*CONV*dy_[1:]**2)]
cash_g = np.r_[1, chf_m[1:]]

def run_sleeve2(k, eq, s, e, start_cash, sell_sig=None, floor=0.5, sell_months=12, wait_cap=36,
                bond_share=0.5, log=None, cooldown=12, tc=0.001):
    P, ma = PRICE[k], MA[k]; cool_until = s; COST = np.zeros(e-s+1)
    tot0 = 1.0
    units = 0.0 if start_cash else tot0/eq[s]
    cash = tot0*(1-bond_share) if start_cash else 0.0
    bond = tot0*bond_share if start_cash else 0.0
    dep = None; step = None; last_sale = s if start_cash else None
    peak_p = ATH[k][s]; peak_i = int(np.where(P[:s+1] == peak_p)[0][-1])
    H = np.zeros((e-s+1, 3))                                     # equity, bonds, cash (CHF)
    def reserve(): return cash + bond
    def take(a):                                                 # withdraw a from reserve pro rata
        nonlocal cash, bond
        r = reserve(); a = min(a, r)
        if r > 0: cash -= a*cash/r; bond -= a*bond/r
        return a
    def put(a):                                                  # deposit a into reserve at target split
        nonlocal cash, bond
        cash += a*(1-bond_share); bond += a*bond_share
    def rec(i, what, a):
        if log is not None: log.append((D[i], k, what, round(a, 4)))
    for i in range(s, e+1):
        if i > s:
            cash *= cash_g[i]; bond *= bond_g[i]
            r_ = cash + bond; cash, bond = r_*(1-bond_share), r_*bond_share     # keep reserve at target split
        if P[i] >= peak_p: peak_p, peak_i = P[i], i
        eqv = units*eq[i]; tot = eqv + reserve(); w = eqv/tot
        sig = sell_sig is not None and bool(sell_sig[i])
        # ---- SELL leg: stocks -> reserve (CHF cash + CHF bonds) ----
        if dep is None and sig and w > floor + 1e-9 and i >= cool_until:
            if step is None: step = tot/sell_months; rec(i, 'SELL signal on', 0)
            a = min(step, eqv - floor*tot); units -= a/eq[i]; put(a*(1-tc)); COST[i-s] += a*tc; last_sale = i; rec(i, 'sell', a)
        elif not sig: step = None
        # ---- BUY leg: crash trigger or wait cap ----
        if dep is None and reserve() > 0.01*tot:
            trig, months, first = trig_params(k, peak_i, False)
            dd_now = P[i]/peak_p - 1
            crash = dd_now <= -trig
            capped = wait_cap and last_sale is not None and i - last_sale >= wait_cap and not sig
            if crash or capped:
                a = take(reserve()*first); units += a*(1-tc)/eq[i]; COST[i-s] += a*tc
                rec(i, f'TRIGGER {"crash %.0f%%" % (100*dd_now) if crash else "wait-cap DCA"}', a)
                dep = dict(t=i, M=reserve()/months, bank=0.0, ref=peak_p, trend=crash, dl=36 if crash else 24,
                           done={c for c in CP if c <= trig+1e-9} if crash else set(CP))
        elif dep is not None:
            kk = i - dep['t']
            for c, f in CP.items():
                if c not in dep['done'] and P[i]/dep['ref'] - 1 <= -c:
                    dep['done'].add(c); a = take(reserve()*f); units += a*(1-tc)/eq[i]; COST[i-s] += a*tc; rec(i, f'checkpoint -{int(c*100)}%', a)
            dep['bank'] += dep['M']
            if (not dep['trend']) or P[i] > ma[i] or kk >= dep['dl']:
                a = take(dep['bank']); units += a*(1-tc)/eq[i]; COST[i-s] += a*tc; dep['bank'] = 0
                if a > 1e-9: rec(i, 'monthly buy', a)
            if kk >= dep['dl'] or reserve() < 1e-9:
                a = take(reserve()); units += a*(1-tc)/eq[i]; COST[i-s] += a*tc; rec(i, 'deployment complete', a); dep = None; last_sale = None; cool_until = i + cooldown
        H[i-s] = (units*eq[i], bond, cash)
    run_sleeve2.cost = COST
    return H

COSTS = {}
def portfolio2(h=1.0, s=0, e=None, mode='cycle', rule=(30,120,True,0.5), sell_scope='all', bond_share=0.5,
               wait_cap=36, log=None, rebalance=False, static_eq=None):
    e = N-1 if e is None else e; out = {}
    for k, wk in W.items():
        eq = sleeve_index(k, 0.0 if k == 'CH' else h)
        if mode == 'bh':
            v = eq[s:e+1]/eq[s]; Hk = np.c_[v, 0*v, 0*v]
        else:
            sig = None
            if mode == 'cycle' and (k == 'US' or sell_scope == 'all'):
                C, B, trend, _ = rule
                sig = (CAPE >= C) & (BI >= B) & ((PRICE[k] < MA[k]) if trend else True)
            Hk = run_sleeve2(k, eq, s, e, start_cash=(mode == 'crash'), sell_sig=sig, floor=rule[3],
                             wait_cap=wait_cap, bond_share=bond_share, log=log)
        out[k] = wk*Hk
        if mode != 'bh': COSTS[k] = wk*run_sleeve2.cost
    Htot = sum(out.values()); return Htot.sum(1), Htot, out

def rebal_mix(h=1.0, eq_w=1.0, bond_share=0.5, s=0, e=None):
    """annually rebalanced 30/30/40 equity mix at weight eq_w, rest in reserve (CHF cash/bonds)"""
    e = N-1 if e is None else e
    g = {k: np.r_[1, sleeve_index(k, 0.0 if k=='CH' else h)[1:]/sleeve_index(k, 0.0 if k=='CH' else h)[:-1]] for k in W}
    res_g = bond_share*bond_g + (1-bond_share)*cash_g
    tgt = {**{k: eq_w*W[k] for k in W}, 'R': 1-eq_w}; hold = dict(tgt); v = [1.0]
    for i in range(s+1, e+1):
        for k in W: hold[k] *= g[k][i]
        hold['R'] *= res_g[i]; tot = sum(hold.values()); v.append(tot)
        if D[i].month == 1: hold = {k: tgt[k]*tot for k in tgt}
    return np.array(v)
