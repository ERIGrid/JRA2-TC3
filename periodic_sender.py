import mosaik_api
import itertools
import math

META={
    'models': {
        'PeriodicSender':{
            'public': True,
            'params': ['period', 'eid_prefix', 'start_time'],
            'attrs': ['in', 't', 'out'],
        },
    },
}


class PeriodicSender(mosaik_api.Simulator):
    """
        Component which periodically raises *out* to the value of *in*
        *out* is initialized to be None.
    """
    def __init__(self):
        super().__init__(META)
        self.eid = None
        self.step_size=1
        self.eid_counters = {}
        self.eps = 1e-10 # Possible uncertainty in time messages
        self.senders = {} # Tables for translation

    # Additional initialization contingent on sid
    def init(self, sid, eid_prefix='Sender', verbose=False):
        """
            sid: ID given to us by Mosaik
            eid_prefix: Optional eid prefix
        """
        self.sid = sid
        self.eid_prefix = eid_prefix
        self.verbose = verbose

        return self.meta  # Must return self.meta!

    # Initialize simulator model instances (entities)
    def create(self, num, model, **model_params):
        """
        Input:
            num: Number of instances to create
            model: Model identifier (unused)
            source_ids: *num*-length list of identifiers for each metaizers source.
                        If unspecified, replaced with 'UnknownSource_i'
                        where i is a unique integer
        """
        counter = self.eid_counters.setdefault(model, itertools.count())
        entities = []
        for i in range(num):
            eid = '{0}_{1}'.format(self.eid_prefix, next(counter))

            period = model_params.get('period', 1.0)
            start_time = model_params.get('start_time', 0.0)

            self.senders[eid] = {
                    'in': None, 't': None, 'out': None,
                    'start_time': start_time, 'period': period,
                    'next_transmission': int(start_time), 'transmitting' : False}

            entities.append({'eid': eid, 'type': model})

        return entities

    #COS2.4: TODO: Add sec_per_mt
    def step(self, time, inputs):

        # Process inputs
        for eid, sender in self.senders.items():
            inputdata = inputs.get(eid, {})
            if self.verbose: print('At mosaiktime {0} PeriodicSender {1} got input {2}.'.format(time, eid, inputdata))

            sender['t'] = time

            inport = inputdata.get('in', {0:None})
            if len(inport) > 1:
                raise RuntimeError('PeriodicSender {0}\'s *in* is connected to multiple sources. Only one source allowed.'.format(eid))
            inport = next(iter(inport.values()))
            sender['in'] = inport
            if time >= sender['next_transmission']:
                # We have hit our transmission time; time to send a message
                out = inport
                sender['next_transmission'] = int(round(((time-sender['start_time']+self.eps)/sender['period']) + 1) * sender['period']+sender['start_time'])
                sender['transmitting'] = True
            else:
                # Not time yet, lie dormant
                out = None
                sender['transmitting'] = False
            sender['out'] = out
            if self.verbose: print('PeriodicSender {0} sent out {1}'.format(eid, out))

        if any(s['transmitting'] for s in self.senders.values()):
            # Make sure we are woken up so we can set *out* to None
            if self.verbose: print('Transmitting, next time: {0}'.format(time+1))
            return time + 1
        else:
            next_outgoing = min(s['next_transmission'] for s in self.senders.values())
            if self.verbose: print('Not transmitting, next time: {0}'.format(next_outgoing))
            return next_outgoing

    def get_data(self, outputs):
        data = {}
        for eid, sender in self.senders.items():
            requests = outputs.get(eid, [])
            mydata = {}
            for attr in requests:
                try:
                    mydata[attr] = sender[attr]
                except KeyError:
                    raise RuntimeError("PeriodicSender has no attribute {0}".format(attr))

            data[eid] = mydata
        return data

def main():
    return mosaik_api.start_simulation(PeriodicSender())

if __name__ == '__main__':
    main()
