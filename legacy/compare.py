exec(open('portfolio2.py').read())
import pickle
res = {}
# (1) single start 1971
v_lump, _, _ = portfolio2(1.0, mode='bh')
v_cyc, Hc, _ = portfolio2(1.0, mode='cycle')
v_crash, Hk, _ = portfolio2(1.0, mode='crash')
avg_w = (Hc[:,0]/v_cyc).mean()
v_reb = rebal_mix(1.0, 1.0); v_rm = rebal_mix(1.0, round(avg_w, 2))
def ulcer(v): dd = v/np.maximum.accumulate(v)-1; return 100*np.sqrt((dd**2).mean())
def under(v): dd = v/np.maximum.accumulate(v)-1; return (dd < -0.0001).mean()*100
def vol(v): r = v[1:]/v[:-1]-1; return 100*r.std()*np.sqrt(12)
rows = []
for n, v in [('Lump sum, buy & hold', v_lump), ('Lump sum, rebalanced yearly', v_reb),
             (f'Static {int(round(avg_w*100))}% stocks / rest reserve', v_rm), ('Full cycle (sell + crash-buy)', v_cyc),
             ('Crash-buy only (start in reserve)', v_crash)]:
    st = stats(v); rows.append(dict(strategy=n, cagr=round(st['cagr'],2), maxdd=round(st['maxdd']), vol=round(vol(v),1),
                                    ulcer=round(ulcer(v),1), pct_time_under=round(under(v))))
S = pd.DataFrame(rows); print(S.to_string()); print('avg equity weight full cycle', round(avg_w,3))
res['single'] = S; res['paths'] = dict(lump=v_lump, reb=v_reb, cyc=v_cyc, crash=v_crash, Hc=Hc)
# (2) rolling 10y starts
H = 120; R = []
for s in range(0, N-H):
    l, _, _ = portfolio2(1.0, s=s, e=s+H, mode='bh')
    c, _, _ = portfolio2(1.0, s=s, e=s+H, mode='cycle')
    k, _, _ = portfolio2(1.0, s=s, e=s+H, mode='crash')
    f = lambda v: 100*(v[-1]**(12/H)-1); dd = lambda v: 100*(v/np.maximum.accumulate(v)-1).min()
    R.append(dict(start=D[s], lump=f(l), cycle=f(c), crash=f(k), dd_lump=dd(l), dd_cycle=dd(c), dd_crash=dd(k)))
R = pd.DataFrame(R); res['roll'] = R
summ = pd.DataFrame({n: dict(avg=R[n].mean(), median=R[n].median(), worst=R[n].min(), loss_share=100*(R[n]<0).mean(),
                             beat_lump=100*(R[n]>R['lump']).mean(), median_maxdd=R['dd_'+n].median(), worst_maxdd=R['dd_'+n].min())
                     for n in ['lump','cycle','crash']}).T.round(1)
print(summ); res['roll_summ'] = summ
pickle.dump(res, open('compare.pkl','wb'))
