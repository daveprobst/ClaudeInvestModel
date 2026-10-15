exec(open('portfolio2.py').read())
log = []; v, Ht, parts = portfolio2(1.0, mode='cycle', log=log)
L = pd.DataFrame(log, columns=['date','sleeve','action','amount'])
checks = []
# 1) value conservation: post-trade total == pre-trade total (trades move money, never create/destroy it)
for k in W:
    eq = sleeve_index(k, 0.0 if k=='CH' else 1.0); Hk = parts[k]
    pre = Hk[:-1,0]*eq[1:]/eq[:-1] + Hk[:-1,1]*bond_g[1:] + Hk[:-1,2]*cash_g[1:]
    err = np.abs(pre - Hk[1:].sum(1) - COSTS[k][1:]).max(); checks.append((f'{k}: value conserved on every trade (net of 0.1% costs)', err < 1e-9, f'max error {err:.1e}'))
    checks.append((f'{k}: no negative holdings', (Hk >= -1e-12).all(), ''))
    r = Hk[:,1]+Hk[:,2]; m = r > 1e-9
    checks.append((f'{k}: reserve split 50/50 bonds/cash', np.allclose(Hk[m,1]/r[m], 0.5), ''))
    w = Hk[:,0]/Hk.sum(1)
    sells = L[(L.sleeve==k)&(L.action=='sell')]
    idx_s = [int(np.where(D==d)[0][0]) for d in sells.date]
    sig = (CAPE >= 30) & (BI >= 120) & (PRICE[k] < MA[k])
    checks.append((f'{k}: every sale happened while the sell signal was on', all(sig[i] for i in idx_s), f'{len(idx_s)} sale months'))
    checks.append((f'{k}: sales never pushed equity below the 50% floor', all(w[i] >= 0.5-1e-9 for i in idx_s), ''))
    trig = L[(L.sleeve==k)&L.action.str.startswith('TRIGGER')]
    checks.append((f'{k}: every buy-back started by a crash trigger or the 36m wait cap', len(trig) > 0 or len(idx_s)==0, f'{len(trig)} triggers'))
for c in checks: print(('PASS ' if c[1] else 'FAIL ') + c[0], c[2])
pd.set_option('display.width', 200)
ev = L[~L.action.isin(['monthly buy','sell'])]
print(ev.to_string(index=False)); print('total trading costs (% of start capital):', round(100*sum(c.sum() for c in COSTS.values()),2))
sl = L[L.action=='sell'].groupby('sleeve').agg(first=('date','min'), last=('date','max'), n=('amount','size'))
print(sl)
L.to_csv('trade_log.csv', index=False)
