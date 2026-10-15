exec(open('portfolio.py').read())
RULES = {'R1': (35,140,False,0.0), 'R3': (35,140,False,0.5), 'R4': (30,120,True,0.5)}
idx = lambda d: int(np.where(D == pd.Timestamp(d))[0][0])
EPS = [('2000-03-01','2003-03-01'),('2000-03-01','2010-03-01'),('2007-10-01','2010-10-01'),('2021-01-01','2026-08-01')]
rows = []; RUNS = {}
for h in (0.0, 0.5, 1.0):
    configs = [('Buy & hold', dict(mode='bh'))] + \
              [(f'{r} (US sleeve)', dict(mode='cycle', rule=RULES[r], sell_scope='US')) for r in RULES] + \
              [(f'{r} (all sleeves)', dict(mode='cycle', rule=RULES[r], sell_scope='all')) for r in ('R3','R4')]
    for name, kw in configs:
        v, parts = portfolio(h, **kw); RUNS[(h, name)] = (v, parts); st = stats(v)
        seg = {f'{a[:4]}-{b[:4]}': round(100*(v[idx(b)]/v[idx(a)]-1)) for a, b in EPS}
        eqw = sum(parts[k][-1] for k in parts)  # placeholder
        rows.append(dict(hedge=int(100*h), strategy=name, cagr=round(st['cagr'],2), maxdd=round(st['maxdd']), **seg))
T = pd.DataFrame(rows); print(T.to_string()); T.to_csv('port_cycle.csv', index=False)
import pickle; pickle.dump(RUNS, open('port_runs.pkl','wb'))
# rolling 10y: crash-buy from cash vs buy & hold
H = 120; roll = []
for h in (0.0, 0.5, 1.0):
    for s in range(0, N-H, 3):
        st, _ = portfolio(h, s=s, e=s+H, mode='crash'); bh, _ = portfolio(h, s=s, e=s+H, mode='bh')
        roll.append(dict(hedge=int(100*h), start=D[s], strat=100*(st[-1]**0.1-1), bh=100*(bh[-1]**0.1-1)))
R = pd.DataFrame(roll); R.to_csv('port_roll.csv', index=False)
print(R.groupby('hedge').apply(lambda g: pd.Series(dict(strat=g.strat.mean(), bh=g.bh.mean(), lag=100*(g.strat<g.bh).mean(),
      loss_s=100*(g.strat<0).mean(), loss_b=100*(g.bh<0).mean()))).round(1))
