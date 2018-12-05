"""
    A controller implementing a (too) simple coordinated voltage control algorithm.
"""

import collections
import mosaik_api
from itertools import count
import fmipp
import xml.etree.ElementTree as ETree
import os.path


META = {
    'models': {
        'TC3Controller': {
            'public': True,
            'params': ['vlow', 'vup'],
            'attrs': ['u3', 'u4', 'tap'],
        },
    },
}



class TC3Controller(mosaik_api.Simulator):

    def __init__(self):
        super().__init__(META)
        self.data = collections.defaultdict(dict)
        self._entities = {}
        self.eid_counters = {}
        self.is_responsive = {}             # controller state regarding dead time
        self.wakeup_time = {}               # time stamp until end of dead time
        self.dead_time = 0                  # dead time of controller
        self.work_dir = None                # directory of FMU
        self.model_name = None              # model name of FMU
        self.instance_name = None           # instance name of FMU
        self.var_table = None               # dict of FMU variables (input, output, parameters)
        self.translation_table = None       # help dict if variable names cannot be parsed properly in Python
        self.logging_on = False             # FMI++ parameter
        self.time_diff_resolution = 1e-9    # FMI++ parameter
        self.timeout = 0                    # FMI++ parameter
        self.interactive = False            # FMI++ parameter
        self.visible = False                # FMI++ parameter
        self.start_time = 0                 # FMI++ parameter
        self.stop_time = 0                  # FMI++ parameter
        self.stop_time_defined = False      # FMI++ parameter
        self.uri_to_extracted_fmu = None
        self.sec_per_mt = 1                 # Number of seconds of internaltime per mosaiktime
        self.fmutimes = {}                  # Keeping track of each FMU's internal time
        self.verbose = False


    def init( self, sid, work_dir, model_name, instance_name, dead_time=0, start_time=0, stop_time=0,
        logging_on = False, time_diff_resolution=1e-9, timeout=0, interactive=False, visible=False,
        stop_time_defined=False, seconds_per_mosaik_timestep=1, var_table=None, translation_table=None,
        verbose=False ):

        self.dead_time = dead_time / seconds_per_mosaik_timestep
        self.work_dir = work_dir
        self.model_name = model_name
        self.instance_name = instance_name
        self.start_time = start_time
        self.stop_time = stop_time
        self.logging_on = logging_on
        self.time_diff_resolution = time_diff_resolution # How close should two events be to be considered equal?
        self.timeout = timeout
        self.interactive = interactive
        self.visible = visible
        self.stop_time_defined = stop_time_defined
        self.sec_per_mt = seconds_per_mosaik_timestep # Number of seconds of internaltime per mosaiktime (Default: 1, mosaiktime measured in seconds)
        self.verbose = verbose

        path_to_fmu = os.path.join(self.work_dir, self.model_name + '.fmu')
        if self.verbose: print('Attempted to extract FMU {0}, Path {1}'.format(path_to_fmu, self.work_dir))
        self.uri_to_extracted_fmu = fmipp.extractFMU(path_to_fmu, self.work_dir)
        assert self.uri_to_extracted_fmu is not None

        # If no variable table is given by user, parse the modelDescription.xml for a table -
        # however, this will not work properly for some FMUs due to varying conventions.
        xmlfile = os.path.join( self.work_dir, self.model_name, 'modelDescription.xml' )
        if var_table is None:
            self.var_table, self.translation_table = self.get_var_table( xmlfile )
        else:
            self.var_table = var_table
            self.translation_table = translation_table

        self.adjust_var_table()

        return self.meta


    def create(self, num, model, vlow=0.95, vup=1.05):
        counter = self.eid_counters.get(model, count())

        entities = []

        for i in range(num):
            eid = '%s_%s' % (model, next(counter))  # entity ID

            if self.verbose: print('{0}, {1}, {2}, {3}'.format(self.uri_to_extracted_fmu, self.model_name, self.logging_on, self.time_diff_resolution))

            fmu = fmipp.FMUCoSimulationV1( self.uri_to_extracted_fmu, self.model_name,
                self.logging_on, self.time_diff_resolution )
            self._entities[eid] = fmu

            status = self._entities[eid].instantiate( self.instance_name, self.timeout,
                self.visible, self.interactive )
            assert status == fmipp.fmiOK

            status = self._entities[eid].initialize( self.start_time*self.sec_per_mt,
                self.stop_time_defined, self.stop_time*self.sec_per_mt )
            assert status == fmipp.fmiOK

            self.data[eid] = { 'tap': 0 }
            self.set_values( eid, { 'u3': 1., 'u4': 1., 'vlow': vlow, 'vup': vup }, 'input' )

            self.is_responsive[eid] = True
            self.wakeup_time[eid] = None

            # Handling tracking internal fmu times
            self.fmutimes[eid] = self.start_time*self.sec_per_mt

            entities.append( { 'eid': eid, 'type': model, 'rel': [] } )

        return entities


    def step(self, time, inputs):
        #print( 'CONTROLLER called at t = {}, inputs = {}'.format( time, inputs ) )

        # This is the internal time.
        target_time = ( time + self.start_time )*self.sec_per_mt

        for eid, fmu in self._entities.items():
            status = fmu.doStep( self.fmutimes[eid], target_time - self.fmutimes[eid], True )
            assert status == fmipp.fmiOK

            self.fmutimes[eid] += target_time - self.fmutimes[eid]

        for eid, edata in self.data.items():
            input_data = inputs.get(eid, {})

            [ ( _, u3 ) ] = input_data['u3'].items() if 'u3' in input_data else [ ( None, None ) ]
            [ ( _, u4 ) ] = input_data['u4'].items() if 'u4' in input_data else [ ( None, None ) ]


            if True is self.is_responsive[eid]: # Controller is responsive.
                if u3 is not None or u4 is not None:
                    new_tap = self.decide_on_tap(eid, u3, u4)
                    edata['tap'] = new_tap
                    if self.verbose: print( "Decided on tap {} at time {}".format( new_tap, time ) )

                    # Enter dead time.
                    self.is_responsive[eid] = False
                    self.wakeup_time[eid] = time + self.dead_time
                else:
                    edata['tap'] = None # No inputs --> no output.
            else: # Controller is not responsive (dead time).
                if time >= self.wakeup_time[eid]:
                    self.wakeup_time[eid] = None
                    self.is_responsive[eid] = True

        return time + 1


    def decide_on_tap( self, eid, u3, u4 ):

        fmu_inputs = {}
        if u3 is not None: fmu_inputs['u3'] = u3
        if u4 is not None: fmu_inputs['u4'] = u4
        self.set_values( eid, fmu_inputs, 'input' )

        status = self._entities[eid].doStep( self.fmutimes[eid], 0, True )
        assert status == fmipp.fmiOK

        return self.get_value( eid, 'tap' )


    def get_data(self, outputs):
        data = {}
        for eid, edata in self.data.items():
            requests = outputs[eid]
            mydata = {}
            for attr in requests:
                try:
                    mydata[attr] = edata[attr] if self.is_responsive[eid] is True else None
                except KeyError:
                    raise RuntimeError("OLTC controller has no attribute {0}".format(attr))
            data[eid] = mydata
        return data


    def get_var_table( self, filename ):
        var_table = {}
        translation_table = {}

        base = ETree.parse(filename).getroot()
        mvars = base.find('ModelVariables')

        for var in mvars.findall('ScalarVariable'):
            causality = var.get('causality')
            name = var.get('name')
            if causality in ['input', 'output', 'parameter']:
                var_table.setdefault(causality, {})
                translation_table.setdefault(causality, {})
                # Variable names including '.' cannot be used in Python scripts - they get aliases with '_':
                if '.' in name:
                    alt_name = name.replace('.', '_')
                else:
                    alt_name = name
                translation_table[causality][alt_name] = name

                # Store variable type information:
                specs = var.getchildren()
                for spec in specs:
                    if spec.tag in ['Real', 'Integer', 'Boolean', 'String']:
                        var_table[causality][name] = spec.tag
                        continue

        return var_table, translation_table


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
            set_func = getattr(self._entities[eid], 'set' + self.var_table[var_type][name] + 'Value')
            set_stat = set_func(name, val)
            assert set_stat == fmipp.fmiOK


    def get_value(self, eid, alt_attr):
        '''Helper function to get output variable values from a FMU instance.'''
        attr = self.translation_table['output'][alt_attr]
        # Obtain getter function according to specified var type (Real, Integer, etc.):
        get_func = getattr(self._entities[eid], 'get' + self.var_table['output'][attr] + 'Value')
        val = get_func(attr)
        #if val is not 0: print( 'get_value attr = {}, val = {}'.format( attr, val ) )
        return val


if __name__ == '__main__':
    mosaik_api.start_simulation(TC3Controller())
