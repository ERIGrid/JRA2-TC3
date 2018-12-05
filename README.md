[![DOI](https://zenodo.org/badge/160505455.svg)](https://zenodo.org/badge/latestdoi/160505455)

# ERIGrid JRA2: Test case TC3 mosaik implementation

A detailed description of test case TC3 can be found in [ERIGrid deliverable D-JRA2.2](https://erigrid.eu/dissemination/).
In the following, a step-by-step instruction on how to run the TC3 co-simulation is provided as well as a brief description of the simulation components.


## Prerequisites (Windows)

- **Python** (test with Python 3.6.4 32-bit)
- **PowerFactory** (tested with PowerFactory 2017 SP5 x86) and the [**FMI++ PowerFactory FMU Export Utility**](https://sourceforge.net/projects/powerfactory-fmu/)
- **MATLAB** (tested with MATLAB R2015b 32-bit) and the [**FMI++ MATLAB Toolbox for Windows**](https://sourceforge.net/projects/matlab-fmu/)
- **ns-3** (installed in [Cygwin](https://www.cygwin.com/) environment, see documentation for ns-3 module fmi-export) with the extra modules [**fmi-export and fmu-examples**](https://erigrid.github.io/ns3-fmi-export/)

**ATTENTION**: The co-simulation toolchain needs to be completely in either 32-bit or 64-bit.
For TC3 it was decided to use consistently **32-bit** for Windows setups.
Therefore, be sure to install **32-bit versions of all tools** (Python, PowerFactory, MATLAB, Cygwin)!


## Installation (Windows)

1. install all the tool listed in the prerequisites above (including the FMI-compliant interfaces)

2. in the Windows command line, install required Python packages via *pip* by running:
```
      pip install -r requirements.txt
```

3. in the Cygwin terminal, install required Python packages using *pip* (see details below)

4. create the FMUs (see details below)


### Install Cygwin Python packages

It is recommended to install everything into a virtual Python environment called *tc3*:
```
   pip2 install virtualenv virtualenvwrapper
   source /usr/bin/virtualenvwrapper.sh
   mkvirtualenv tc3
   pip2 install mosaik_api
```

**NOTE**:
It is not necessarily required to create this virtual Python environment.
However, if you prefer not to use one, you have to edit file *tc3_comm_ns3_fmu.sh* accordingly.


### Creating the MATLAB FMU

- open MATLAB and go to subfolder *fmus\matlab_controller_fmu*
- run MATLAB script *create_fmu.m*
- copy the resulting FMU to subfolder *fmus*


### Creating the PowerFactory FMU

- go to subfolder *fmus\pf_network_fmu*
- adapt batch script *create_fmu.bat* to fit your installation (path to FMI++ PowerFactory FMU Export Utility)
- run batch script *create_fmu.bat* (e.g., double-click it)
- copy the resulting FMU to subfolder *fmus*


### Creating the ns-3 FMU

- open a Cygwin terminal and go to subfolder *fmus\ns3_comm_fmu*
- adapt shell script *create_fmu.sh* to fit your installation (path to ns-3 installation)
- run shell script *create_fmu.sh*
- copy the resulting FMU to subfolder *fmus*


## Running the simulation (Windows)

There are two scenarios included here:

The first scenario uses FMUs on a Windows PC. For this scenario, DIgSILENT PowerFactory, MATLAB and ns-3 need to be installed and the associated FMUs have to be available (see above).

Because the ns-3 FMU has to be executed in a Cygwin environment, mosaik has to know the path to Cygwin's terminal application (*bash.exe*). For this reason, edit attribute *BASH_PATH* to point to *bash.exe* (beginning of file *tc3_scenario_fmu.py*).

For both scenarios, the time resolution of the simulation can be specified via parameter MT_PER_SEC, which defines the number of mosaik time steps per second (simulation time).

Once this is done, run the full TC3 scenario with this command:
```
   set CHERE_INVOKING=1
   python tc3_scenario_fmu.py
```

It is also possible to run variations of the scenario, for instance by changing ns-3's random generator seed and the number of dummy devices:
```
   set CHERE_INVOKING=1
   python tc3_scenario_fmu.py --random_seed=1234 --send_time_diff=0.01 --ctrl_dead_time=0.005
```

The second scenario does not include a communication network simulator. It is meant as a reference scenarion with "ideal" communication.
```
   python tc3_scenario_nocomm_fmu.py
```

Results from the simulations are stored in *erigridstore.h5* and can be plotted using:
```
   python tc3_analysis.py
```


## Brief description of component functionality

### TC3Controller

Takes voltage measurements 'u3' and 'u4' and calculates a desired tap setting, given to 'tap'. This implementation is intended to use an FMU that internally runs a control algorithm implemented in MATLAB.

### TC3PowerSystem

Simulates the power system, containing two loads and an OLTC transformer. This implementation is intended to use an FMU that internally uses PowerFactory.

### TC3CommNetwork

Simulates the communication network for sending measurements from the voltage meters to the controller and tap positions from the controller to the OLTC. This implementation is intended to use an FMU that internally runs ns-3 simulations.

NOTE: ns-3 is being developed for Linux. However, on Windows ns-3 can be run in a Cygwin environment. And FMUs using ns-3 also have to be executed on Windows within a Cygwin environment. Therefore, when using the TC3CommNetwork component, mosaik starts a Cygwin session (*bash.exe*) in which it runs and connects to the client component (with the help of shell script *tc3_comm_ns3_fmu.sh*).

### RampingLoad

Linearly ramps the output *L*  from *Llow* to *Lhigh* within a specified time span.

### PeriodicSender

Connecting *in* to a continuous time component will periodically raise *out* from None to the value of *in*.
This raising happens every *period* time steps, starting at *start_time*.

### TapActuator

Actuator for the OLTC transformer's tap position. Upon receiving a new tap position setpoint *tap_setpoint*, the actuator becomes unresponsive (i.e., it will not react to new setpoints) until it actuates the new tap position *tap_position* with a certain delay (parameter *dead_time*).
	
### Collector

Polls connected components every *timestep* mosaiktimes, saves results into the specified HDFstore.


## Troubleshooting

Error message:
```
/usr/bin/bash: ./tc3_comm_ns3_fmu.sh: No such file or directory
ERROR: Simulator "CommSim" did not connect to mosaik in time.
Mosaik terminating
```

Solution: You forgot to set variable `CHERE_INVOKING` before running mosaik.
```
   set CHERE_INVOKING=1
```
