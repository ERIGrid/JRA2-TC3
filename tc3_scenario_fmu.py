import mosaik
import mosaik.util
import os
import argparse
from pathlib import Path
from datetime import *

# Simulation stop time and scaling factor.
MT_PER_SEC = 500 # N ticks of mosaik time = 1 second
STOP = 120 * MT_PER_SEC # 2 minutes

# Adapt the following line to fit your Cygwin installation (path to bash.exe).
BASH_PATH = 'C:/Tools/cygwin/bin/bash.exe'

# FMU repository.
FMU_DIR = os.path.abspath( os.path.join( os.path.dirname( __file__ ), 'fmus' ) )

# Sim config.
SIM_CONFIG = {
        'CommSim': {
            'cmd': BASH_PATH + ' -lc "./tc3_comm_ns3_fmu.sh tc3 %(addr)s"',
            'cwd': Path( os.path.abspath( os.path.dirname( __file__ ) ) ).as_posix()
        },
        'LoadFlowSim':{
            'python': 'tc3_powersystem_pf_fmu:TC3PowerSystem'
        },
        'ControllerSim':{
            'python': 'tc3_controller_matlab_fmu:TC3Controller'
        },
        'RampingLoad':{
            'python': 'ramping_load:RampingLoad',
        },
        'PeriodicSender':{
            'python': 'periodic_sender:PeriodicSender',
        },
        'TapActuator':{
            'python': 'tap_actuator:TapActuator',
        },
        'Collector':{
            'python': 'collector:Collector',
        }
    }


def main():

    parser = argparse.ArgumentParser(description='Run a TC3 simulation with the SimICT component')
    parser.add_argument( '--ctrl_dead_time', type=float, help='controller deadtime in seconds', default=1 )
    parser.add_argument( '--send_time_diff', type=float, help='time difference between sending volatge readings', default=3 )
    parser.add_argument( '--random_seed', type=int, help='ns-3 random generator seed', default=1 )
    parser.add_argument( '--output_file', type=str, help='output file name', default='erigridstore.h5' )
    args = parser.parse_args()
    print( 'Starting simulation with args: {0}'.format( vars( args ) ) )

    world = mosaik.World( SIM_CONFIG )
    create_scenario( world, args )
    world.run( until=STOP )


def create_scenario( world, args ):

    # Simulator for ramping loads.
    ramp_load_sim= world.start( 'RampingLoad', eid_prefix='rampload_', step_size=1*MT_PER_SEC )
    ramp_load_bus3 = ramp_load_sim.RampingLoad.create( 1, Llow=0, Lhigh=2, ramp_time=STOP )[0]
    ramp_load_bus4 = ramp_load_sim.RampingLoad.create( 1, Llow=7, Lhigh=10, ramp_time=STOP )[0]

    # Periodic senders for voltage readings.
    periodic_sender_sim = world.start( 'PeriodicSender', verbose=False )
    sender_U3 = periodic_sender_sim.PeriodicSender( period=60.*MT_PER_SEC,
        start_time=args.send_time_diff*MT_PER_SEC )
    sender_U4 = periodic_sender_sim.PeriodicSender( period=60.*MT_PER_SEC )

    # Tap actuator.
    tap_actuator_sim = world.start( 'TapActuator', verbose=False )
    tap_actuator = tap_actuator_sim.TapActuator.create( 1, dead_time=3.*MT_PER_SEC )[0]

    # Simulator for power system.
    loadflow_sim = world.start( 'LoadFlowSim',
        work_dir=FMU_DIR, model_name='TC3_PowerSystem', instance_name='LoadFlow1',
        start_time=0, stop_time=STOP, stop_time_defined=True,
        step_size=1*MT_PER_SEC, seconds_per_mosaik_timestep=1/MT_PER_SEC, verbose=False )
    loadflow = loadflow_sim.TC3PowerSystem.create(1)[0]

    # Simulator for communication network.
    comm_network_sim = world.start( 'CommSim',
        work_dir=FMU_DIR, model_name='TC3_SimICT', instance_name='CommNetwork1',
        start_time=0, stop_time=STOP, stop_time_defined=True, random_seed=args.random_seed,
        seconds_per_mosaik_timestep=1./MT_PER_SEC, path_conversion='win2cygwin', posix=True, verbose=False )
    comm_network = comm_network_sim.TC3CommNetwork.create(1)[0]

    # Simulator for controller.
    controller_sim = world.start( 'ControllerSim',
        work_dir=FMU_DIR, model_name='TC3_Controller', instance_name='Controller1',
        start_time=0, stop_time=STOP, stop_time_defined=True,
        dead_time=args.ctrl_dead_time, seconds_per_mosaik_timestep=1./MT_PER_SEC, verbose=False )
    controller = controller_sim.TC3Controller.create(1)[0]

    # Connect ramping loads to power system.
    world.connect(ramp_load_bus3, loadflow, ('L', 'L_3'))
    world.connect(ramp_load_bus4, loadflow, ('L', 'L_4'))

    # Connect voltage U3 to controller.
    world.connect( loadflow, sender_U3, ('U3', 'in') )
    world.connect( sender_U3, comm_network, ( 'out', 'u3_send' ) )
    world.connect( comm_network, controller, ( 'u3_receive', 'u3' ),
        time_shifted=True, initial_data={ 'u3_receive': None }  )

    # Connect voltage U4 to controller.
    world.connect( loadflow, sender_U4, ('U4', 'in') )
    world.connect( sender_U4, comm_network, ( 'out', 'u4_send' ) )
    world.connect( comm_network, controller, ( 'u4_receive', 'u4' ),
        time_shifted=True, initial_data={ 'u4_receive': None }  )

    # Connect output from controller to OLTC.
    world.connect( controller, comm_network, ( 'tap', 'ctrl_send' ) )
    world.connect( comm_network, tap_actuator, ( 'ctrl_receive', 'tap_setpoint' ) )
    world.connect( tap_actuator, loadflow, ( 'tap_position', 'tap' ),
        time_shifted=True, initial_data={ 'tap_position': 0 } )

    # Collect results.
    collector = world.start( 'Collector',
        step_size=MT_PER_SEC, seconds_per_mosaik_timestep=1./MT_PER_SEC, print_results=False,
        h5_storename=args.output_file, h5_panelname='Monitor' )
    monitor = collector.Monitor()

    world.connect( ramp_load_bus3, monitor, 'L' )
    world.connect( ramp_load_bus4, monitor, 'L' )
    world.connect( loadflow, monitor, 'U3' )
    world.connect( loadflow, monitor, 'U4' )
    world.connect( loadflow, monitor, 'current_tap' )


if __name__ == '__main__':
    sim_start_time = datetime.now()

    # Run the simulation.
    main()

    delta_sim_time = datetime.now() - sim_start_time
    print( 'simulation took {} seconds'.format( delta_sim_time.total_seconds() ) )
