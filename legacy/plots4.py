exec(open('hedge_cmp.py').read().split("rows=[]")[0])
import pickle, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, seaborn as sns
sns.set_theme(style='whitegrid', context='notebook', font_scale=0.95)
OUT='/mnt/user-data/outputs/'
T = pd.read_csv('hedge_table.csv'); RUNS = pickle.load(open('hedge_runs.pkl','rb'))
cols = {'Buy & hold':'grey','R1':sns.color_palette('deep')[0],'R3':sns.color_palette('deep')[1],'R4':sns.color_palette('deep')[2]}
sty  = {'Buy & hold':'-','R1':'-','R3':'--','R4':':'}
wid  = {'Buy & hold':3.5,'R1':2.6,'R3':2.0,'R4':2.2}

# ---- Fig 5 (fixed): equity weight, distinct styles + note ----
fig, ax = plt.subplots(2,1,figsize=(11,6),sharex=True,gridspec_kw=dict(height_ratios=[2,3]))
for n in ['R1','R3','R4']:
    df = RUNS[(1.0,n)]; ax[0].plot(df.date,100*df.w_eq,color=cols[n],ls=sty[n],lw=wid[n],label=n)
ax[0].set_ylabel('Equity weight (%)'); ax[0].set_ylim(-5,108); ax[0].legend(fontsize=8,ncol=3,loc='lower left')
ax[0].text(pd.Timestamp('1975-01-01'),60,'All three rules are 100% invested (lines overlap)\nuntil the first sell signal in 1999',fontsize=9,color='dimgrey')
ax[0].set_title('When each rule held cash (100% hedged)')
bhv = RUNS[(1.0,'Buy & hold')].set_index('date').value
for n in ['R1','R3','R4']:
    v = RUNS[(1.0,n)].set_index('date').value; ax[1].plot(v.index,100*(v/bhv-1),color=cols[n],ls=sty[n],lw=wid[n],label=n)
ax[1].axhline(0,color='k',lw=.8); ax[1].set_ylabel('Value vs buy & hold (%)'); ax[1].legend(fontsize=8,ncol=3,loc='upper left')
ax[1].set_title('Cumulative lead/lag vs buy & hold (0 = identical)')
plt.tight_layout(); plt.savefig(OUT+'5_valuation_signals_fixed.png',dpi=150); plt.close()

# ---- Fig 6 (fixed): equity curves, buy & hold drawn thick underneath ----
fig, ax = plt.subplots(figsize=(11,5))
for n in ['Buy & hold','R1','R3','R4']:
    df = RUNS[(1.0,n)]; ax.plot(df.date,df.value,color=cols[n],ls=sty[n],lw=wid[n],alpha=.9 if n=='Buy & hold' else 1,
                                label=f"{n} ({T[(T.hedge==100)&(T.strat==n)].cagr.iloc[0]:.1f}%/yr)")
df = RUNS[(0.0,'Buy & hold')]; ax.plot(df.date,df.value,color='silver',lw=1.5,ls='-.',label=f"Buy & hold unhedged ({T[(T.hedge==0)&(T.strat=='Buy & hold')].cagr.iloc[0]:.1f}%/yr)")
ax.set_yscale('log'); ax.set_ylabel('Growth of CHF 1 (log)'); ax.set_title('Full cycle, 100% hedged (1971–2026) — lines overlap until 1999 because all rules are fully invested')
ax.legend(fontsize=8,loc='upper left'); plt.tight_layout(); plt.savefig(OUT+'6_full_cycle_equity_fixed.png',dpi=150); plt.close()

# ---- Fig 9: hedge ratio comparison ----
fig, ax = plt.subplots(1,3,figsize=(13,4.3))
T['Hedge'] = T.hedge.astype(str)+'%'
for a_, col, title in zip(ax, ['cagr','2000-2003','2021-2026'], ['Yearly return 1971–2026 (%)','Dot-com: Mar 2000 → Mar 2003 (%)','Recent: Jan 2021 → Aug 2026 (%)']):
    g = sns.barplot(T, x='strat', y=col, hue='Hedge', palette='Blues', ax=a_)
    for c in g.containers: g.bar_label(c, fmt='%.0f' if col!='cagr' else '%.1f', fontsize=7, padding=1)
    a_.set_title(title, fontsize=10); a_.set_xlabel(''); a_.set_ylabel(''); a_.axhline(0,color='k',lw=.8)
    if col=='cagr': a_.set_ylim(6,10)
    if a_ is not ax[0]: a_.get_legend().remove()
    else: a_.legend(title='Hedge',fontsize=8)
plt.suptitle('Effect of the currency hedge ratio (CHF investor)', fontsize=11); plt.tight_layout(); plt.savefig(OUT+'9_hedge_ratio.png',dpi=150); plt.close()

# ---- Fig 10: when did hedging help? ----
s0 = S0; H=120
diff = [100*((EQ[1.0][i+H]/EQ[1.0][i])**(12/H) - (EQ[0.0][i+H]/EQ[0.0][i])**(12/H)) for i in range(s0, len(p)-H)]
fig, ax = plt.subplots(2,1,figsize=(11,6),sharex=True)
ax[0].plot(dates[s0:], usdchf[s0:], color='k'); ax[0].set_ylabel('CHF per USD'); ax[0].set_title('USD/CHF and when hedging paid off')
d = pd.Series(diff, index=dates[s0:len(p)-H].values)
ax[1].fill_between(d.index, d, 0, where=d>=0, color=sns.color_palette('deep')[0], alpha=.6, label='Hedged better')
ax[1].fill_between(d.index, d, 0, where=d<0, color=sns.color_palette('deep')[3], alpha=.6, label='Unhedged better')
ax[1].set_ylabel('Hedged minus unhedged\n10y return (%/yr), by start'); ax[1].legend(fontsize=8); ax[1].axhline(0,color='k',lw=.8)
plt.tight_layout(); plt.savefig(OUT+'10_when_hedging_helped.png',dpi=150); plt.close()
print('share of 10y windows hedged better', round(100*(d>0).mean()), 'median', round(d.median(),2), d.idxmin(), round(d.min(),1), d.idxmax(), round(d.max(),1))
