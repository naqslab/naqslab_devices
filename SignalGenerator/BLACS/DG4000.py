#####################################################################
#                                                                   #
# /naqslab_devices/SignalGenerator/BLACS/DG4000.py                  #
#                                                                   #
# Copyright 2025, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from naqslab_devices.SignalGenerator.blacs_tab import SignalGeneratorTab
from naqslab_devices.SignalGenerator.blacs_worker import SignalGeneratorWorker, enable_on_off_formatter
from naqslab_devices.VISA.blacs_worker import VISAWorker
from labscript import LabscriptError
from labscript_utils import dedent


class DG4000Tab(SignalGeneratorTab):
    # Capabilities
    base_min = {'freq': 1e-6, 'amp':1e-3}
    base_units = {'freq':'Hz', 'amp':'Vpp'}
    base_step = {'freq':1e5,    'amp':0.1}
    base_decimals = {'freq':6, 'amp':4}

    # Event Status Byte Label Definitions for DG4000 models
    status_byte_labels = {'bit 7':'Unknown',
                          'bit 6':'Unknown',
                          'bit 5':'Unknown',
                          'bit 4':'Unknown',
                          'bit 3':'Unknown',
                          'bit 2':'Unknown',
                          'bit 1':'Unknown',
                          'bit 0':'Unknown'}
    
    def __init__(self,*args,**kwargs):
        self.device_worker_class = DG4000Worker
        SignalGeneratorTab.__init__(self,*args,**kwargs)
        
    def initialise_GUI(self):
        
        # get connection_table properties for configuration
        connection_object = self.settings['connection_table'].find_by_name(self.device_name)
        conn_props = connection_object.properties
        self.freq_max = conn_props.get('freq_max')
        
        # use labscript_device defined freq limits to set BLACS Tab limits
        # need to convert from scaled unit to do so
                            
        self.base_max = {'freq':self.freq_max,
                        'amp':10.0} # output impedance dependent
        
        # call parent to finish initialisation of GUI
        SignalGeneratorTab.initialise_GUI(self)


class DG4000Worker(SignalGeneratorWorker):
    
    def init(self):
        '''Calls parent init and sends device specific initialization commands'''        
        # initialize VISA interface
        VISAWorker.init(self)
        try:
            ident_string = self.connection.query('*IDN?')
        except Exception:
            msg = '\'*IDN?\' command did not complete. Is %s connected?'
            raise LabscriptError(dedent(msg%self.VISA_name)) from None
        
        if 'DG4' not in ident_string:
            msg = '%s is not supported by the DG4000 class.'
            raise LabscriptError(dedent(msg%ident_string))
        
        # log which device connected to worker terminal
        print('Connected to \n', ident_string)
    
        # define instrument specific read and write strings for Freq & Amp control
        self.freq_write_string = 'SOUR{chan:d}:FREQ:FIX {:.6f}' # in Hz
        self.freq_query_string = 'SOUR{chan:d}:FREQ:FIX?' # DG4000 returns float, in Hz
        
        # define amplitude string
        self.amp_write_string = 'SOUR{chan:d}:VOLT {:.4f}' # in Vpp
        self.amp_query_string = 'SOUR{chan:d}:VOLT?' # in Vpp
        
        # initialize sig-gen now that write/query strings are defined
        SignalGeneratorWorker.init(self)

    # define correct output enable command strings
    enable_write_string = enable_on_off_formatter('OUTP{chan:d}:STAT {:s}')
    enable_query_string = 'OUTP{chan:d}:STAT?'
    def enable_parser(self,enable_string):
        '''Output Enable Query for DG4000.'''
        return 'ON' in enable_string
    
    def freq_parser(self,freq_string):
        '''Frequency Query string parser for DG4000
        freq_string format is float, in Hz
        Returns float in instrument units, Hz (i.e. needs scaling to base_units)'''
        return float(freq_string)
    
    def amp_parser(self,amp_string):
        '''Amplitude Query string parser for SDG4000
        amp_string format is float in configured units (Vpp by default)
        Returns float in instrument units, Vpp'''
        return float(amp_string)
        
    def check_status(self):
        # no real info in stb, use esr instead
        esr = int(self.connection.query('*ESR?'))
        
        # if esr is non-zero, read out the error message and report
        # use mask to ignore non-error messages
        if (esr) != 0:
            err_list = []
            while True:
                err = int(self.connection.query('SYST:ERR?'))
                err_code = int(err.split(',')[0])
                if err_code !=0:
                    err_list.append(err_code)
                else:
                    break
            msg = '{0:s} has errors\n	{1:}'
            raise LabscriptError(dedent(msg.format(self.VISA_name,err_list))) 
        
        return self.convert_register(esr)
