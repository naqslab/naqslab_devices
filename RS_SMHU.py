#####################################################################
#                                                                   #
# /RS_SMHU.py                                                       #
#                                                                   #
#                                                                   #
#####################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from labscript_devices.SignalGenerator import *
import labscript_utils.properties
from labscript import LabscriptError
        
@labscript_device              
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

@BLACS_tab
class RS_SMHUTab(SignalGeneratorTab):
    # Capabilities
    base_units = {'freq':'MHz', 'amp':'dBm'}
    base_min = {'freq':0.1,   'amp':-140}
    base_max = {'freq':4320,  'amp':13}
    base_step = {'freq':1,    'amp':0.1}
    base_decimals = {'freq':7, 'amp':1}
    # Event Byte Label Definitions for RS SMHU
    status_byte_labels = {'bit 7':'Power On', 
                          'bit 6':'URQ',
                          'bit 5':'Command Error',
                          'bit 4':'Execution Error',
                          'bit 3':'Device-Dependent Error',
                          'bit 2':'Query Error',
                          'bit 1':'SRQ',
                          'bit 0':'OPC'}
    
    def __init__(self,*args,**kwargs):
        self.device_worker_class = RS_SMHUWorker
        SignalGeneratorTab.__init__(self,*args,**kwargs)      

@BLACS_worker
class RS_SMHUWorker(SignalGeneratorWorker):
    # define the scale factor
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6
    amp_scale_factor = 1.0
    
    def init(self):
        '''Calls parent init and sends device specific initialization commands'''
        SignalGeneratorWorker.init(self)
        
        # enables ESR status reading
        self.connection.write('HEADER:OFF;*ESE 60;*SRE 32;*CLS')
        self.esr_mask = 60
    
    # define instrument specific read and write strings for Freq & Amp control
    freq_write_string = 'RF {:.1f}HZ' 
    freq_query_string = 'RF?'
    def freq_parser(self,freq_string):
        '''Frequency Query string parser for RS SMHU
        freq_string format is sdddddddddd.d
        Returns float in instrument units, Hz (i.e. needs scaling to base_units)'''
        return float(freq_string)
    amp_write_string = 'LEVEL:RF {:.1f}DBM'
    amp_query_string = 'LEVEL:RF?'
    def amp_parser(self,amp_string):
        '''Amplitude Query string parser for RS SMHU
        amp_string format is sddd.d
        Returns float in instrument units, dBm'''
        if amp_string == '\n':
            raise LabscriptError('RS SMHU device {0:s} has RF OFF!'.format(self.VISA_name))
        return float(amp_string)
            
    def check_status(self):
        # no real info in stb in these older sig gens, use esr instead
        esr = int(self.connection.query('*ESR?'))
        
        # if esr is non-zero, read out the error message and report
        # use mask to ignore non-error messages
        if (esr & self.esr_mask) != 0:
            err_string = self.connection.query('ERRORS?')
            # some error conditions do not persist to ERRORS? query (ie query errors)
            # Still need to inform user of issue
            if err_string.endswith('0'):
                err_string = 'Event Status Register: {0:d}'.format(esr)
            else:
                raise LabscriptError('RS SMHU device {0:s} has \n{1:s}'.format(self.VISA_name,err_string)) 
        
        # note: SMHU has 9 bits in ESR, 
        # so need to ensure last bit (Sweep End) not present when passed
        return self.convert_register(esr & 255)

