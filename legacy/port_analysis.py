exec(open('portfolio.py').read())
def breakeven(path):
    m = int(np.argmin(path))
    if path[m] >= 1: return 0.0
    k = next((k for k in range(m, len(path)) if path[k] >= 1), None)
    return None if k is None else round(k/12, 1)
def events_for(h):
    bh, _ = portfolio(h); ath_ = np.maximum.accumulate(bh); dd_ = bh/ath_-1
    ev, armed = [], True
    for i in range(N):
        if dd_[i] == 0: armed = True
        if armed and dd_[i] <= -0.2: ev.append(i); armed = False
    return ev, dd_
rows = []
for h in (0.0, 0.5, 1.0):
    ev, dd_ = events_for(h)
    for t in ev:
        j = t
        while j < N and dd_[j] < 0: j += 1
        st, _ = portfolio(h, s=t, e=min(N-1, t+180), mode='crash')
        ls, _ = portfolio(h, s=t, e=min(N-1, t+180), mode='bh')
        g = lambda v, m: round(100*(v[m]-1)) if m < len(v) else None
        rows.append(dict(hedge=int(100*h), crash=D[t].strftime('%Y-%m'), maxDD=round(100*dd_[t:j].min()),
                         S3=g(st,36), S5=g(st,60), S10=g(st,120), S_trough=round(100*(st.min()-1)), S_be=breakeven(st),
                         L3=g(ls,36), L10=g(ls,120), L_be=breakeven(ls)))
E = pd.DataFrame(rows); print(E.to_string()); E.to_csv('port_events.csv', index=False)
