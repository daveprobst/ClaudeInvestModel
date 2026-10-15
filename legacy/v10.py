exec(open('v9.py').read().split('ulcer = lambda')[0])          # data + V5 definitions
ulcer = lambda v: 100*np.sqrt(((v/np.maximum.accumulate(v)-1)**2).mean())
epdd = lambda v,a,b: 100*(v[idx(a):idx(b)+1]/np.maximum.accumulate(v[idx(a):idx(b)+1])-1).min()
WIN = 240
VL20 = {k: roll_pct(cape_full, WIN)[iu] if k=='US' else roll_pct(VAL[k], WIN) for k in W}
FIRE20 = {k: np.nan_to_num(VL20[k]) >= .9 for k in W}; FORCE20 = sum(FIRE20[k].astype(int) for k in W) >= 2
def run_v6(s=0, e=None, tc=0.001, cooldown=12, log=None):
    """joint engine: sell all when >=2 markets fire; buy back all when >=2 markets are buy-ready"""
    e = N-1 if e is None else e
    EQ = {k: sleeve_index(k, 0.0 if k=='CH' else 1.0) for k in W}; RG = {k: reserve_growth(k) for k in W}
    u = {k: 1/EQ[k][s] for k in W}; r = {k: 0.0 for k in W}; st = {k: 'IN' for k in W}; ctx = {k: {} for k in W}
    pk = {k: (ATH[k][s], int(np.where(PRICE[k][:s+1]==ATH[k][s])[0][-1])) for k in W}; cool = s
    H = {k: np.zeros((e-s+1,2)) for k in W}; S = {k: [] for k in W}
    rec = lambda i,k,x: log.append(dict(date=D[i], block=k, event=x)) if log is not None else None
    def buy(i,k,a): a=min(a,r[k]); u[k]+=a*(1-tc)/EQ[k][i]; r[k]-=a
    def depth(k):
        v = VL20[k][pk[k][1]]
        return (0.30,48,0.10) if v>=.9 else (0.25,42,0.15) if v>=.75 else (0.20,36,0.15)
    for i in range(s, e+1):
        for k in W:
            if i > s: r[k] *= RG[k][i]
            if PRICE[k][i] >= pk[k][0]: pk[k] = (PRICE[k][i], i)
        # ---- SELL: majority fired -> every invested block sells 100% at once ----
        if FORCE20[i] and i >= cool and any(st[k]=='IN' for k in W):
            for k in W:
                if st[k]=='IN': a=u[k]*EQ[k][i]; r[k]+=a*(1-tc); u[k]=0.0; st[k]='OUT'; rec(i,k,'SELL (2-of-3 fired)')
        # ---- BUY: majority buy-ready -> all OUT blocks start buying ----
        if all(st[k]=='OUT' for k in W):
            crash = {k: PRICE[k][i]/pk[k][0]-1 <= -depth(k)[0] for k in W}
            clear = {k: np.nan_to_num(VL20[k][i], nan=1) < .70 and PRICE[k][i] > MA[k][i] and not FORCE20[i] for k in W}
            if sum(crash[k] or clear[k] for k in W) >= 2:
                for k in W:
                    trig, months, first = depth(k)
                    if clear[k] and not crash[k]:
                        st[k]='REENTRY'; ctx[k]=dict(t=i, M=r[k]/24); rec(i,k,'BUY start: all-clear')
                    else:
                        buy(i,k,r[k]*first); st[k]='DEPLOY'
                        ctx[k]=dict(t=i, M=r[k]/months, bank=0.0, ref=pk[k][0], done={c for c in CP if c<=trig+1e-9})
                        rec(i,k,f'BUY start: crash program (own drop {100*(PRICE[k][i]/pk[k][0]-1):.0f}%)')
        for k in W:
            if st[k]=='DEPLOY':
                c_=ctx[k]; kk=i-c_['t']
                for c,f in CP.items():
                    if c not in c_['done'] and PRICE[k][i]/c_['ref']-1 <= -c: c_['done'].add(c); buy(i,k,r[k]*f)
                c_['bank'] += c_['M']
                if PRICE[k][i] > MA[k][i] or kk >= 36: buy(i,k,c_['bank']); c_['bank']=0.0
                if kk >= 36 or r[k] < 1e-12: buy(i,k,r[k]); st[k]='IN'; cool=max(cool,i+cooldown); rec(i,k,'fully re-invested')
            elif st[k]=='REENTRY':
                buy(i,k,ctx[k]['M'])
                if i-ctx[k]['t'] >= 23 or r[k] < 1e-12: buy(i,k,r[k]); st[k]='IN'; cool=max(cool,i+cooldown); rec(i,k,'fully re-invested')
            H[k][i-s] = (u[k]*EQ[k][i], r[k]); S[k].append(st[k])
    parts = {k: W[k]*H[k] for k in W}; Ht = sum(parts.values()); return Ht.sum(1), Ht, parts, S
vl = portfolio4(mode='bh')[0]; v1, H1, p1, s1, _ = portfolio5(win=300, q=0.90, contagion=True); v5, H5, p5, s5 = run_v5()
log = []; v6, H6, p6, s6 = run_v6(log=log); L = pd.DataFrame(log)
print(L[~L.event.str.contains('fully')].assign(date=lambda x: x.date.dt.strftime('%Y-%m')).groupby(['date','event']).block.apply(','.join).to_string())
MOD = [('Lump sum', vl, None, 'grey', '-'), ('V2 (25y, val+trend)', v1, H1, pal[2], '-'), ('V5 (25y|50y, 1-day)', v5, H5, pal[3], '--'), ('V6 new (20y, 2-of-3 sell & buy)', v6, H6, pal[0], '-')]
print(pd.DataFrame([dict(model=n, cagr=stats(v)['cagr'], maxdd=stats(v)['maxdd'], ulcer=ulcer(v), dd00=epdd(v,'2000-01-01','2003-12-01'),
      dd08=epdd(v,'2007-01-01','2009-12-01'), r21=100*(v[-1]/v[idx('2021-01-01')]-1), stocks_now=100 if Ht is None else 100*Ht[-1,0]/v[-1]) for n,v,Ht,_,_ in MOD]).round(2).to_string())
R = {'lump': [], 'V2': [], 'V5': [], 'V6': []}
for s in range(0, N-120, 3):
    R['lump'].append(100*(portfolio4(s=s, e=s+120, mode='bh')[0][-1]**0.1-1)); R['V2'].append(100*(portfolio5(s=s, e=s+120, win=300, q=0.90)[0][-1]**0.1-1))
    R['V5'].append(100*(run_v5(s=s, e=s+120)[0][-1]**0.1-1)); R['V6'].append(100*(run_v6(s=s, e=s+120)[0][-1]**0.1-1))
R = pd.DataFrame(R); print(pd.DataFrame({n: dict(avg=R[n].mean(), worst=R[n].min(), better=100*(R[n]-R.lump>0.05).mean(), worse=100*(R[n]-R.lump<-0.05).mean()) for n in R}).T.round(1))
print('fired now (20y):', {k: round(float(VL20[k][-1]),2) for k in W})
# ---- Fig 26: V6 switches ----
SC = {'OUT': pal[3], 'DEPLOY': pal[2], 'REENTRY': pal[4]}; CNT20 = sum(FIRE20[k].astype(int) for k in W)
fig, ax = plt.subplots(4,1,figsize=(11,10),sharex=True,gridspec_kw=dict(height_ratios=[1,2,2,2]))
ax[0].step(D, CNT20, 'k', where='mid'); ax[0].axhline(1.5, color=pal[3], ls='--'); ax[0].set_yticks([0,1,2,3]); ax[0].set_title('Markets ≥90th pct of previous 20 years (sell all when ≥2)', fontsize=10)
for a_, k in zip(ax[1:], W):
    P = PRICE[k]; S_ = np.array(s6[k]); a_.plot(D, P/P[0], 'k', lw=1.1); a_.set_yscale('log')
    for x, c in SC.items(): a_.fill_between(D, 0, 1, where=S_==x, color=c, alpha=.35, step='mid', transform=a_.get_xaxis_transform())
    b = a_.twinx(); b.plot(D, 100*p6[k][:,0]/p6[k].sum(1), color=pal[0], lw=1.5); b.set_ylim(-3,103); b.grid(False); b.set_ylabel('stocks %')
    a_.set_title({'US':'S&P 500 (→ US Treasuries)','EU':'Europe (→ German Bunds)','CH':'SPI (→ CHF cash)'}[k], fontsize=10)
ax[1].legend(handles=[Patch(color=SC[x], alpha=.5, label=l) for x,l in [('OUT','100% reserve'),('DEPLOY','crash buy-back'),('REENTRY','all-clear re-entry')]], fontsize=7, loc='upper left')
plt.tight_layout(); plt.savefig(OUT+'26_v6_switches.png', dpi=150); plt.close()
# ---- Fig 27: comparison ----
fig, ax = plt.subplots(3,1,figsize=(11,9),sharex=True,gridspec_kw=dict(height_ratios=[3,2,2]))
for n, v, _, c, ls in MOD:
    ax[0].plot(D, v, color=c, ls=ls, lw=2.5 if n=='Lump sum' else 1.6, label=f"{n} ({stats(v)['cagr']:.2f}%/yr, worst {stats(v)['maxdd']:.0f}%)")
    if n != 'Lump sum': ax[1].plot(D, 100*(v/vl-1), color=c, ls=ls, lw=1.6, label=n)
    ax[2].plot(D, 100*(v/np.maximum.accumulate(v)-1), color=c, ls=ls, lw=1.2)
ax[0].set_yscale('log'); ax[0].legend(fontsize=8, loc='upper left'); ax[0].set_title('30/30/40, US+EU hedged', fontsize=10)
ax[1].axhline(0, color='k', lw=.8); ax[1].set_ylabel('vs lump sum %'); ax[1].legend(fontsize=8); ax[2].set_ylabel('drawdown %')
plt.tight_layout(); plt.savefig(OUT+'27_v6_comparison.png', dpi=150); plt.close()
