import itertools
import os
import mosaik_api

from fmi_cs_v1_standalone.FMUCoSimulationV1 import *
from fmi_cs_v1_standalone.extractFMU import *
import fmi_cs_v1_standalone.parse_xml

from math import ceil
from collections import defaultdict

META = {
    'models': {
        'TC3CommNetwork': {
            'public': True,
            'params': [],
            'attrs': [
                'u3_send',
                'u4_send',
                'ctrl_send',
                'u3_receive',
                'u4_receive',
                'ctrl_receive',
                'current_time'
            ],
        }
    }
}



class TC3CommNetwork(mosaik_api.Simulator):
    """
        MosaikTime-based edition of Cornelius' JRA2 TC3 workaround.
        This version meta-izes messages sent through the queue
    """
    def __init__(self):
        super(TC3CommNetwork, self).__init__(META)
        self.sid = None

        self._entities = {}
        self.eid_counters = {}

        self.work_dir = None                # directory of FMU
        self.model_name = None              # model name of FMU
        self.instance_name = None           # instance name of FMU
        self.var_table = None               # dict of FMU variables (input, output, parameters)
        self.translation_table = None       # help dict if variable names cannot be parsed properly in Python
        self.logging_on = False             # FMI++ parameter
        self.time_diff_resolution = 1e-9    # FMI++ parameter
        self.interactive = False            # FMI++ parameter
        self.visible = False                # FMI++ parameter
        self.start_time = 0                 # FMI++ parameter
        self.stop_time = 0                  # FMI++ parameter
        self.stop_time_defined = False      # FMI++ parameter
        self.uri_to_extracted_fmu = None
        self.current_time = 0               # keeping track of current time needed for JRA2-TC3 workaround
        self.fmutimes = {}                  # Keeping track of each FMU's internal time
        self.fmuwanttimes = {}              # Keeping track of each FMU's next event in internal time
        self.event_var_name = False         # Name of the FMU's variable that gives the timing of the next event
        self.default_event_step_size = 0,   # Time between 'default events' (0 = no default events)
        self.random_seed = 1,               # ns-3 random generator seed
        self.msgtable = {}                  # Tables of messages for translation
        self.msgcounters = {}               # Set of counters for message ID translation
        self.outqueue = {}                  # Holds lists of outputs for various simulators
        self.sec_per_mt = 1                 # Number of seconds of internaltime per mosaiktime
        self.verbose = False


    def init( self, sid, work_dir, model_name, instance_name,
              start_time=0, stop_time=0, stop_time_defined=False, seconds_per_mosaik_timestep=1,
              time_diff_resolution=1e-9, logging_on=False, interactive=False, visible=False,
              event_var_name='next_event_time', default_event_step_size=0, random_seed=1,
              var_table=None, translation_table=None, path_conversion=None, verbose=False
              ):
        '''Function that allows mosaik to initialize the simulator. Extract the FMU and construct meta description
        for mosaik.'''
        assert work_dir is not None
        assert model_name is not None
        assert instance_name is not None
        self.sid = sid

        if path_conversion == 'win2cygwin':
            from utils_cygwin import Cygpath
            work_dir = Cygpath().win2posix( work_dir )
            if verbose is True:
                print( 'Converted working directory to Cygwin path: {}'.format( work_dir ) )

        self.work_dir = work_dir
        self.model_name = model_name
        self.instance_name = instance_name
        self.start_time = start_time
        self.stop_time = stop_time
        self.stop_time_defined = stop_time_defined
        self.sec_per_mt = seconds_per_mosaik_timestep
        self.time_diff_resolution = time_diff_resolution
        self.logging_on = logging_on
        self.interactive = interactive
        self.visible = visible
        self.event_var_name = event_var_name
        self.default_event_step_size = default_event_step_size
        self.random_seed = random_seed
        self.verbose = verbose

        path_to_fmu = os.path.join(self.work_dir, self.model_name + '.fmu')
        if self.verbose: print('Attempted to extract FMU {0}, Path {1}'.format(path_to_fmu, self.work_dir))

        self.uri_to_extracted_fmu = extractFMU(
            path_to_fmu,
            self.work_dir,
            command = 'unzip -q -o {fmu} -d {dir}'
            )
        assert self.uri_to_extracted_fmu is not None

        '''If no variable table is given by user, parse the modelDescription.xml for a table -
        however, this will not work properly for some FMUs due to varying conventions.'''
        xmlfile = os.path.join(self.work_dir, self.model_name, 'modelDescription.xml')
        if var_table is None:
            self.var_table, self.translation_table = fmi_cs_v1_standalone.parse_xml.get_var_table(xmlfile)
        else:
            self.var_table = var_table
            self.translation_table = translation_table

        self.adjust_var_table()

        return self.meta

    def create(self, num, model):
        '''Function that allows mosaik the creation of model entities for the connection in co-sim scenarios.'''
        counter = self.eid_counters.setdefault(model, itertools.count())

        entities = []

        for i in range(num):
            eid = '%s_%s' % (model, next(counter))  # entity ID

            if self.verbose: print('{0}, {1}, {2}, {3}'.format(self.work_dir, self.model_name, self.logging_on, self.time_diff_resolution))

            fmu = FMUCoSimulationV1( self.model_name, self.work_dir )

            self._entities[eid] = fmu
            self._entities[eid].instantiateSlave(
                name = self.instance_name,
                visible = self.visible,
                interactive = self.interactive,
                logging_on = self.logging_on
                )

            model_params = {
                'default_event_step_size' : self.default_event_step_size,
                'random_seed' : self.random_seed
            }
            self.set_values(eid, model_params, 'parameter')

            init_stat = self._entities[eid].initializeSlave(
                start_time = self.start_time*self.sec_per_mt,
                stop_time = self.stop_time*self.sec_per_mt,
                stop_time_defined = self.stop_time_defined
                )

            # Handling tracking internal fmu times
            self.fmutimes[eid] = self.start_time*self.sec_per_mt
            self.fmuwanttimes[eid] = self.stop_time*self.sec_per_mt

            # Message ID tracker
            self.msgcounters[eid] = itertools.count(start=1) # msgIDs start at 1, as 0 == no msg
            self.msgtable[eid] = {} # Table containing msgID -> message information

            # Outbound message queue
            self.outqueue[eid] = {}

            entities.append({'eid': eid, 'type': model, 'rel': []})

        return entities

    def step(self, time, inputs=None):
        '''Function for stepping of the simulator during the co-simulation process.'''

        #if self.verbose: print( '\n##### MOSAIK TIME {} #####\nqueue input was {}'.format( time, inputs ) )
        if self.verbose: print( '\n##### MOSAIK TIME {} #####'.format( time ) )

        # This is the internaltime we want to step our queues to
        target_time = ( time + self.start_time )*self.sec_per_mt

        for eid, fmu in self._entities.items():
            # Process outputs
            # Clear output queue
            self.outqueue[eid] = {}

            # Grab the time of next event
            next_event_time = fmu.getReal( [ self.event_var_name ] )[0]
            self.fmuwanttimes[eid] = next_event_time

            # While we have output messages waiting, step the queue along and store the output in self.outqueue
            while self.fmuwanttimes[eid] < target_time + self.time_diff_resolution:

                if self.verbose: print( 'QUEUE: About to step from fmutime = {}, to fmuwanttime = {}'.format( self.fmutimes[eid], self.fmuwanttimes[eid] ) )
                # Update the internal state of the FMU to the time of the next event,

                fmu.doStep(
                    current_communication_point = self.fmutimes[eid],
                    communication_step_size = self.fmuwanttimes[eid]-self.fmutimes[eid]
                    )
                # Save the current internal time

                self.fmutimes[eid] = self.fmuwanttimes[eid]
                # Update the internal state of the FMU to the time of the next event,
                fmu.doStep(
                    current_communication_point = self.fmutimes[eid],
                    communication_step_size = 0
                    )

                for attr in self.var_table['output'].keys():
                    if attr == self.event_var_name: continue

                    msg_id = self.get_value(eid, attr)
                    # msg_id == 0 => no msg
                    if msg_id > 0:
                        # A message is here! Append it to the message queue!
                        [ input_name, val ] = self.msgtable[eid][msg_id]
                        self.outqueue[eid][input_name] = val
                        if self.verbose: print( 'OUTPUT MESSAGE: {} from {}, msg_id = {}'.format( val, input_name, msg_id ) )

                next_event_time = fmu.getReal( [ self.event_var_name ] )[0]
                self.fmuwanttimes[eid] = next_event_time

            # Step our FMU to the current time
            if self.fmutimes[eid] < target_time - self.time_diff_resolution:
                if self.verbose: print( 'QUEUE: About to step from fmutime = {} to target_time = {}'.format( self.fmutimes[eid], target_time ) )
                fmu.doStep(
                    current_communication_point = self.fmutimes[eid],
                    communication_step_size = target_time-self.fmutimes[eid]
                    )
                # Save the current internal time
                self.fmutimes[eid] = target_time

            # Process inputs
            inputdata = inputs.get(eid, {})

            # Set inputs to FMU if any input port is nonzero
            for input_name, vals in inputdata.items():
                for source, val in vals.items():
                    if val is not None:
                        msg_id = next( self.msgcounters[eid] )
                        self.msgtable[eid][msg_id] = [ input_name, val ]
                        if self.verbose:
                            print( 'INPUT MESSAGE: {0} from {1}, assigned msg_id = {2}.'.format( val, input_name, msg_id ) )
                        self.set_values( eid, { input_name: msg_id }, 'input' )

            # Conduct a zero-length step to process inputs
            fmu.doStep(
                current_communication_point = self.fmutimes[eid],
                communication_step_size = 0.
                )

            next_event_time = fmu.getReal( [ self.event_var_name ] )[0]
            if self.verbose: print( 'FMU: next_event_time = {}'.format( next_event_time ) )
            self.fmuwanttimes[eid] = next_event_time

        #Update our external belief about the current time
        self.current_time = time

        return time + 1


    def get_data(self, outputs):
        '''Function for obtaining FMU output during co-simulation process.'''
        data = {}
        # print('Got get_data request {0}'.format(outputs))
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == 'current_time':
                    data[eid][attr] = self.current_time
                    # print('current time: ', self.current_time)
                else:
                    receive = attr
                    send = receive.replace( '_receive', '_send' )
                    data[eid][receive] = self.outqueue[eid][send] if send in self.outqueue[eid] else None


        return data

    def adjust_var_table(self):
        '''Helper function that adds missing keys to the var_table and its associated translation table.
        Avoids errors due to faulty access later on.'''
        self.var_table.setdefault('parameter', {})
        self.var_table.setdefault('input', {})
        self.var_table.setdefault('output', {})

        self.translation_table.setdefault('parameter', {})
        self.translation_table.setdefault('input', {})
        self.translation_table.setdefault('output', {})

    def set_values(self, eid, val_dict, var_type):
        '''Helper function to set input variable and parameter values to a FMU instance'''
        for alt_name, val in val_dict.items():
            name = self.translation_table[var_type][alt_name]
            # Obtain setter function according to specified var type (Real, Integer, etc.):
            set_func = getattr(self._entities[eid], 'set' + self.var_table[var_type][name])
            set_func( [ name ], [ val ] )

    def get_value(self, eid, alt_attr):
        '''Helper function to get output variable values from a FMU instance.'''
        attr = self.translation_table['output'][alt_attr]
        # Obtain getter function according to specified var type (Real, Integer, etc.):
        get_func = getattr(self._entities[eid], 'get' + self.var_table['output'][attr])
        val = get_func( [ attr ] )[0]
        #if val is not 0: print( 'TC3CommNetwork::get_value attr = {}, val = {}'.format( attr, val ) )
        return val


if __name__ == '__main__':
    mosaik_api.start_simulation( TC3CommNetwork() )