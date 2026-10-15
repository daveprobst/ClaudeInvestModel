exec(open('portfolio3.py').read())
idx = lambda d: int(np.where(D == pd.Timestamp(d))[0][0])
def ulcer(v): dd = v/np.maximum.accumulate(v)-1; return 100*np.sqrt((dd**2).mean())
rows=[]
for pct in (0.80, 0.85, 0.90, 0.95):
    EU_CH_PCT = pct
    for T_ in (3, 6, 12):
        v, Ht, _ = portfolio3(1.0, mode='cycle', decoupled=True, shape='log', floor=0.0, T=T_)
        st = stats(v); rows.append(dict(pct=pct, T=T_, cagr=round(st['cagr'],2), maxdd=round(st['maxdd']), ulcer=round(ulcer(v),1),
                                        r21_26=round(100*(v[-1]/v[idx('2021-01-01')]-1)), eq_now=round(100*Ht[-1,0]/v[-1])))
print(pd.DataFrame(rows).to_string())
EU_CH_PCT = 0.90
# audit D
log=[]; v, Ht, parts = portfolio3(1.0, mode='cycle', decoupled=True, shape='log', floor=0.0, log=log)
ok=True
for k in W:
    eq = sleeve_index(k, 0.0 if k=='CH' else 1.0); Hk = parts[k]
    pre = Hk[:-1,0]*eq[1:]/eq[:-1] + Hk[:-1,1]*bond_g[1:] + Hk[:-1,2]*cash_g[1:]
    err = np.abs(pre - Hk[1:].sum(1) - COSTS3[k][1:]).max(); ok &= err < 1e-9 and (Hk >= -1e-12).all()
    L = pd.DataFrame(log, columns=['date','sleeve','action','amount'])
    sig = signals(k, True); si = [int(np.where(D==d)[0][0]) for d in L[(L.sleeve==k)&(L.action=='sell')].date]
    ok &= all(sig[i] for i in si)
print('audit D passed:', ok)
L = pd.DataFrame(log, columns=['date','sleeve','action','amount'])
ev = L[L.action.isin(['SELL signal on']) | L.action.str.startswith('TRIGGER') | (L.action=='deployment complete')]
print(ev.to_string(index=False))
# how fast is the log switch: equity weight path of US sleeve in 2000
w = parts['US'][:,0]/parts['US'].sum(1); i0 = idx('2000-09-01'); print('US weight Sep2000-Apr2001', np.round(w[i0:i0+8],2))
L.to_csv('trade_log_v6D.csv', index=False)
