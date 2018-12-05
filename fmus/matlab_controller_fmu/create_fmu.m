% Init MATLAB FMI++ Export package. 
fmippPath = getenv( 'MATLAB_FMIPP_ROOT' );
run( fullfile( fmippPath, 'setup.m' ) );

% Create FMU.
model_identifier = 'TC3_Controller';
class_definition_file = 'TC3_Controller.m';
additional_files = '';
fmipputils.createFMU( model_identifier, class_definition_file, additional_files, false );