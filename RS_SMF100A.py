#####################################################################
#                                                                   #
# /RS_SMF100A.py                                                    #
#                                                                   #
#                                                                   #
#####################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from labscript_devices.SignalGenerator import *
from labscript import LabscriptError
import labscript_utils.properties
        
@labscript_device              
class RS_SMF100A(SignalGenerator):
    description = 'Rhode & Schwarz SMF100A Signal Generator'
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e9 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (100e3, 22e9) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-26, 18) # set in scaled unit (dBm)        
        

@BLACS_tab
class RS_SMF100ATab(SignalGeneratorTab):
    # Capabilities
    base_units = {'freq':'GHz', 'amp':'dBm'}
    base_min = {'freq':1e-6,   'amp':-26}
    base_max = {'freq':22,  'amp':18}
    base_step = {'freq':0.1,    'amp':1}
    base_decimals = {'freq':6, 'amp':1}
    # Status Byte Label Definitions for SMF100A
    status_byte_labels = {'bit 7':'Operation', 
                          'bit 6':'SRQ',
                          'bit 5':'ESB',
                          'bit 4':'Message Available',
                          'bit 3':'Questionable Status',
                          'bit 2':'Error Queue Not Empty',
                          'bit 1':'Unused',
                          'bit 0':'Unused'}

    def __init__(self,*args,**kwargs):
        self.device_worker_class = RS_SMF100AWorker
        SignalGeneratorTab.__init__(self,*args,**kwargs)

@BLACS_worker
class RS_SMF100AWorker(SignalGeneratorWorker):
    # define the scale factor
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e9
    amp_scale_factor = 1.0
    
    # define instrument specific read and write strings for Freq & Amp control
    freq_write_string = 'FREQ:CW {:.0f}HZ'
    freq_query_string = 'FREQ?' #SMF100A returns 'ddddddddddd', in Hz
    def freq_parser(self,freq_string):
        '''Frequency Query string parser for SMF100A
        freq_string format is ddddddddddd
        Returns float in instrument units, Hz (i.e. needs scaling to base_units)'''
        return float(freq_string)
    amp_write_string = 'POW:POW {:.2f}dBm' #SMF100A accepts two decimals, in dBm
    amp_query_string = 'POW?' #SMF100A returns 'sdd.dd'
    def amp_parser(self,amp_string):
        '''Amplitude Query string parser for SMF100A
        Returns float in instrument units, dBm'''
        return float(amp_string)
        
    def check_status(self):
        # call parent method to read status byte register
        results = SignalGeneratorWorker.check_status(self)
        # do some device specific error handling with status byte information
        if results['bit 2'] == True:
            errors = self.connection.query('SYST:ERR:ALL?')
            raise LabscriptError('SMF100A VISA device {:s} has Errors in Queue: \n{:s}'.format(self.VISA_name,errors))
            
        return results
