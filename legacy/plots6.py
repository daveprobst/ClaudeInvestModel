exec(open('portfolio3.py').read())
import pickle, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, seaborn as sns
sns.set_theme(style='whitegrid', context='notebook', font_scale=0.95); pal = sns.color_palette('deep')
OUT = '/mnt/user-data/outputs/'; X = pickle.load(open('v6.pkl','rb')); PATHS = X['PATHS']
names = list(PATHS)

# ---- Fig 17: the log switch ----
fig = plt.figure(figsize=(12,7.5)); gs = fig.add_gridspec(2, 3, height_ratios=[1,1.2])
a0 = fig.add_subplot(gs[0,0]); t = np.arange(0, 13)
a0.plot(t, [100] + [max(50, 100 - 100*m/12) for m in t[1:]], color=pal[0], lw=2, marker='o', ms=3, label='Gradual (old): 1/12 per month, floor 50%')
a0.plot(t, [100] + [100*(1-log_path(m)) for m in t[1:]], color=pal[3], lw=2, marker='o', ms=3, label='Log switch (new): floor 0%, T=6, k=30')
a0.set_xlabel('Months after the sell signal'); a0.set_ylabel('Stocks in the block (%)'); a0.set_title('Sell transition', fontsize=10); a0.legend(fontsize=7)
a1 = fig.add_subplot(gs[0,1:])
for n, c in [(names[1], pal[0]), (names[2], pal[3])]:
    v, Ht = PATHS[n]; a1.plot(D, 100*Ht[:,0]/v, color=c, lw=1.8, label=n.split('  ')[0] + ': ' + n.split('  ')[1])
a1.set_ylabel('Stocks, % of portfolio'); a1.set_title('Same signals (US CAPE + Buffett + trend on all blocks), different transition', fontsize=10); a1.legend(fontsize=7, loc='lower left')
a2 = fig.add_subplot(gs[1,:]); v, Ht = PATHS[names[4]]; sh = Ht/v[:,None]*100
a2.stackplot(D, sh[:,0], sh[:,1], sh[:,2], colors=[pal[0], pal[1], pal[8]], labels=['Stocks','CHF govt bonds','CHF cash'], alpha=.85)
a2.set_ylim(0,100); a2.set_ylabel('% of portfolio'); a2.legend(fontsize=8, loc='lower left', ncol=3)
a2.set_title('Model D (per-market signals + log switch): what the portfolio held', fontsize=10)
plt.tight_layout(); plt.savefig(OUT+'17_log_switch.png', dpi=150); plt.close()

# ---- Fig 18: per-market signals ----
fig, ax = plt.subplots(3,1,figsize=(11,8.5),sharex=True)
ax[0].plot(D, CAPE, color='k', lw=1.3, label='US CAPE'); ax[0].axhline(30, color=pal[3], ls='--', lw=1, label='CAPE ≥ 30')
a0b = ax[0].twinx(); a0b.plot(D, BI, color=pal[0], lw=1.3, label='US Buffett proxy (%)'); a0b.axhline(120, color=pal[0], ls=':', lw=1, label='Buffett ≥ 120%'); a0b.grid(False)
on = (CAPE>=30)&(BI>=120); ax[0].fill_between(D, 0, 50, where=on, color=pal[3], alpha=.12, step='mid')
ax[0].set_ylim(0,50); ax[0].set_title('US: sell zone = CAPE ≥ 30 AND Buffett ≥ 120% (shaded), then only while S&P < 10-month avg', fontsize=10)
h1,l1 = ax[0].get_legend_handles_labels(); h2,l2 = a0b.get_legend_handles_labels(); ax[0].legend(h1+h2, l1+l2, fontsize=7, loc='upper left', ncol=4)
for a_, k, nm in [(ax[1],'EU','Europe'), (ax[2],'CH','Switzerland')]:
    a_.plot(D, 100*PCT[k], color='k', lw=1.3, label=f'{nm}: price/GDP percentile vs own history since 1971')
    a_.axhline(90, color=pal[3], ls='--', lw=1, label='90th percentile')
    a_.fill_between(D, 0, 100, where=np.nan_to_num(PCT[k])>=0.9, color=pal[3], alpha=.12, step='mid')
    a_.set_ylim(0,102); a_.set_ylabel('percentile'); a_.legend(fontsize=7, loc='lower right'); a_.set_title(f'{nm}: sell zone = own valuation ≥ 90th pct (shaded), then only while index < 10-month avg', fontsize=10)
plt.tight_layout(); plt.savefig(OUT+'18_per_market_signals.png', dpi=150); plt.close()

# ---- Fig 19: results ----
fig, ax = plt.subplots(2,1,figsize=(11,7.5),sharex=True,gridspec_kw=dict(height_ratios=[3,2]))
cols = ['grey', pal[0], pal[3], pal[1], pal[2]]; lss = ['-', '--', ':', '-.', '-']
vl = PATHS[names[0]][0]
for n, c, ls in zip(names, cols, lss):
    v = PATHS[n][0]; ax[0].plot(D, v, color=c, ls=ls, lw=3 if n==names[0] else 1.9, label=f"{n} ({stats(v)['cagr']:.1f}%/yr, worst {stats(v)['maxdd']:.0f}%)")
    if n != names[0]: ax[1].plot(D, 100*(v/vl-1), color=c, ls=ls, lw=1.9)
ax[0].set_yscale('log'); ax[0].legend(fontsize=7, loc='upper left'); ax[0].set_ylabel('Growth of CHF 1 (log)')
ax[0].set_title('30/30/40, US+EU hedged, reserve 50% CHF bonds / 50% CHF cash, 0.1% costs')
ax[1].axhline(0, color='k', lw=.8); ax[1].set_ylabel('vs lump sum (%)')
plt.tight_layout(); plt.savefig(OUT+'19_v6_results.png', dpi=150); plt.close()

# ---- Fig 20: robustness of model D ----
S = []
for pct in (0.80, 0.85, 0.90, 0.95):
    EU_CH_PCT = pct
    for T_ in (3, 6, 12):
        v, _, _ = portfolio3(1.0, mode='cycle', decoupled=True, shape='log', floor=0.0, T=T_)
        dd = v/np.maximum.accumulate(v)-1
        S.append(dict(pct=int(pct*100), T=T_, cagr=stats(v)['cagr']-stats(vl)['cagr'], ulcer=100*np.sqrt((dd**2).mean())))
S = pd.DataFrame(S); fig, ax = plt.subplots(1,2,figsize=(11,3.8))
sns.heatmap(S.pivot(index='pct', columns='T', values='cagr'), annot=True, fmt='+.2f', cmap='RdYlGn', center=0, ax=ax[0], cbar=False)
ax[0].set_title('Model D: return vs lump sum (%/yr)', fontsize=10); ax[0].set_ylabel('Europe/Swiss sell percentile'); ax[0].set_xlabel('Log-switch length T (months)')
sns.heatmap(S.pivot(index='pct', columns='T', values='ulcer'), annot=True, fmt='.1f', cmap='RdYlGn_r', ax=ax[1], cbar=False)
ax[1].set_title('Model D: ulcer index (lump sum = 14.9)', fontsize=10); ax[1].set_ylabel(''); ax[1].set_xlabel('Log-switch length T (months)')
plt.tight_layout(); plt.savefig(OUT+'20_modelD_robustness.png', dpi=150); plt.close()
