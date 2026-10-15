exec(open('portfolio5.py').read())
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, seaborn as sns
from matplotlib.patches import Patch
sns.set_theme(style='whitegrid', font_scale=0.95); pal = sns.color_palette('deep'); OUT='/mnt/user-data/outputs/'
idx = lambda d: int(np.where(D == pd.Timestamp(d))[0][0])
# valuation firing per market: >= 90th pct in 25y OR 50y window. US uses CAPE only.
def lvl(k, win): return roll_pct(cape_full, win)[iu] if k == 'US' else roll_pct(VAL[k], win)
FIRE = {k: (np.nan_to_num(lvl(k,300)) >= .9) | (np.nan_to_num(lvl(k,600)) >= .9) for k in W}
CNT = sum(FIRE[k].astype(int) for k in W); FORCE = CNT >= 2
def run_v5(s=0, e=None, log=None):
    e = N-1 if e is None else e; res = {}
    for k in W:
        H_, S_, C_ = run_block(k, s, e, win=300, q=1.01, T=1, force=FORCE, trend=True, log=log)   # q>1: own signal off
        res[k] = (W[k]*H_, S_)
    Ht = sum(r[0] for r in res.values()); return Ht.sum(1), Ht, {k: res[k][0] for k in W}, {k: res[k][1] for k in W}
ulcer = lambda v: 100*np.sqrt(((v/np.maximum.accumulate(v)-1)**2).mean())
epdd = lambda v,a,b: 100*(v[idx(a):idx(b)+1]/np.maximum.accumulate(v[idx(a):idx(b)+1])-1).min()
vl = portfolio4(mode='bh')[0]; v1, H1, p1, s1, _ = portfolio5(win=300, q=0.90, contagion=True)
log = []; v5, H5, p5, s5 = run_v5(log=log); L = pd.DataFrame(log)
print(L[L.event.str.contains('SELL TRIGGER|CRASH|ALL-CLEAR')].assign(date=lambda x: x.date.dt.strftime('%Y-%m'))[['date','block','event']].to_string(index=False))
rows = []
for n, v, Ht in [('Lump sum', vl, None), ('V2 current (val+trend, 6m switch)', v1, H1), ('V5 new (2-of-3, 25y|50y, CAPE only, 1-day switch)', v5, H5)]:
    rows.append(dict(model=n, cagr=stats(v)['cagr'], maxdd=stats(v)['maxdd'], ulcer=ulcer(v), dd00=epdd(v,'2000-01-01','2003-12-01'),
                     dd08=epdd(v,'2007-01-01','2009-12-01'), r21=100*(v[-1]/v[idx('2021-01-01')]-1), stocks_now=100 if Ht is None else 100*Ht[-1,0]/v[-1]))
print(pd.DataFrame(rows).round(2).to_string())
Hh = 120; R = {'lump': [], 'V2': [], 'V5': []}; FORCE0 = FORCE.copy()
for s in range(0, N-Hh, 3):
    R['lump'].append(100*(portfolio4(s=s, e=s+Hh, mode='bh')[0][-1]**0.1-1))
    R['V2'].append(100*(portfolio5(s=s, e=s+Hh, win=300, q=0.90, contagion=True)[0][-1]**0.1-1))
    R['V5'].append(100*(run_v5(s=s, e=s+Hh)[0][-1]**0.1-1))
R = pd.DataFrame(R); print(pd.DataFrame({n: dict(avg=R[n].mean(), worst=R[n].min(), loss=100*(R[n]<0).mean(), better=100*(R[n]-R.lump>0.05).mean(), worse=100*(R[n]-R.lump<-0.05).mean()) for n in R}).T.round(1))
print('markets fired now:', {k: bool(FIRE[k][-1]) for k in W}, '| 2-of-3 active since', D[max(i for i in range(N) if not FORCE[i])+1].strftime('%Y-%m'))
# ---- Fig 24: V5 switches ----
SC = {'OUT': pal[3], 'DEPLOY': pal[2], 'REENTRY': pal[4]}
fig, ax = plt.subplots(4,1,figsize=(11,10),sharex=True,gridspec_kw=dict(height_ratios=[1,2,2,2]))
ax[0].step(D, CNT, color='k', where='mid'); ax[0].axhline(1.5, color=pal[3], ls='--'); ax[0].set_ylim(-.2,3.2); ax[0].set_yticks([0,1,2,3])
ax[0].set_title('Markets at ≥90th pct (25y or 50y window); switch when ≥2 (dashed line)', fontsize=10)
for a_, k in zip(ax[1:], W):
    P = PRICE[k]; S_ = np.array(s5[k]); a_.plot(D, P/P[0], 'k', lw=1.1); a_.set_yscale('log')
    for st_, c in SC.items(): a_.fill_between(D, 0, 1, where=S_==st_, color=c, alpha=.35, step='mid', transform=a_.get_xaxis_transform())
    b = a_.twinx(); b.plot(D, 100*p5[k][:,0]/p5[k].sum(1), color=pal[0], lw=1.5); b.set_ylim(-3,103); b.grid(False); b.set_ylabel('stocks %')
    a_.set_title({'US':'S&P 500 block (→ US Treasuries)','EU':'Europe block (→ German Bunds)','CH':'SPI block (→ CHF cash)'}[k], fontsize=10)
ax[1].legend(handles=[Patch(color=SC[x], alpha=.5, label=l) for x,l in [('OUT','100% reserve'),('DEPLOY','crash buy-back'),('REENTRY','all-clear re-entry')]], fontsize=7, loc='upper left')
plt.tight_layout(); plt.savefig(OUT+'24_v5_switches.png', dpi=150); plt.close()
# ---- Fig 25: comparison ----
fig, ax = plt.subplots(3,1,figsize=(11,9),sharex=True,gridspec_kw=dict(height_ratios=[3,2,2]))
for n, v, c, ls in [('Lump sum', vl, 'grey', '-'), ('V2 current', v1, pal[2], '-'), ('V5 new', v5, pal[3], '--')]:
    ax[0].plot(D, v, color=c, ls=ls, lw=2.5 if n=='Lump sum' else 1.8, label=f"{n} ({stats(v)['cagr']:.2f}%/yr, worst {stats(v)['maxdd']:.0f}%)")
    if n != 'Lump sum': ax[1].plot(D, 100*(v/vl-1), color=c, ls=ls, lw=1.8, label=n)
    ax[2].plot(D, 100*(v/np.maximum.accumulate(v)-1), color=c, ls=ls, lw=1.3, label=n)
ax[0].set_yscale('log'); ax[0].legend(fontsize=8, loc='upper left'); ax[0].set_ylabel('CHF 1 grows to'); ax[0].set_title('30/30/40, US+EU hedged: lump sum vs V2 vs V5', fontsize=10)
ax[1].axhline(0, color='k', lw=.8); ax[1].set_ylabel('vs lump sum %'); ax[1].legend(fontsize=8)
ax[2].set_ylabel('drawdown %'); ax[2].legend(fontsize=8, loc='lower left')
plt.tight_layout(); plt.savefig(OUT+'25_v5_vs_v2.png', dpi=150); plt.close()
