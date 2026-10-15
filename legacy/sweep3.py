exec(open('model3.py').read())
E12 = int(np.where(dates==pd.Timestamp('2012-12-01'))[0][0])
bhA = stats(bh(eqH, e=E12)); bhB = stats(bh(eqH))
rows=[]
for C in [25,28,30,33,35,38,40]:
    for B in [100,120,140,160,180,200]:
        for tc in (False,True):
            for fl in (0.0,0.5):
                a=stats(cycle(C,B,trend_confirm=tc,floor=fl,wait_cap=36,e=E12)); b=stats(cycle(C,B,trend_confirm=tc,floor=fl,wait_cap=36))
                rows.append(dict(C=C,B=B,trend=tc,floor=fl,dA=a['cagr']-bhA['cagr'],ddA=a['maxdd'],dB=b['cagr']-bhB['cagr'],ddB=b['maxdd'],cashB=b['cash_share']))
df=pd.DataFrame(rows); df.to_csv('sweep3.csv',index=False)
print('BH A',bhA,'BH B',bhB)
print(df.sort_values('dA',ascending=False).head(12).round(2).to_string())
print(df[(df.trend)&(df.floor==0)].pivot(index='C',columns='B',values='dA').round(2))
print(df[(~df.trend)&(df.floor==0)].pivot(index='C',columns='B',values='dA').round(2))
