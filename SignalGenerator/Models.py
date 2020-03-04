#####################################################################
#                                                                   #
# /naqslab_devices/SignalGenerator/Models.py                        #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

from naqslab_devices.SignalGenerator.labscript_device import SignalGenerator
from labscript import set_passed_properties, LabscriptError

__version__ = '0.1.0'
__author__ = ['dihm']
                     
class RS_SMF100A(SignalGenerator):
    description = 'Rhode & Schwarz SMF100A Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e9 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (100e3, 22e9) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-26, 18) # set in scaled unit (dBm) 
    
class RS_SMHU(SignalGenerator):
    description = 'RS SMHU Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (100e3, 4320e6) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-140, 13) # set in scaled unit (dBm)
    # Output high can be adjusted up to 19dBm without spec guarantee
    # above 13 will generate error warnings
    
class HP_8642A(SignalGenerator):
    description = 'HP 8642A Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (100e3, 1057.5e6) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-140, 20) # set in scaled unit (dBm)
    # Output limits depend on frequency. Can be as low as 17 dBm

class HP_8643A(SignalGenerator):
    description = 'HP 8643A Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (260e3, 1030e6) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-137, 13) # set in scaled unit (dBm)
    
class HP_8648A(SignalGenerator):
    description = 'HP 8648A Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (100e3, 1000e6) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-136, 20) # set in scaled unit (dBm)
    # Output limits depend on frequency. Can be as low as 10 dBm
    
class HP_8648B(SignalGenerator):
    description = 'HP 8648B Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (9e3, 2000e6) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-136, 20) # set in scaled unit (dBm)
    # Output limits depend on frequency. Can be as low as 10 dBm
    
class HP_8648C(SignalGenerator):
    description = 'HP 8648C Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (9e3, 3200e6) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-136, 20) # set in scaled unit (dBm)
    # Output limits depend on frequency. Can be as low as 10 dBm
    
class HP_8648D(SignalGenerator):
    description = 'HP 8648D Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (9e3, 4000e6) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-136, 20) # set in scaled unit (dBm)
    # Output limits depend on frequency. Can be as low as 10 dBm
    
class SRS_SG380(SignalGenerator):
    description = 'Base SG380 device class that defines option'
    # define allowed outputs
    outputs = ['DC','RF','Doubled_RF']
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    # define variable limit
    RF_freq_max = 0
    
    @set_passed_properties(property_names = {
        'connection_table_properties': ['output','freq_limits','amp_limits',
                                    'mod_type']
        })
    def __init__(self, name, VISA_name, output='RF', mod_type='AM'):
        """Saves the user specified output to use and saves for reading by
        BLACS_Tab.
        
        Specific models of this series subclass this class.
        
        Args:
            name (str): variable name to create labscript_device under
            VISA_name (str): the VISA connection string to the physical device
            output (str): Selects which output of the SG380 to use. Options are
                    'DC', 'RF', and 'Doubled_RF'. Defaults to 'RF'.
            mod_type (str): Selects which modulation type to use. Options are
                    'AM', 'FM', 'PM', 'Sweep'. Defaults to 'AM'.
        """
        # set in scaled unit (Hz)
        freq_capabilities = {'DC': (0,62.5e6),
                         'RF': (950e3,self.RF_freq_max),
                         'Doubled_RF': (self.RF_freq_max,8100e6)}
        
        # set in scaled unit (dBm)                 
        amp_capabilities = {'DC': (-47,15), # calibrated output only to 13
                         'RF': (-110,16.5), # high depends on frequency
                         'Doubled_RF': (-10,16.5)} # high depends on frequency
        
        if output in self.outputs:
            self.output = output
            self.freq_limits = freq_capabilities[output]
            self.amp_limits = amp_capabilities[output]
        else:
            msg = f'''{output} is not a valid output option.
            Please select from {self.outputs}
            '''
            raise LabscriptError(msg)
            
        # set modulation stuff here
        self.mod_type = mod_type
        
        # finish initialization with parent __init__
        SignalGenerator.__init__(self,name,VISA_name)

class SRS_SG382(SRS_SG380):
    description = 'Stanford Research Systems SG382 Signal Generator'
    RF_freq_max = 2.025e9
    outputs = ['DC','RF'] # doubled output option not available for this device

class SRS_SG384(SRS_SG380):
    description = 'Stanford Research Systems SG384 Signal Generator'
    RF_freq_max = 4.050e9

class SRS_SG386(SRS_SG380):
    description = 'Stanford Research Systems SG386 Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    RF_freq_max = 6.075e9
