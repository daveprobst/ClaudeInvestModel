exec(open('portfolio2.py').read())
import pickle; res = pickle.load(open('compare.pkl','rb')); R = res['roll']
for n in ['cycle','crash']:
    d = R[n]-R['lump']; print(n, 'better', round(100*(d>0.05).mean()), 'same', round(100*(d.abs()<=0.05).mean()), 'worse', round(100*(d<-0.05).mean()),
          'avg diff when different', round(d[d.abs()>0.05].mean(),2))
v_l = res['paths']['lump']; v_c = res['paths']['cyc']
# episodes: drawdowns >= 15% of the lump-sum mix (100% hedged)
ath_ = np.maximum.accumulate(v_l); dd_ = v_l/ath_-1
eps = []; i = 0
while i < N:
    if dd_[i] < 0:
        j = i
        while j < N and dd_[j] < 0: j += 1
        if dd_[i:j].min() <= -0.15:
            pk = i-1; tr = i + int(np.argmin(dd_[i:j])); eps.append((pk, tr, j if j < N else None))
        i = j
    else: i += 1
rows = []
for pk, tr, rec in eps:
    end = rec if rec is not None else N-1
    w = slice(pk, end+1)
    cdd = (v_c[w]/np.maximum.accumulate(v_c[w])-1).min()
    # months until each is back above its value at the lump-sum peak
    back = lambda v: next((m for m in range(pk+1, N) if v[m] >= v[pk] and m > tr), None)
    bl, bc = back(v_l), back(v_c)
    # crash-only started in reserve at the peak
    k, _, _ = portfolio2(1.0, s=pk, e=min(N-1, pk+120), mode='crash')
    l, _, _ = portfolio2(1.0, s=pk, e=min(N-1, pk+120), mode='bh')
    g = lambda v, m: round(100*(v[m]-1)) if m < len(v) else None
    rows.append(dict(peak=D[pk].strftime('%Y-%m'), trough=D[tr].strftime('%Y-%m'), dd_lump=round(100*dd_[tr]), dd_cycle=round(100*cdd),
                     rec_lump=None if bl is None else bl-pk, rec_cycle=None if bc is None else bc-pk,
                     peakstart_lump_3y=g(l,36), peakstart_crash_3y=g(k,36), peakstart_lump_5y=g(l,60), peakstart_crash_5y=g(k,60),
                     peakstart_lump_10y=g(l,120), peakstart_crash_10y=g(k,120)))
E = pd.DataFrame(rows); pd.set_option('display.width', 250); print(E.to_string()); E.to_csv('episodes_v5.csv', index=False)
