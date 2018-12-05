"""
    Actuator for the OLTC transformer's tap position.
    Upon receiving a new tap position setpoint, the actuator becomes unresponsive (dead time) until it actuates the new tap position.
"""

import collections
import mosaik_api
from itertools import count


META = {
    'models': {
        'TapActuator': {
            'public': True,
            'params': ['dead_time'],
            'attrs': ['tap_setpoint', 'tap_position'],
        },
    },
}



class TapActuator(mosaik_api.Simulator):

    def __init__(self, META=META):
        super().__init__(META)
        self.data = collections.defaultdict(dict)
        self._entities = {}
        self.eid_counters = {}
        self.is_responsive = {}             # controller state regarding dead time
        self.wakeup_time = {}               # time stamp until end of dead time
        self.dead_time = {}                 # dead time of controller
        self.tap_position = {}                 # dead time of controller
        self.verbose = False


    def init( self, sid, seconds_per_mosaik_timestep=1, verbose=False ):

        self.sec_per_mt = seconds_per_mosaik_timestep # Number of seconds of internaltime per mosaiktime (Default: 1, mosaiktime measured in seconds)
        self.verbose = verbose

        return self.meta


    def create(self, num, model, dead_time=0.):
        counter = self.eid_counters.get(model, count())

        entities = []

        for i in range(num):
            eid = '%s_%s' % (model, next(counter))  # entity ID

            self.data[eid] = { 'tap_position': 0 }
            self.dead_time[eid] = dead_time
            self.is_responsive[eid] = True
            self.wakeup_time[eid] = None

            entities.append( { 'eid': eid, 'type': model, 'rel': [] } )

        return entities


    def step(self, time, inputs):
        #print( 'TAP ACTUATOR called at t = {}, inputs = {}'.format( time, inputs ) )

        for eid, edata in self.data.items():
            input_data = inputs.get(eid, {})

            [ ( _, tap_setpoint ) ] = input_data['tap_setpoint'].items() if 'tap_setpoint' in input_data else [ ( None, None ) ]

            if True is self.is_responsive[eid]: # Tap actuator is responsive.
                if tap_setpoint is not None:
                    self.tap_position[eid] = tap_setpoint
                    if self.verbose: print( "Received new tap position {} at time {}".format( tap_setpoint, time ) )

                    # Enter dead time.
                    self.is_responsive[eid] = False
                    self.wakeup_time[eid] = time + self.dead_time[eid]
                else:
                    edata['tap_position'] = None # No inputs --> no output.
            else: # Controller is not responsive (dead time).
                if time >= self.wakeup_time[eid]:
                    self.wakeup_time[eid] = None
                    self.is_responsive[eid] = True

                    edata['tap_position'] = self.tap_position[eid]
                    if self.verbose: print( "Actuate tap position {} at time {}".format( tap_setpoint, time ) )

        return time + 1


    def get_data(self, outputs):
        data = {}
        for eid, edata in self.data.items():
            requests = outputs[eid]
            mydata = {}
            for attr in requests:
                try:
                    mydata[attr] = edata[attr] if self.is_responsive[eid] is True else None
                except KeyError:
                    raise RuntimeError("Tap actuator has no attribute {0}".format(attr))
            data[eid] = mydata
        return data


if __name__ == '__main__':
    mosaik_api.start_simulation(TapActuator())
