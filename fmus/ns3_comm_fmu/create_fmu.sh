#!/bin/sh

# Specify path to ns-3 (with package 'fmi-export' and 'fmu-examples' installed).
NS3_PATH=/cygdrive/c/Development/erigrid/ns-3-allinone/ns-3-dev

# Specify FMI model identifier (i.e., the name of the FMU).
FMI_MODEL_ID=TC3_SimICT

# Just to be on the safe side: delete old FMU.
rm -rf ${FMI_MODEL_ID}.fmu

# Set ns-3 compiler flags for Cygwin.
export CXXFLAGS="-D_USE_MATH_DEFINES -D_BSD_SOURCE -include limits.h"

# Create FMU using Python script 'ns3_fmu_create.py'.
${NS3_PATH}/src/fmi-export/ns3_fmu_create.py -v -m ${FMI_MODEL_ID} -s TC3.cc -f 1
