exec(open('portfolio4.py').read())
import pickle, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, seaborn as sns
from matplotlib.patches import Patch
sns.set_theme(style='whitegrid', context='notebook', font_scale=0.95); pal = sns.color_palette('deep')
OUT = '/mnt/user-data/outputs/'; NAME = {'US':'S&P 500 block (reserve: US Treasuries)','EU':'Europe block (reserve: German Bunds)','CH':'SPI block (reserve: CHF cash)'}
CFG = dict(win=300, q=0.90); log = []; v, Ht, parts, states, costs = portfolio4(log=log, **CFG)
SC = {'SELLING': pal[1], 'OUT': pal[3], 'DEPLOY': pal[2], 'REENTRY': pal[4]}

# ---- Fig 21: committed switches per block ----
fig, ax = plt.subplots(3,1,figsize=(11,9),sharex=True)
for a_, k in zip(ax, W):
    P = PRICE[k]; Sk = np.array(states[k]); a_.plot(D, P/P[0], color='k', lw=1.2); a_.set_yscale('log')
    for stt, c in SC.items():
        a_.fill_between(D, 0, 1, where=Sk==stt, color=c, alpha=.35, step='mid', transform=a_.get_xaxis_transform())
    b = a_.twinx(); w = parts[k][:,0]/parts[k].sum(1)*100; b.plot(D, w, color=pal[0], lw=1.6); b.set_ylim(-3,103); b.set_ylabel('stocks %'); b.grid(False)
    a_.set_title(NAME[k], fontsize=10); a_.set_ylabel('index (log)')
ax[0].legend(handles=[Patch(color=SC[s_], alpha=.5, label=l) for s_, l in [('SELLING','switching out (log, 6 months)'),('OUT','100% in reserve'),
        ('DEPLOY','crash buy-back'),('REENTRY','all-clear re-entry')]] + [plt.Line2D([],[],color=pal[0],label='stocks % (right axis)')], fontsize=7, loc='upper left', ncol=3)
fig.suptitle('Committed switches, 25-year window, 90th percentile trigger', fontsize=11); plt.tight_layout(); plt.savefig(OUT+'21_committed_switches.png', dpi=150); plt.close()

# ---- Fig 22: moving-window percentiles ----
fig, ax = plt.subplots(3,1,figsize=(11,8.5),sharex=True)
for a_, k in zip(ax, W):
    for win, lab, c, ls in [(300,'25-year window',pal[0],'-'),(600,'50-year window',pal[1],'--'),(None,'all history',pal[7],':')]:
        a_.plot(D, 100*val_level(k, win, 'pct'), color=c, ls=ls, lw=1.5, label=lab)
    a_.axhline(90, color=pal[3], lw=1, ls='--', label='sell trigger 90th pct'); a_.axhline(70, color=pal[2], lw=1, ls=':', label='all-clear 70th pct')
    a_.set_ylim(0,102); a_.set_ylabel('percentile')
    a_.set_title({'US':'US: lower of CAPE and Buffett-indicator percentiles','EU':'Europe: price / GDP percentile','CH':'Switzerland: price / GDP percentile'}[k], fontsize=10)
ax[0].legend(fontsize=7, ncol=5, loc='lower left'); plt.tight_layout(); plt.savefig(OUT+'22_window_percentiles.png', dpi=150); plt.close()

# ---- Fig 23: grid + equity curve ----
G = pd.read_csv('v7_grid.csv'); G['window'] = pd.Categorical(G.window, ['25y','35y','50y','all'])
fig = plt.figure(figsize=(12,8)); gs = fig.add_gridspec(2,3,height_ratios=[1,1.3])
for j, (col, t, cm, fmt) in enumerate([('vs_lump','Return vs lump sum (%/yr)','RdYlGn','+.2f'),('ulcer','Ulcer index (lump sum 14.9)','RdYlGn_r','.1f'),('stocks_now','Stocks today (%)','Blues','.0f')]):
    a_ = fig.add_subplot(gs[0,j]); m = G.pivot(index='window', columns='q', values=col)
    sns.heatmap(m, annot=True, fmt=fmt, cmap=cm, center=0 if col=='vs_lump' else None, cbar=False, ax=a_); a_.set_title(t, fontsize=10)
    a_.set_xlabel('sell percentile'); a_.set_ylabel('window' if j==0 else '')
a_ = fig.add_subplot(gs[1,:]); vl, *_ = portfolio4(mode='bh')
a_.plot(D, vl, color='grey', lw=3, label=f"Lump sum ({stats(vl)['cagr']:.1f}%/yr, worst {stats(vl)['maxdd']:.0f}%)")
for cfg, c, lab in [(dict(win=300,q=0.90), pal[2], '25y window, 90th pct'), (dict(win=600,q=0.90), pal[1], '50y window, 90th pct')]:
    vv, *_ = portfolio4(**cfg); a_.plot(D, vv, color=c, lw=1.8, label=f"{lab} ({stats(vv)['cagr']:.1f}%/yr, worst {stats(vv)['maxdd']:.0f}%)")
a_.set_yscale('log'); a_.legend(fontsize=8, loc='upper left'); a_.set_ylabel('Growth of CHF 1 (log)')
a_.set_title('Committed-switch model, 30/30/40, US+EU hedged', fontsize=10)
plt.tight_layout(); plt.savefig(OUT+'23_window_results.png', dpi=150); plt.close()
