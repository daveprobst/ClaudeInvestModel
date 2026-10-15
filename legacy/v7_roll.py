exec(open('portfolio4.py').read())
import pickle
CF = {'Lump sum': dict(mode='bh'), '25y window, 90th pct': dict(win=300, q=0.90), '35y window, 90th pct': dict(win=420, q=0.90),
      '50y window, 90th pct': dict(win=600, q=0.90), '25y window, 85th pct': dict(win=300, q=0.85), '25y window, 95th pct': dict(win=300, q=0.95)}
H = 120; R = {n: [] for n in CF}
for s in range(0, N-H, 2):
    for n, kw in CF.items():
        v, *_ = portfolio4(s=s, e=s+H, **kw); R[n].append(100*(v[-1]**(12/H)-1))
R = pd.DataFrame(R); L = R['Lump sum']
RS = pd.DataFrame({n: dict(avg=R[n].mean(), worst=R[n].min(), loss=100*(R[n]<0).mean(), better=100*(R[n]-L>0.05).mean(),
                           worse=100*(R[n]-L<-0.05).mean()) for n in CF}).T.round(1); print(RS)
pickle.dump(RS, open('v7_roll.pkl','wb'))
