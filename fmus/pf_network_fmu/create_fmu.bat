@ECHO OFF

REM Adapt the line below to point to your installation of the FMI++ PowerFactory FMU Export Utility.
SET PF_FMU_EXPORT_UTILITY_PATH=C:\Development\erigrid\powerfactory-fmu-v0.6

REM Specify FMI model identifier.
SET FMI_MODEL_ID=TC3_PowerSystem

REM Specify the PowerFactory model file.
SET PF_MODEL=Erigrid_LV.pfd

REM Create the FMU.
python %PF_FMU_EXPORT_UTILITY_PATH%\powerfactory_fmu_create.py -v -m %FMI_MODEL_ID% -p %PF_MODEL% -i inputs.txt -o outputs.txt -t FileTrigger:60

PAUSE