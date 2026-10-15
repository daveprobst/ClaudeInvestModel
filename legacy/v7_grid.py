exec(open('portfolio4.py').read())
import pickle, itertools
idx = lambda d: int(np.where(D == pd.Timestamp(d))[0][0])
def ulcer(v): dd = v/np.maximum.accumulate(v)-1; return 100*np.sqrt((dd**2).mean())
def epdd(v, a, b): x = v[idx(a):idx(b)+1]; return 100*(x/np.maximum.accumulate(x)-1).min()
WINS = {'25y': 300, '35y': 420, '50y': 600, 'all': None}
vl, *_ = portfolio4(mode='bh'); rows = []
for (wn, win), q in itertools.product(WINS.items(), (0.85, 0.90, 0.95)):
    log = []; v, Ht, parts, states, costs = portfolio4(win=win, q=q, log=log)
    L = pd.DataFrame(log); n_sw = (L.event == 'reached 0% stocks').sum() if len(L) else 0
    out_share = np.mean([np.mean([x in ('OUT','SELLING') for x in states[k]]) for k in W])
    rows.append(dict(window=wn, q=q, cagr=stats(v)['cagr'], vs_lump=stats(v)['cagr']-stats(vl)['cagr'], maxdd=stats(v)['maxdd'],
                     ulcer=ulcer(v), dd00=epdd(v,'2000-01-01','2003-12-01'), dd08=epdd(v,'2007-01-01','2009-12-01'),
                     r21=100*(v[-1]/v[idx('2021-01-01')]-1), stocks_now=100*Ht[-1,0]/v[-1], switches=n_sw, time_out=100*out_share,
                     now=' '.join(f"{k}:{states[k][-1]}" for k in W)))
G = pd.DataFrame(rows); pd.set_option('display.width', 250); print(G.round(2).to_string())
print('lump', {k: round(x,2) for k,x in stats(vl).items()}, 'ulcer', round(ulcer(vl),1), 'r21', round(100*(vl[-1]/vl[idx('2021-01-01')]-1)))
G.to_csv('v7_grid.csv', index=False)
