exec(open('model2.py').read())
V = {
 'Base (20%)':            make(),
 'Trigger 22%':           make(trig=.22),
 'Trigger 25%':           make(trig=.25),
 'Trigger 30%':           make(trig=.30),
 'CAPE-adaptive':         make(cape_adapt=True),
 'CAPE-adapt + 50% hedge':make(cape_adapt=True, hedge=.5),
 'CAPE-adapt + 100% hedge':make(cape_adapt=True, hedge=1.0),
 'Full: CAPE+50%hedge+30% pre+36m wait cap': make(cape_adapt=True, hedge=.5, pre=.3, wait_limit=36),
}
