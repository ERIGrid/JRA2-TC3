"""
    A simple data collector that prints all data when the simulator ends.
"""

import collections
import mosaik_api
import pandas as pd
import warnings
# import numpy as np


META = {
        'models': {
                'Monitor': {
                    'public': True,
                    'any_inputs': True,
                    'params': [],
                    'attrs': [],
                    },
            },
    }

def format_func(x):
    try:
        return '{0:.02f}'.format(x)
    except TypeError:
        return str(x)

class Collector(mosaik_api.Simulator):
    def __init__(self):
        super(Collector, self).__init__(META)
        self.eid = None
        self.data = collections.defaultdict(
                lambda: collections.defaultdict(list))
        self.time_list=[]

        self.step_size = None
        self.sec_per_mt = None

    def init(self, sid, step_size, seconds_per_mosaik_timestep=1, print_results=True, save_h5=True, h5_storename='collectorstore', h5_panelname=None):
        self.step_size = step_size
        self.sec_per_mt = seconds_per_mosaik_timestep
        self.print_results = print_results
        self.save_h5 = save_h5
        self.h5_storename = h5_storename
        self.h5_panelname = h5_panelname
        return self.meta

    def create(self, num, model):
        if num>1 or self.eid is not None:
            raise RuntimeError("Can only create one instance of Collector.")

        self.eid = 'Monitor'
        if self.h5_panelname is None: self.h5_panelname = self.eid
        return [{'eid': self.eid, 'type': model}]

    def step(self, time, inputs):
        data = inputs[self.eid]
        for attr, values in data.items():
            for src, value in values.items():
                val_list = self.data[src][attr]
                if value is None:
                    if len( val_list ) is not 0:
                        val_list.append( val_list[-1] )
                        # val_list.append( np.NaN )
                    else:
                        val_list.append( 0 )
                        # val_list.append( np.NaN )
                else:
                    val_list.append( value )
        self.time_list.append(time*self.sec_per_mt)

        return time + self.step_size

    def finalize(self):
        if self.print_results:
            print('Collected data:')
            for sim, sim_data in sorted(self.data.items()):
                print('- {0}'.format(sim))
                for attr, values in sorted(sim_data.items()):
                    print('  - {0}: {1}'.format(attr, list(map(format_func, values))))
        if self.save_h5:
            with warnings.catch_warnings():
                warnings.filterwarnings( 'ignore', category=FutureWarning )

                store = pd.HDFStore(self.h5_storename)
                store[self.h5_panelname] = pd.Panel.from_dict({k: pd.DataFrame(v, index=self.time_list) for k,v in self.data.items()})
                store.close()

if __name__ == '__main__':
    mosaik_api.start_simulation(Collector())
