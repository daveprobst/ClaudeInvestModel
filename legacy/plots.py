exec(open('variants.py').read())
import pickle, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, seaborn as sns
sns.set_theme(style='whitegrid', context='notebook', font_scale=0.95)
res = pickle.load(open('res.pkl','rb'))
OUT='/mnt/user-data/outputs/'
short = {'Base (20%)':'Base 20%','Trigger 22%':'Trigger 22%','Trigger 25%':'Trigger 25%','Trigger 30%':'Trigger 30%',
         'CAPE-adaptive':'CAPE-adaptive','CAPE-adapt + 50% hedge':'CAPE + 50% hedge',
         'CAPE-adapt + 100% hedge':'CAPE + 100% hedge','Full: CAPE+50%hedge+30% pre+36m wait cap':'Full package'}

# ---- Fig 1: trigger sweep ----
trigs=[.15,.18,.20,.22,.25,.28,.30,.35]; rows=[]
for tg in trigs:
    c=make(trig=tg); e=event_stats(c).set_index('crash'); r=rolling_stats(c)
    miss=0
    for t in events:
        run(c,t,60,peak_mode='ath'); j=t
        while j<len(p) and dd[j]<0: j+=1
        if LAST_TRIG is None or LAST_TRIG>=j: miss+=1
    rows.append(dict(trig=int(tg*100), r3=e.r3[2001], r10=e.r10[2001], miss=miss, roll=100*r.strat.mean()))
sw=pd.DataFrame(rows); sw.to_csv('sweep.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(11,4.2))
ax[0].plot(sw.trig,sw.r3,'o-',label='3 years after'); ax[0].plot(sw.trig,sw.r10,'s--',label='10 years after')
ax[0].axhline(0,color='grey',lw=1); ax[0].set(title='2001 crash: return in CHF by trigger level',xlabel='First-buy trigger (% drop)',ylabel='Return (%)'); ax[0].legend()
a2=ax[1]; a2.bar(sw.trig,sw.miss,width=1.6,color=sns.color_palette()[3],alpha=.75,label='Crashes missed (of 11)')
a2.set(xlabel='First-buy trigger (% drop)',ylabel='Crashes missed entirely',title='Cost of waiting deeper')
b2=a2.twinx(); b2.plot(sw.trig,sw.roll,'o-',color=sns.color_palette()[0],label='Avg 10y return, all start dates'); b2.set_ylabel('Avg 10y return (%/yr)'); b2.grid(False)
b2.set_ylim(0,max(sw.roll)*1.3)
h1,l1=a2.get_legend_handles_labels(); h2,l2=b2.get_legend_handles_labels(); a2.legend(h1+h2,l1+l2,loc='upper left',fontsize=8)
plt.tight_layout(); plt.savefig(OUT+'1_trigger_sweep.png',dpi=150); plt.close()

# ---- Fig 2: heatmap 3y returns ----
hm=pd.DataFrame({short[n]:res[n][0].r3 for n in V}).T
missed={}
for n,c in V.items():
    for t in events:
        run(c,t,60,peak_mode='ath'); j=t
        while j<len(p) and dd[j]<0: j+=1
        if LAST_TRIG is None or LAST_TRIG>=j: missed[(short[n],dates[t].year)]=1
annot=hm.copy().astype(object)
for (r_,c_),_ in missed.items(): annot.loc[r_,c_]=f"{hm.loc[r_,c_]:.0f}\nmiss"
for r_ in hm.index:
    for c_ in hm.columns:
        if not isinstance(annot.loc[r_,c_],str): annot.loc[r_,c_]='' if np.isnan(hm.loc[r_,c_]) else f"{hm.loc[r_,c_]:.0f}"
plt.figure(figsize=(12,5))
sns.heatmap(hm,annot=annot,fmt='',cmap='RdYlGn',center=0,vmin=-45,vmax=45,linewidths=.5,cbar_kws={'label':'3-year return in CHF (%)'})
plt.title('3-year return after each crash (clock starts at the 20% drop) — "miss" = never deployed'); plt.xlabel('Crash (year of 20% drop)'); plt.ylabel('')
plt.tight_layout(); plt.savefig(OUT+'2_heatmap_3y.png',dpi=150); plt.close()

# ---- Fig 3: 2001 paths ----
t=[e for e in events if dates[e].year==2001][0]
plt.figure(figsize=(10,4.8))
for n in ['Base (20%)','Trigger 25%','CAPE-adaptive','CAPE-adapt + 50% hedge','Full: CAPE+50%hedge+30% pre+36m wait cap']:
    pth=run(V[n],t,144,peak_mode='ath'); plt.plot(np.arange(len(pth))/12+2001.2,100*pth,lw=2 if n!='Base (20%)' else 2.5,label=short[n],ls='-' if 'CAPE' in n or 'Full' in n else '--')
ls=tr_chf[t:t+145]/tr_chf[t]; plt.plot(np.arange(len(ls))/12+2001.2,100*ls,color='grey',lw=1.5,ls=':',label='Lump sum at 20% drop')
plt.axhline(100,color='black',lw=.8); plt.axvspan(2001.2,2004.2,color='grey',alpha=.08); plt.text(2001.4,142,'3-year goal window',fontsize=9,color='grey')
plt.title('2000–2002 dot-com crash: portfolio value in CHF (100 = capital at 20% drop, Mar 2001)'); plt.ylabel('Value (CHF, start = 100)'); plt.xlabel('')
plt.legend(fontsize=8,ncol=2,loc='lower left'); plt.tight_layout(); plt.savefig(OUT+'3_dotcom_paths.png',dpi=150); plt.close()

# ---- Fig 4: rolling 10y ----
plt.figure(figsize=(11,4.5))
for n,col in [('Base (20%)',sns.color_palette()[0]),('Full: CAPE+50%hedge+30% pre+36m wait cap',sns.color_palette()[2])]:
    r=res[n][1]; s_=r.set_index('start').strat.rolling(12).mean()*100; plt.plot(s_.index,s_,color=col,lw=2,label=short[n])
bh=res['Base (20%)'][1].set_index('start').bh.rolling(12).mean()*100; plt.plot(bh.index,bh,color='grey',lw=1.5,ls='--',label='Buy & hold S&P (CHF)')
plt.axhline(0,color='black',lw=.8)
plt.title('Average yearly return over the next 10 years, by start date (CHF)'); plt.ylabel('% per year'); plt.legend(fontsize=9)
plt.tight_layout(); plt.savefig(OUT+'4_rolling_10y.png',dpi=150); plt.close()
print(sw)
