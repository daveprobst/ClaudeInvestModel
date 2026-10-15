exec(open('portfolio5.py').read())
idx = lambda d: int(np.where(D == pd.Timestamp(d))[0][0])
ulcer = lambda v: 100*np.sqrt(((v/np.maximum.accumulate(v)-1)**2).mean())
epdd = lambda v,a,b: 100*(v[idx(a):idx(b)+1]/np.maximum.accumulate(v[idx(a):idx(b)+1])-1).min()
# when did each market cross the 90th pct (25y window) most recently?
for k in W:
    lv = np.nan_to_num(val_level(k, 300, 'pct')) >= 0.9; i = N-1
    while i > 0 and lv[i-1]: i -= 1
    blw = [D[j].strftime('%Y-%m') for j in range(i, N) if PRICE[k][j] < MA[k][j]]
    print(k, 'above 90th pct since', D[i].strftime('%Y-%m'), '| months below 10m avg since then:', blw)
CF = {'V1 val+trend (current)': dict(trend=True, contagion=False), 'V2 val+trend + 2-of-3': dict(trend=True, contagion=True),
      'V3 val only': dict(trend=False, contagion=False), 'V4 val only + 2-of-3': dict(trend=False, contagion=True)}
vl, *_ = portfolio4(mode='bh'); rows = []
for n, c in CF.items():
    log = []; v, Ht, parts, st, _ = portfolio5(win=300, q=0.90, log=log, **c); L = pd.DataFrame(log)
    rows.append(dict(model=n, vs_lump=stats(v)['cagr']-stats(vl)['cagr'], maxdd=stats(v)['maxdd'], ulcer=ulcer(v),
                     dd00=epdd(v,'2000-01-01','2003-12-01'), dd08=epdd(v,'2007-01-01','2009-12-01'), r21=100*(v[-1]/v[idx('2021-01-01')]-1),
                     stocks_now=100*Ht[-1,0]/v[-1], switches=(L.event=='reached 0% stocks').sum()))
    if 'V4' in n or 'V2' in n: print(n, L[L.event.str.contains('SELL TRIGGER|CRASH|ALL-CLEAR')].assign(date=lambda x: x.date.dt.strftime('%Y-%m'))[['date','block','event']].to_string(index=False))
T = pd.DataFrame(rows).round(2); print(T.to_string()); print('lump r21', round(100*(vl[-1]/vl[idx('2021-01-01')]-1)))
H = 120; R = {n: [] for n in ['lump'] + list(CF)}
for s in range(0, N-H, 3):
    R['lump'].append(100*(portfolio4(s=s, e=s+H, mode='bh')[0][-1]**0.1-1))
    for n, c in CF.items(): R[n].append(100*(portfolio5(s=s, e=s+H, win=300, q=0.90, **c)[0][-1]**0.1-1))
R = pd.DataFrame(R); L0 = R['lump']
print(pd.DataFrame({n: dict(avg=R[n].mean(), worst=R[n].min(), loss=100*(R[n]<0).mean(), better=100*(R[n]-L0>0.05).mean(), worse=100*(R[n]-L0<-0.05).mean()) for n in R}).T.round(1))
