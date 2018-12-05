#!/usr/bin/bash

# Unset variables that may have been previously defined by another virtual environment.
unset WORKON_HOME
unset _OLD_VIRTUAL_PATH

# NOTE: There are potentially also other previously defined variables that may cause problems 
# when starting a virtual environment (VENV, VIRTUALENVWRAPPER_PROJECT_FILENAME, VIRTUAL_ENV,
# _OLD_VIRTUAL_PROMPT, etc.).

# Declare Python version to be used for virtualenv.
#export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3

# Init virtualenvwrapper.
source /usr/bin/virtualenvwrapper.sh

# Start virtual environment.
workon $1

# Start the collector.
python tc3_comm_ns3_fmu.py $2
