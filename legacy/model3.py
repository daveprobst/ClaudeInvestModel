"""Full-cycle strategy: valuation-based SELL trigger (CAPE + Buffett indicator) + crash BUY strategy
(CAPE-adaptive, 100% CHF-hedged). Test window 1971-2026 (floating CHF). """
exec(open('model2.py').read())

# ---- extend CAPE past Sep 2023 (Shiller file ends there); calibrated to CAPE 41.4 in Jul 2026 ----
last = np.where(sp.PE10.values > 0)[0][-1]
i_jul26 = np.where(dates == pd.Timestamp('2026-07-01'))[0][0]
raw = sp.PE10.values[last] * p / p[last]
adj_end = raw[i_jul26] / 41.4                       # implied growth of the 10y earnings base
cape = sp.PE10.values.astype(float).copy()
for i in range(last+1, len(p)):
    f = min(1, (i-last)/(i_jul26-last)); cape[i] = raw[i] / adj_end**f

# ---- Buffett indicator proxy: S&P price / US nominal GDP, scaled so Mar-2000 = 145% ----
g = pd.read_csv('gdp.csv'); g = g[g['Country Code']=='USA']
pre = {1929:104.6,1930:92.2,1931:77.4,1932:59.5,1933:57.2,1934:66.8,1935:74.2,1936:84.8,1937:93.0,1938:87.4,1939:93.4,
       1940:102.9,1941:129.3,1942:166.0,1943:203.1,1944:224.4,1945:228.0,1946:227.5,1947:249.6,1948:274.5,1949:272.5,
       1950:299.8,1951:346.9,1952:367.3,1953:389.2,1954:390.5,1955:425.5,1956:449.4,1957:474.0,1958:481.2,1959:521.7}
gd = {**{k:v*1e9 for k,v in pre.items()}, **dict(zip(g.Year, g.Value)), 2024:29.2e12, 2025:30.4e12, 2026:31.6e12}
yrs = np.array(sorted(gd)); lv = np.log([gd[y] for y in yrs])
tt = dates.dt.year + (dates.dt.month-1)/12 - 0.5 + 1/24
gdp_m = np.exp(np.interp(tt, yrs, lv, left=np.nan))
bi = p / gdp_m; bi = 145 * bi / bi[np.where(dates == pd.Timestamp('2000-03-01'))[0][0]]

S0 = int(np.where(dates == pd.Timestamp('1971-01-01'))[0][0])
eqH = tr_hedged   # 100% CHF-hedged S&P total return

def cycle(C=35, B=150, sell_months=12, floor=0.0, trend_confirm=False, wait_cap=None,
          cps=CP_DEFAULT, s=S0, e=None, log=False):
    e = len(p)-1 if e is None else e
    units = 1/eqH[s]; cash = 0.0; mode = 'inv'; step = 0; sold_since = None
    dep = None; hist = []; peak_p = ath[s]; peak_i = s
    for i in range(s, e+1):
        if i > s: cash *= cash_m[i]
        if p[i] >= ath[i]: peak_p, peak_i = p[i], i
        eqv = units*eqH[i]; tot = eqv + cash; w = eqv/tot
        # ---- SELL: valuation (and optionally trend) says expensive ----
        sell_sig = cape[i] >= C and bi[i] >= B and (not trend_confirm or p[i] < ma10[i])
        if dep is None and sell_sig and w > floor + 1e-6:
            if mode != 'sell': mode = 'sell'; step = tot/sell_months
            amt = min(step, eqv - floor*tot); units -= amt/eqH[i]; cash += amt; sold_since = i
        elif mode == 'sell' and not sell_sig: mode = 'inv'
        # ---- BUY: crash deployment of the cash pile ----
        if dep is None and cash > 0.01*tot:
            c0 = cape[peak_i]
            trig, months, first = (0.30,48,0.10) if c0>=35 else (0.25,42,0.15) if c0>=25 else (0.20,36,0.15)
            crash = p[i]/peak_p - 1 <= -trig
            capped = wait_cap and sold_since is not None and i - sold_since >= wait_cap and not sell_sig
            if crash or capped:
                a = cash*first; units += a/eqH[i]; cash -= a
                dep = dict(t=i, M=cash/months, bank=0, done={c for c in cps if c <= trig+1e-9} if crash else set(cps),
                           ref=peak_p, dl=36 if crash else 24, trend=crash)
                mode = 'dep'
        elif dep is not None:
            k = i - dep['t']
            for c, f in cps.items():
                if c not in dep['done'] and p[i]/dep['ref'] - 1 <= -c:
                    dep['done'].add(c); a = cash*f; units += a/eqH[i]; cash -= a
            dep['bank'] += dep['M']
            if (not dep['trend']) or p[i] > ma10[i] or k >= dep['dl']:
                a = min(dep['bank'], cash); units += a/eqH[i]; cash -= a; dep['bank'] = 0
            if k >= dep['dl'] or cash < 1e-9:
                units += cash/eqH[i]; cash = 0; dep = None; mode = 'inv'; sold_since = None
        tot = units*eqH[i] + cash
        hist.append((dates[i], tot, units*eqH[i]/tot, mode))
    return pd.DataFrame(hist, columns=['date','value','w_eq','mode'])

def stats(df):
    v = df.value.values; yrs_ = (len(v)-1)/12
    cagr = v[-1]**(1/yrs_) - 1; mdd = (v/np.maximum.accumulate(v) - 1).min()
    return dict(cagr=100*cagr, maxdd=100*mdd, cash_share=100*(1-df.w_eq).mean())

def bh(eq, s=S0, e=None):
    e = len(p)-1 if e is None else e
    v = eq[s:e+1]/eq[s]; return pd.DataFrame(dict(date=dates[s:e+1].values, value=v, w_eq=1.0, mode='inv'))

def target_w(i, bands=((30,0.8),(35,0.65),(40,0.5)), B=140):
    """graduated equity target: only de-risk when BOTH CAPE and Buffett indicator are high"""
    if bi[i] < B: return 1.0
    w = 1.0
    for c, tw in bands:
        if cape[i] >= c: w = tw
    return w

def glide(bands=((30,0.8),(35,0.65),(40,0.5)), B=140, speed=12, cps=CP_DEFAULT, s=S0, e=None):
    """Graduated version: drift toward valuation target (sell AND buy back slowly), crash rule deploys the cash."""
    e = len(p)-1 if e is None else e
    units = 1/eqH[s]; cash = 0.0; dep = None; hist = []; peak_p = ath[s]; peak_i = s
    for i in range(s, e+1):
        if i > s: cash *= cash_m[i]
        if p[i] >= ath[i]: peak_p, peak_i = p[i], i
        eqv = units*eqH[i]; tot = eqv+cash; w = eqv/tot; tw = target_w(i, bands, B)
        if dep is None:
            c0 = cape[peak_i]
            trig, months, first = (0.30,48,0.10) if c0>=35 else (0.25,42,0.15) if c0>=25 else (0.20,36,0.15)
            if cash > 0.01*tot and p[i]/peak_p - 1 <= -trig:
                a = cash*first; units += a/eqH[i]; cash -= a
                dep = dict(t=i, M=cash/months, bank=0, done={c for c in cps if c <= trig+1e-9}, ref=peak_p)
            else:
                gap = (tw - w)*tot                                   # + buy, - sell
                amt = np.sign(gap)*min(abs(gap), tot/speed)
                if abs(gap) > 0.01*tot:
                    amt = max(-units*eqH[i], min(amt, cash)); units += amt/eqH[i]; cash -= amt
        else:
            k = i - dep['t']
            for c, f in cps.items():
                if c not in dep['done'] and p[i]/dep['ref'] - 1 <= -c:
                    dep['done'].add(c); a = cash*f; units += a/eqH[i]; cash -= a
            dep['bank'] += dep['M']
            if p[i] > ma10[i] or k >= 36:
                a = min(dep['bank'], cash); units += a/eqH[i]; cash -= a; dep['bank'] = 0
            if k >= 36 or cash < 1e-9:
                units += cash/eqH[i]; cash = 0; dep = None
        tot = units*eqH[i]+cash
        hist.append((dates[i], tot, units*eqH[i]/tot, 'dep' if dep else 'inv'))
    return pd.DataFrame(hist, columns=['date','value','w_eq','mode'])
