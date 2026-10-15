exec(open('portfolio.py').read())
import pickle, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, seaborn as sns
sns.set_theme(style='whitegrid', context='notebook', font_scale=0.95)
OUT = '/mnt/user-data/outputs/'; pal = sns.color_palette('deep')
RUNS = pickle.load(open('port_runs.pkl','rb')); E = pd.read_csv('port_events.csv'); T = pd.read_csv('port_cycle.csv')

# ---- Fig 11: sleeves in CHF ----
fig, ax = plt.subplots(figsize=(11,4.8))
for (k,h,lab,c,ls) in [('US',0,'S&P 500 unhedged',pal[0],'--'),('US',1,'S&P 500 100% hedged',pal[0],'-'),
                        ('EU',0,'Europe unhedged',pal[1],'--'),('EU',1,'Europe 100% hedged',pal[1],'-'),('CH',0,'SPI (CHF)',pal[3],'-')]:
    v = sleeve_index(k,h); ax.plot(D, v/v[0], color=c, ls=ls, lw=2, label=f"{lab} ({stats(v/v[0])['cagr']:.1f}%/yr)")
bh,_ = portfolio(0.5); ax.plot(D, bh, color='k', lw=2.5, label=f"30/30/40 mix, 50% hedged ({stats(bh)['cagr']:.1f}%/yr)")
ax.set_yscale('log'); ax.set_ylabel('Growth of CHF 1 (log)'); ax.set_title('The three building blocks in CHF, 1971–2026 (total return)')
ax.legend(fontsize=8, loc='upper left'); plt.tight_layout(); plt.savefig(OUT+'11_sleeves_chf.png', dpi=150); plt.close()

# ---- Fig 12: crash events, strategy vs lump sum (50% hedge) ----
e = E[E.hedge==50].copy(); e['crash'] = e.crash.str[:4]
fig, ax = plt.subplots(1,2,figsize=(12,4.4))
for a_, (sc, lc, title) in zip(ax, [('S3','L3','3 years after the 20% drop'),('S10','L10','10 years after the 20% drop')]):
    x = np.arange(len(e)); w = .38
    b1 = a_.bar(x-w/2, e[sc], w, color=pal[2], label='Crash-buy strategy (start in cash)')
    b2 = a_.bar(x+w/2, e[lc], w, color='grey', label='Lump sum at the 20% drop')
    a_.bar_label(b1, fmt='%.0f', fontsize=8, padding=2); a_.bar_label(b2, fmt='%.0f', fontsize=8, padding=2)
    a_.set_xticks(x, e.crash); a_.margins(y=0.12); a_.axhline(0, color='k', lw=.8); a_.set_title(title, fontsize=10); a_.set_ylabel('Return in CHF (%)')
ax[0].legend(fontsize=8)
fig.suptitle('30/30/40 portfolio: every crash of 20%+ since 1971 (50% hedged)', fontsize=11)
plt.tight_layout(); plt.savefig(OUT+'12_portfolio_crashes.png', dpi=150); plt.close()

# ---- Fig 13: full cycle vs buy & hold (50% hedge) ----
fig, ax = plt.subplots(2,1,figsize=(11,7),sharex=True,gridspec_kw=dict(height_ratios=[3,2]))
bh = RUNS[(0.5,'Buy & hold')][0]
sty = {'Buy & hold':('grey','-',3.5),'R4 (US sleeve)':(pal[2],':',2.4),'R4 (all sleeves)':(pal[0],'-',2),'R3 (all sleeves)':(pal[1],'--',2)}
for n,(c,ls,lw) in sty.items():
    v = RUNS[(0.5,n)][0]; ax[0].plot(D, v, color=c, ls=ls, lw=lw, label=f"{n} ({stats(v)['cagr']:.2f}%/yr)")
    if n != 'Buy & hold': ax[1].plot(D, 100*(v/bh-1), color=c, ls=ls, lw=lw, label=n)
ax[0].set_yscale('log'); ax[0].set_ylabel('Growth of CHF 1 (log)'); ax[0].legend(fontsize=8, loc='upper left')
ax[0].set_title('Full cycle on the 30/30/40 portfolio (50% hedged) — lines overlap until the first sell signal in 1999')
ax[1].axhline(0,color='k',lw=.8); ax[1].set_ylabel('Value vs buy & hold (%)'); ax[1].legend(fontsize=8, loc='upper left')
plt.tight_layout(); plt.savefig(OUT+'13_portfolio_full_cycle.png', dpi=150); plt.close()
