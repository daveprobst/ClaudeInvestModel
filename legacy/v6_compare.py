exec(open('portfolio3.py').read())
import pickle, time
V = {'Lump sum (buy & hold)':      dict(mode='bh'),
     'A  R4, US signal on all, gradual to 50%':  dict(mode='cycle'),
     'B  R4, US signal on all, log switch to 0%': dict(mode='cycle', shape='log', floor=0.0),
     'C  Per-market signals, gradual to 50%':     dict(mode='cycle', decoupled=True),
     'D  Per-market signals, log switch to 0%':   dict(mode='cycle', decoupled=True, shape='log', floor=0.0)}
def ulcer(v): dd = v/np.maximum.accumulate(v)-1; return 100*np.sqrt((dd**2).mean())
def vol(v): r = v[1:]/v[:-1]-1; return 100*r.std()*np.sqrt(12)
idx = lambda d: int(np.where(D == pd.Timestamp(d))[0][0])
def epdd(v, a, b): x = v[idx(a):idx(b)+1]; return 100*(x/np.maximum.accumulate(x)-1).min()
rows, PATHS = [], {}
for n, kw in V.items():
    v, Ht, parts = portfolio3(1.0, **kw); PATHS[n] = (v, Ht)
    st = stats(v); tc = sum(c.sum() for c in COSTS3.values()) if kw['mode'] != 'bh' else 0
    rows.append(dict(model=n, cagr=st['cagr'], maxdd=st['maxdd'], vol=vol(v), ulcer=ulcer(v),
                     dd_2000_03=epdd(v,'2000-01-01','2003-12-01'), dd_2007_09=epdd(v,'2007-01-01','2009-12-01'),
                     dd_2020=epdd(v,'2020-01-01','2020-12-01'), dd_2022=epdd(v,'2021-10-01','2022-12-01'),
                     r_2021_26=100*(v[-1]/v[idx('2021-01-01')]-1), eq_now=100*Ht[-1,0]/v[-1], avg_eq=100*(Ht[:,0]/v).mean()))
T = pd.DataFrame(rows).round(1); pd.set_option('display.width', 250); print(T.to_string())
H = 120; R = {n: [] for n in V}
for s in range(0, N-H):
    for n, kw in V.items():
        v, _, _ = portfolio3(1.0, s=s, e=s+H, **kw); R[n].append(100*(v[-1]**(12/H)-1))
R = pd.DataFrame(R, index=D[:N-H]); L = R['Lump sum (buy & hold)']
RS = pd.DataFrame({n: dict(avg=R[n].mean(), worst=R[n].min(), loss=100*(R[n]<0).mean(),
                           better=100*(R[n]-L>0.05).mean(), worse=100*(R[n]-L<-0.05).mean()) for n in V}).T.round(1)
print(RS)
pickle.dump(dict(T=T, RS=RS, R=R, PATHS=PATHS), open('v6.pkl','wb'))
