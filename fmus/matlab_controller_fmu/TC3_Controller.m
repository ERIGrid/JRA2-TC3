classdef TC3_Controller < fmipputils.FMIAdapter

	properties
	
		tap_ = 0;

	end % properties


	methods
		
		function init( obj, currentCommunicationPoint )

			% Define inputs (of type real).
			inputVariableNames = { 'u3', 'u4', 'vup', 'vlow' };
			obj.defineRealInputs( inputVariableNames );

			% Define outputs (of type int).
			outputVariableNames = { 'tap' };
			obj.defineIntegerOutputs( outputVariableNames );
			
			disp( 'FMI++ backend for co-simulation: INIT DONE.' );

		end % function init


		function doStep( obj, currentCommunicationPoint, communicationStepSize )
			
			syncTime = currentCommunicationPoint + communicationStepSize;

			if ( communicationStepSize ~= 0 ) % Update internal state of controller
				%disp('update state');
				;
			else
				%disp('iterate');
				obj.decideOnTap();
				obj.setIntegerOutputValues( obj.tap_ );
			end


		end % function doStep

		
		function decideOnTap( obj )

			% Read current input values.
			realInputValues = obj.getRealInputValues();
			u3 = realInputValues(1);
			u4 = realInputValues(2);
			vup = realInputValues(3);
			vlow = realInputValues(4);

			umin = min( u3, u4 );
			umax = max( u3, u4 );
			
			if ( umax > vup )
				obj.tap_ = obj.tap_ + 1;
			end
			
			if ( umin < vlow )
				obj.tap_ = obj.tap_ - 1;
			end
			
		end % function decideOnTap
		
	end % methods

end % classdef