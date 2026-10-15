exec(open('model3.py').read())
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, seaborn as sns, matplotlib.dates as mdates
sns.set_theme(style='whitegrid', context='notebook', font_scale=0.95)
OUT='/mnt/user-data/outputs/'
R = {'R1: sell 100% at CAPE≥35 & BI≥140': dict(C=35,B=140),
     'R3: same, sell only to 50%':       dict(C=35,B=140,floor=0.5),
     'R4: CAPE≥30 & BI≥120 & price<10m avg, to 50%': dict(C=30,B=120,trend_confirm=True,floor=0.5)}
runs = {n: cycle(**k, wait_cap=36) for n,k in R.items()}
runs_bh = {'Buy & hold, 100% hedged': bh(eqH), 'Buy & hold, unhedged': bh(tr_chf)}
pal = dict(zip(list(runs_bh)+list(R), ['grey','silver']+sns.color_palette('deep')[:3]))
D = dates[S0:].values

# ---- Fig 5: valuation dashboard ----
fig, ax = plt.subplots(3,1,figsize=(11,8.5),sharex=True,gridspec_kw=dict(height_ratios=[3,3,2]))
ax[0].plot(D, cape[S0:], color='k', lw=1.4); ax[0].axhline(30,ls='--',color=pal[list(R)[2]],lw=1.2,label='R4 threshold 30'); ax[0].axhline(35,ls='--',color=pal[list(R)[0]],lw=1.2,label='R1/R3 threshold 35')
ax[0].set_ylabel('Shiller CAPE'); ax[0].legend(loc='upper left',fontsize=8); ax[0].set_title('Valuation signals and when each rule held cash (1971–2026)')
ax[0].annotate(f'Now ≈{cape[-1]:.0f}', (D[-1], cape[-1]), xytext=(-60,5), textcoords='offset points', fontsize=9)
ax[1].plot(D, bi[S0:], color='k', lw=1.4); ax[1].axhline(120,ls='--',color=pal[list(R)[2]],lw=1.2,label='R4 threshold 120%'); ax[1].axhline(140,ls='--',color=pal[list(R)[0]],lw=1.2,label='R1/R3 threshold 140%')
ax[1].set_ylabel('Buffett indicator (%)\nmarket cap / GDP (proxy)'); ax[1].legend(loc='upper left',fontsize=8)
ax[1].annotate(f'Now ≈{bi[-1]:.0f}%', (D[-1], bi[-1]), xytext=(-75,-5), textcoords='offset points', fontsize=9)
for n,df in runs.items(): ax[2].plot(df.date, 100*df.w_eq, color=pal[n], lw=1.6, label=n.split(':')[0])
ax[2].set_ylabel('Equity weight (%)'); ax[2].set_ylim(-5,105); ax[2].legend(loc='lower left',fontsize=8,ncol=3)
plt.tight_layout(); plt.savefig(OUT+'5_valuation_signals.png',dpi=150); plt.close()

# ---- Fig 6: equity curves ----
fig, ax = plt.subplots(figsize=(11,5))
for n,df in {**runs_bh, **runs}.items():
    ax.plot(df.date, df.value, color=pal[n], lw=2 if n in R else 1.5, ls='--' if 'unhedged' in n else '-', label=f"{n}  ({stats(df)['cagr']:.1f}%/yr)")
ax.set_yscale('log'); ax.set_ylabel('Growth of CHF 1 (log scale)'); ax.set_title('Full cycle: valuation sell rule + crash buy rule, in CHF (1971–2026)')
for a,b in [('2000-03-01','2003-03-01'),('2021-01-01','2026-08-01')]: ax.axvspan(pd.Timestamp(a),pd.Timestamp(b),color='grey',alpha=.08)
ax.legend(fontsize=8,loc='upper left'); plt.tight_layout(); plt.savefig(OUT+'6_full_cycle_equity.png',dpi=150); plt.close()

# ---- Fig 7: threshold heatmaps ----
sw = pd.read_csv('sweep3.csv')
fig, ax = plt.subplots(1,2,figsize=(12,4.6))
for a_, (tr,fl,title) in zip(ax, [(False,0.0,'Valuation only, sell 100%'),(True,0.5,'Valuation + price below 10m avg, sell to 50%')]):
    m = sw[(sw.trend==tr)&(sw.floor==fl)].pivot(index='C',columns='B',values='dB')
    sns.heatmap(m, annot=True, fmt='.1f', cmap='RdYlGn', center=0, vmin=-1.5, vmax=1.5, ax=a_, cbar_kws={'label':'%/yr vs buy & hold (hedged)'})
    a_.set_title(title, fontsize=10); a_.set_xlabel('Buffett indicator threshold (%)'); a_.set_ylabel('CAPE threshold'); a_.invert_yaxis()
fig.suptitle('Extra return per year vs buy & hold, 1971–2026 (CHF, hedged)', fontsize=11)
plt.tight_layout(); plt.savefig(OUT+'7_threshold_heatmaps.png',dpi=150); plt.close()

# ---- Fig 8: episode bars ----
def seg(df,a,b):
    v=df.set_index('date').value; return 100*(v[pd.Timestamp(b)]/v[pd.Timestamp(a)]-1)
eps_ = [('Dot-com: Mar 2000 → Mar 2003','2000-03-01','2003-03-01'),('Dot-com: Mar 2000 → Mar 2010','2000-03-01','2010-03-01'),
        ('2008: Oct 2007 → Oct 2010','2007-10-01','2010-10-01'),('Recent: Jan 2021 → Aug 2026','2021-01-01','2026-08-01')]
rows=[]
for n,df in {**{'Buy & hold, 100% hedged':runs_bh['Buy & hold, 100% hedged']}, **runs}.items():
    for lab,a,b in eps_: rows.append(dict(strategy=n.split(':')[0] if ':' in n else 'Buy & hold', episode=lab, ret=seg(df,a,b)))
eb = pd.DataFrame(rows); eb.to_csv('episodes.csv', index=False)
plt.figure(figsize=(11,4.8))
g = sns.barplot(eb, x='episode', y='ret', hue='strategy', palette=['grey']+sns.color_palette('deep')[:3])
for c in g.containers: g.bar_label(c, fmt='%.0f', fontsize=8, padding=2)
plt.axhline(0,color='k',lw=.8); plt.ylabel('Return in CHF (%)'); plt.xlabel(''); plt.title('What the sell rule does in each type of episode'); plt.legend(fontsize=8)
plt.tight_layout(); plt.savefig(OUT+'8_episodes.png',dpi=150); plt.close()
for n,df in {**runs_bh, **runs}.items(): print(n, {k:round(v,2) for k,v in stats(df).items()}, round(df.w_eq.iloc[-1],2))
print(eb.pivot(index='strategy',columns='episode',values='ret').round(0))
