import mosaik_api
from itertools import count
import math

META = {
    'models': {
        'RampingLoad': {
            'public': True,
            'params': ['Llow', 'Lhigh', 'ramp_time'],
            'attrs': ['L'],
        },
    },
}


class RampLoadSim:
    def __init__(self, Llow, Lhigh, ramp_time):
        self.Llow = Llow
        self.Lhigh = Lhigh
        self.ramp_time = ramp_time
        self.calc_load(0)

    def calc_load(self, t):
        if t > self.ramp_time:
            self.load = self.Lhigh
        else:
            delta = 1 - ( self.ramp_time - t ) / self.ramp_time
            self.load = self.Llow + ( self.Lhigh - self.Llow ) * delta

    def get_load(self):
        return self.load


class RampingLoad(mosaik_api.Simulator):
    def __init__(self, META=META):
        super().__init__(META)

        # Per-entity dicts
        self.eid_counters = {}
        self.simulators = {}
        self.return_data = False

    def init(self, sid, step_size=5, eid_prefix="RampingLoad"):
        self.step_size = step_size
        self.eid_prefix = eid_prefix
        return self.meta

    def create(self, num, model, Llow=1.0, Lhigh=5.0, ramp_time=0):
        counter = self.eid_counters.setdefault(model, count())

        entities = []

        for _ in range(num):
            eid = '%s_%s' % (self.eid_prefix, next(counter))

            esim = RampLoadSim(Llow, Lhigh, ramp_time)
            self.simulators[eid] = esim

            entities.append({'eid': eid, 'type': model})

        return entities

    ###
    #  Functions used online
    ###

    def step(self, time, inputs):

        if 0 == math.fmod( time, self.step_size ):
            for eid, esim in self.simulators.items():
                esim.calc_load(time)
            self.return_data = True
        else:
            self.return_data = False

        return time + 1 # self.step_size

    def get_data(self, outputs):
        data = {}

        for eid, esim in self.simulators.items():
            requests = outputs.get(eid, [])
            mydata = {}
            for attr in requests:
                if attr == 'L':
                    mydata[attr] = esim.get_load() if self.return_data is True else None
                else:
                    raise RuntimeError("RampingLoad {0} has no attribute {1}.".format(eid, attr))
            data[eid] = mydata

        return data
