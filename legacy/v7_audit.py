exec(open('portfolio4.py').read())
CFG = dict(win=300, q=0.90)
log = []; v, Ht, parts, states, costs = portfolio4(log=log, **CFG); L = pd.DataFrame(log)
checks = []
for k in W:
    eq = sleeve_index(k, 0.0 if k=='CH' else 1.0); rg = reserve_growth(k); Hk = parts[k]; Sk = np.array(states[k])
    pre = Hk[:-1,0]*eq[1:]/eq[:-1] + Hk[:-1,1]*rg[1:]
    err = np.abs(pre - Hk[1:].sum(1) - costs[k][1:]).max()
    checks.append((k, 'value conserved every month (net of 0.1% costs)', err < 1e-12, f'max err {err:.1e}'))
    w = Hk[:,0]/Hk.sum(1)
    trig = L[(L.block==k)&(L.event=='SELL TRIGGER')].date; done = L[(L.block==k)&(L.event=='reached 0% stocks')].date
    ok = len(trig) == len(done) and all((d2.year-d1.year)*12 + d2.month-d1.month == 5 for d1, d2 in zip(trig, done))
    checks.append((k, 'every sell trigger reached 0% stocks exactly 5 months later (6th month)', ok, f'{len(trig)} switches'))
    # weight path during SELLING equals the log schedule
    devs = []
    for d1 in trig:
        i0 = int(np.where(D==d1)[0][0]); w0 = (Hk[i0-1,0]*eq[i0]/eq[i0-1]) / (Hk[i0-1,0]*eq[i0]/eq[i0-1] + Hk[i0-1,1]*rg[i0])
        for t in range(1, 6): devs.append(abs(w[i0+t-1] - w0*(1-log_path(t))))
    checks.append((k, 'weights followed the log schedule (66/79/87/94/.. % sold)', max(devs, default=0) < 1e-3, f'max dev {max(devs, default=0):.1e}'))
    checks.append((k, 'exactly 0% stocks in every OUT month', bool((Hk[Sk=='OUT',0] == 0).all()), f'{(Sk=="OUT").sum()} OUT months'))
    ex = L[(L.block==k)&L.event.str.startswith(('CRASH','ALL-CLEAR'))]
for c in checks: print('PASS' if c[2] else 'FAIL', c[0], '-', c[1], c[3])
ev = L[L.event.str.contains('TRIGGER|reached|ALL-CLEAR|fully')]
print(ev.to_string(index=False))
V25 = {k: val_level(k, 300, 'pct')[-1] for k in W}
print('Now (Aug 2026): valuation percentile (25y window):', {k: round(float(x),3) for k,x in V25.items()},
      '| index below 10m avg:', {k: bool(PRICE[k][-1] < MA[k][-1]) for k in W}, '| distance to 10m avg %:', {k: round(100*(PRICE[k][-1]/MA[k][-1]-1),1) for k in W})
L.to_csv('v7_trade_log.csv', index=False)
# stronger checks: units only fall inside SELLING months; reserve return equals the block's instrument
for k in W:
    eq = sleeve_index(k, 0.0 if k=='CH' else 1.0); Hk = parts[k]; Sk = np.array(states[k])
    units = Hk[:,0]/eq; dec = np.where(np.diff(units) < -1e-12)[0] + 1
    print('PASS' if all(Sk[i]=='SELLING' for i in dec) else 'FAIL', k, '- stocks only reduced in committed-switch months', len(dec), 'sale months')
    rg = reserve_growth(k); m = np.where((Sk[1:]=='OUT') & (Sk[:-1]=='OUT'))[0] + 1
    err = np.abs(Hk[m,1] - Hk[m-1,1]*rg[m]).max() if len(m) else 0
    print('PASS' if err < 1e-12 else 'FAIL', k, f'- reserve earned exactly the {RES_NAME[k]} return while OUT', f'max err {err:.1e}')
