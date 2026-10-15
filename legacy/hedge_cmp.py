exec(open('model3.py').read())
def mix(h):
    r = h*(tr_hedged[1:]/tr_hedged[:-1]) + (1-h)*(tr_chf[1:]/tr_chf[:-1])   # monthly-rebalanced hedge ratio
    return np.cumprod(np.r_[1, r])
EQ = {h: mix(h) for h in (0.0, 0.5, 1.0)}
R = {'R1': dict(C=35,B=140), 'R3': dict(C=35,B=140,floor=0.5), 'R4': dict(C=30,B=120,trend_confirm=True,floor=0.5)}
def seg(df,a,b):
    v=df.set_index('date').value; return 100*(v[pd.Timestamp(b)]/v[pd.Timestamp(a)]-1)
EPS=[('2000-03-01','2003-03-01'),('2000-03-01','2010-03-01'),('2007-10-01','2010-10-01'),('2021-01-01','2026-08-01')]
rows=[]; RUNS={}
for h,eq in EQ.items():
    eqH = eq                                  # cycle() reads the global eqH
    for n,k in [('Buy & hold',None)]+list(R.items()):
        df = bh(eq) if k is None else cycle(**k, wait_cap=36)
        RUNS[(h,n)] = df; st = stats(df)
        rows.append(dict(hedge=int(h*100), strat=n, cagr=st['cagr'], maxdd=st['maxdd'], **{f'{a[:4]}-{b[:4]}':seg(df,a,b) for a,b in EPS}))
T = pd.DataFrame(rows); print(T.round(1).to_string())
T.to_csv('hedge_table.csv', index=False)
import pickle; pickle.dump(RUNS, open('hedge_runs.pkl','wb'))
