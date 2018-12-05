import matplotlib.pyplot as plt
#import matplotlib.dates as mdates
import pandas as pd
import sys
# import seaborn as sns

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

#plt.ion()

if len(sys.argv) > 1:
    storename = sys.argv[1]
else:
    storename = 'erigridstore.h5'



store = pd.HDFStore(storename)
df = store['Monitor']
store.close()
df2 = df.to_frame(False).unstack().dropna(axis=1)
df2.columns = df2.columns.map('.'.join)
df2.index.name = ""
df2 = df2.rename(columns=lambda x: '.'.join(x.split('.')[1:]))

c1 = [c for c in df2.columns if '.U' in c]
c1r = {'TC3PowerSystem_0.U3': 'V1', 'TC3PowerSystem_0.U4': 'V2'} # {c : c.split('.')[-1] for c in c1}

c2 = [c for c in df2.columns if 'rampload' in c]
c2r = {c: 'Load{0}'.format(1 + int(c.split('.')[0].split('_')[-1])) for c in c2}

c3 = [c for c in df2.columns if '.current_tap' in c]
c3r = {c : c.split('.')[-1] for c in c3}

df2 = df2.rename(columns=c1r)
df2 = df2.rename(columns=c2r)
c1 = [c1r[c] for c in c1]
c2 = [c2r[c] for c in c2]

#plt.figure(dpi=200)

fig, axarr = plt.subplots( 3, sharex = True, figsize = ( 4, 8 ) )
plt.subplots_adjust( bottom=0.08, top=0.98 )

df2.plot(y=c2, ax=axarr[0], lw=2, ls='-')
leg = axarr[0].legend(ncol=2, loc='upper left')
axarr[0].set( ylabel = r'$P_{\mathrm{load}}$ in kW' )

df2.plot(y=c3, ax=axarr[1], lw=2, c='g', ls='-', ylim = ( -3, 1 ), legend = False)
axarr[1].set( ylabel = r'tap position' )

df2.plot(y=c1, ax=axarr[2], lw=2, ls='-', ylim = ( 0.93, 1.07 ) )
leg2=axarr[2].legend(ncol=2, loc='upper left')
plt.axhline( 0.95, ls='--', lw=1, c='k', alpha = 0.5 )
plt.axhline( 1.05, ls='--', lw=1, c='k', alpha = 0.5)
plt.ylabel( 'voltage in p.u.' )


fig.text( 0.5, 0.02, 'time in s', ha = 'center' )

plt.subplots_adjust( left = 0.17, right = 0.99, hspace = 0.1 )

plt.show()
