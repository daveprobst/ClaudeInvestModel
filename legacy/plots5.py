exec(open('portfolio2.py').read())
import pickle, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, seaborn as sns
sns.set_theme(style='whitegrid', context='notebook', font_scale=0.95); pal = sns.color_palette('deep')
OUT = '/mnt/user-data/outputs/'; res = pickle.load(open('compare.pkl','rb')); R = res['roll']; E = pd.read_csv('episodes_v5.csv')
lab = {'lump':'Lump sum, buy & hold','cycle':'Full cycle (sell + crash-buy)','crash':'Crash-buy only (start in reserve)'}
col = {'lump':'grey','cycle':pal[0],'crash':pal[2]}

# ---- Fig 14: rolling 10y vs lump sum ----
fig, ax = plt.subplots(1,2,figsize=(13,4.6),gridspec_kw=dict(width_ratios=[1,1.6]))
m = R.melt(value_vars=['lump','cycle','crash'], var_name='s', value_name='r'); m['s'] = m.s.map(lab)
sns.boxplot(m, x='s', y='r', hue='s', palette=[col[k] for k in lab], ax=ax[0], legend=False, width=.5, fliersize=2)
ax[0].axhline(0,color='k',lw=.8); ax[0].set_xlabel(''); ax[0].set_ylabel('10-year return, %/yr'); ax[0].set_title('All 10-year windows starting 1971–2016', fontsize=10)
ax[0].set_xticks(range(3), ['Lump sum','Full cycle','Crash-buy\nonly'])
for n in ['cycle','crash']:
    ax[1].plot(R.start, (R[n]-R.lump).rolling(6,min_periods=1).mean(), color=col[n], lw=2, label=lab[n])
ax[1].axhline(0,color='k',lw=.8); ax[1].set_ylabel('vs lump sum, %/yr (10y window)'); ax[1].set_title('Difference to lump sum by start date', fontsize=10); ax[1].legend(fontsize=8)
plt.tight_layout(); plt.savefig(OUT+'14_vs_lump_sum.png', dpi=150); plt.close()

# ---- Fig 15: allocation of the full-cycle portfolio ----
log = []; v, Ht, parts = portfolio2(1.0, mode='cycle', log=log); L = pd.DataFrame(log, columns=['date','sleeve','action','amount'])
fig, ax = plt.subplots(2,1,figsize=(11,6.5),sharex=True,gridspec_kw=dict(height_ratios=[2,3]))
share = Ht/v[:,None]*100
ax[0].stackplot(D, share[:,0], share[:,1], share[:,2], colors=[pal[0], pal[1], pal[8]], labels=['Stocks','CHF govt bonds','CHF cash'], alpha=.85)
ax[0].set_ylim(40,100); ax[0].set_ylabel('% of portfolio'); ax[0].legend(fontsize=8, loc='lower left', ncol=3)
ax[0].set_title('Full cycle, 30/30/40, US+EU hedged: what the portfolio held (audit of the mechanics)')
mk = {'US':(pal[0],'o'),'EU':(pal[1],'s'),'CH':(pal[3],'^')}
for k in W:
    eq = sleeve_index(k, 0.0 if k=='CH' else 1.0); P = PRICE[k]
    ax[1].plot(D, P/P[0], color=mk[k][0], lw=1.2, label={'US':'S&P 500','EU':'Europe','CH':'SPI'}[k])
    s_ = L[(L.sleeve==k)&(L.action=='sell')]; t_ = L[(L.sleeve==k)&L.action.str.startswith('TRIGGER')]
    ii = [int(np.where(D==d)[0][0]) for d in s_.date]; jj = [int(np.where(D==d)[0][0]) for d in t_.date]
    ax[1].scatter(D[ii], P[ii]/P[0], color='red', marker='v', s=14, zorder=3)
    ax[1].scatter(D[jj], P[jj]/P[0], color='green', marker=mk[k][1], s=60, zorder=4, edgecolor='k')
ax[1].scatter([],[],color='red',marker='v',label='sale month'); ax[1].scatter([],[],color='green',marker='o',edgecolor='k',label='buy trigger')
ax[1].set_yscale('log'); ax[1].set_ylabel('Index (local, log)'); ax[1].legend(fontsize=8, loc='upper left', ncol=5)
ax[1].set_xlim(pd.Timestamp('1996-01-01'), D[-1]); plt.tight_layout(); plt.savefig(OUT+'15_mechanics_audit.png', dpi=150); plt.close()

# ---- Fig 16: crash types ----
E['label'] = E.peak.str[:4] + '\n' + ['stagflation','flash crash','recession','LTCM/Asia','bubble bust','credit crisis','Covid','rate shock']
fig, ax = plt.subplots(1,2,figsize=(13,4.6))
x = np.arange(len(E)); w = .38
b1 = ax[0].bar(x-w/2, E.dd_lump, w, color='grey', label='Lump sum'); b2 = ax[0].bar(x+w/2, E.dd_cycle, w, color=pal[0], label='Full cycle')
ax[0].bar_label(b1, fontsize=7, padding=2); ax[0].bar_label(b2, fontsize=7, padding=2); ax[0].set_xticks(x, E.label, fontsize=7)
ax[0].set_title('Worst drop in each episode (portfolio invested throughout)', fontsize=10); ax[0].set_ylabel('%'); ax[0].legend(fontsize=8); ax[0].margins(y=.12)
e5 = E.dropna(subset=['peakstart_lump_5y']); x5 = np.arange(len(e5))
b1 = ax[1].bar(x5-w/2, e5.peakstart_lump_5y, w, color='grey', label='Lump sum at the peak')
b2 = ax[1].bar(x5+w/2, e5.peakstart_crash_5y, w, color=pal[2], label='Reserve at the peak, crash-buy')
ax[1].bar_label(b1, fontsize=7, padding=2); ax[1].bar_label(b2, fontsize=7, padding=2); ax[1].set_xticks(x5, e5.label, fontsize=7)
ax[1].axhline(0,color='k',lw=.8); ax[1].set_title('5-year return if you start exactly at the pre-crash peak', fontsize=10); ax[1].legend(fontsize=8); ax[1].margins(y=.12)
plt.tight_layout(); plt.savefig(OUT+'16_crash_types.png', dpi=150); plt.close()
