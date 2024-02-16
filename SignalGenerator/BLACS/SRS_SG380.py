#####################################################################
#                                                                   #
# /naqslab_devices/SignalGenerator/BLACS/SRS_SG380.py               #
#                                                                   #
# Copyright 2019, Zac Castillo                                      #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from naqslab_devices.SignalGenerator.blacs_tab import SignalGeneratorTab
from naqslab_devices.SignalGenerator.blacs_worker import SignalGeneratorWorker
from naqslab_devices.VISA.blacs_worker import VISAWorker
from labscript import LabscriptError
from naqslab_devices.SignalGenerator.modulationcontrol import ModulationControl
from labscript_utils import dedent


class SRS_SG380Tab(SignalGeneratorTab):
    # Capabilities
    base_units = {'freq':'MHz', 'amp':'dBm'}
    base_step = {'freq':1,    'amp':1}
    base_decimals = {'freq':9, 'amp':2}

    # Event Status Byte Label Definitions for SRS_SG380 models
    status_byte_labels = {'bit 7':'Power On',
                          'bit 6':'Reserved',
                          'bit 5':'Command Error',
                          'bit 4':'Execution Error',
                          'bit 3':'Device Error',
                          'bit 2':'Query Error',
                          'bit 1':'Reserved',
                          'bit 0':'Operation Complete'}

    device_properties = {}
    
    # Define modulation settings
    # Note that these settings are the maximum values
    # Actual max/min values depend on present settings of box                      
    mod_defs = {'AM':{'DEV':{'min':0,'max':100,'step':1,'decimals':1,
                              'base_unit':'%','default':0},
                      'RATE':{'min':1e-6,'max':500e3,'step':1,'decimals':6, # all internal mod rates depend on center frequency band
                              'base_unit':'Hz','default':1e3}},
                'FM':{'DEV':{'min':0.1,'max':64e6,'step':1,'decimals':1, #max dev depends on center frequency band
                              'base_unit':'Hz','default':1e3},
                      'RATE':{'min':1e-6,'max':500e3,'step':1,'decimals':6,
                              'base_unit':'Hz','default':1e3}},
                'PM':{'DEV':{'min':0,'max':360,'step':1,'decimals':2,
                              'base_unit':'deg','default':0},
                      'RATE':{'min':1e-6,'max':500e3,'step':1,'decimals':6,
                              'base_unit':'Hz','default':1e3}},
                'Sweep':{'DEV':{'min':0.1,'max':4.4e9,'step':1,'decimals':1, #range depends heavily on center frequency band
                              'base_unit':'Hz','default':0},
                      'RATE':{'min':1e-6,'max':120,'step':1,'decimals':6,
                              'base_unit':'Hz','default':10}}}
    
    def __init__(self,*args,**kwargs):
        self.device_worker_class = SRS_SG380Worker
        SignalGeneratorTab.__init__(self,*args,**kwargs)
        
    def initialise_GUI(self):
        
        # get connection_table properties for configuration
        connection_object = self.settings['connection_table'].find_by_name(self.device_name)
        conn_props = connection_object.properties
        self.freq_limits = conn_props.get('freq_limits',None)
        self.scale_factor = conn_props.get('scale_factor',1)
        self.amp_limits = conn_props.get('amp_limits',None)
        self.amp_scale_factor = conn_props.get('amp_scale_factor',1)
        self.output = conn_props.get('output','RF')
        self.mod_type = conn_props.get('mod_type','AM')
        
        # use labscript_device defined freq limits to set BLACS Tab limits
        # need to convert from scaled unit to do so
        self.base_min = {'freq':self.freq_limits[0]/self.scale_factor, 
                         'amp':self.amp_limits[0]/self.amp_scale_factor}
                            
        self.base_max = {'freq':self.freq_limits[1]/self.scale_factor,
                               'amp':self.amp_limits[1]/self.amp_scale_factor}
        
        # send properties to worker
        self.worker_init_kwargs = {'output':self.output,'mod_type':self.mod_type}
        
        self.device_properties = {'freq_mod': self.initialise_ModControl()}
        
        # call parent to finish initialisation of GUI
        SignalGeneratorTab.initialise_GUI(self)
                
        
    def initialise_ModControl(self):
        mod_controls = {'MODL':{'default':False,'type':'bool'},
                        'COUP':{'default':'AC','type':'enum','return_type':'index','options':['AC','DC']},
                        'FNC':{'default':'Sine','type':'enum','return_type':'index','options':
                                {'Sine':0,'Ramp':1,'Triangle':2,'Square':3,'External':5}},
                        'RATE':{'type':'num'},
                        'DEV':{'type':'num'}}
                        
        mod_controls['RATE'].update(self.mod_defs[self.mod_type]['RATE'])
        mod_controls['DEV'].update(self.mod_defs[self.mod_type]['DEV'])
        
        #self.device_properties.update(mod_controls)
        self.create_device_properties(mod_controls)
        modWidget = ModulationControl(f'{self.mod_type} Control')
        
        for key in mod_controls:
            prop = self.get_property(key)
            widget = modWidget.get_sub_widget(key)
            prop.add_widget(widget)
            
        return modWidget
        
        

class SRS_SG380Worker(SignalGeneratorWorker):
    
    def init(self):
        '''Calls parent init and sends device specific initialization commands'''        
        # initialize VISA interface
        VISAWorker.init(self)
        try:
            ident_string = self.connection.query('*IDN?')
        except:
            msg = '\'*IDN?\' command did not complete. Is %s connected?'
            raise LabscriptError(dedent(msg%self.VISA_name)) from None
        
        if 'SG38' not in ident_string:
            msg = '%s is not supported by the SRS_SG380 class.'
            raise LabscriptError(dedent(msg%ident_string))
        
        # log which device connected to worker terminal
        print('Connected to \n', ident_string)

        # enables ESR status reading
        self.connection.write('*ESE 60;*SRE 32;*CLS')
        self.esr_mask = 60
    
        # define instrument specific read and write strings for Freq & Amp control
        # may need to extend to other two outputs
        self.freq_write_string = 'FREQ {:.6f} HZ' # in Hz
        self.freq_query_string = 'FREQ?' #SRS_SG380 returns float, in Hz
        
        # define amplitude string based on which output is selected
        self.amp_outputs = {'DC':'L','RF':'R','Doubled_RF':'H'}
        self.amp_write_string = 'AMP'+self.amp_outputs[self.output]+'{:.2f}' # in dBm
        self.amp_query_string = 'AMP'+self.amp_outputs[self.output]+'? ' # in dBm
        # define correct output enable command strings
        self.enable_write_string = 'ENB'+self.amp_outputs[self.output]+'{:1d}'
        self.enable_query_string = 'ENB'+self.amp_outputs[self.output]+'?'
        
        # define modulation control read/write strings
        self.mod_strings = {'AM':{'FNC':'MFNC','DEV':'ADEP','RATE':'RATE'},
                            'FM':{'FNC':'MFNC','DEV':'FDEV','RATE':'RATE'},
                            'PM':{'FNC':'MFNC','DEV':'PDEV','RATE':'RATE'},
                            'Sweep':{'FNC':'SFNC','DEV':'SDEV','RATE':'SRAT'}}
        
        # initialize sig-gen now that write/query strings are defined
        SignalGeneratorWorker.init(self)
    
    def freq_parser(self,freq_string):
        '''Frequency Query string parser for SRS_SG380
        freq_string format is float, in Hz
        Returns float in instrument units, Hz (i.e. needs scaling to base_units)'''
        return float(freq_string)
    
    def amp_parser(self,amp_string):
        '''Amplitude Query string parser for SRS_SG380
        amp_string format is float in configured units (dBm by default)
        Returns float in instrument units, dBm'''
        return float(amp_string)
        
    def program_properties(self,values):
        # TODO: This needs to be cleaned up a lot
        # Likely when the meta_class gets implemented
        # need some validation here since output frequency sets valid ranges
        vals = values.copy()
        mod_strings = self.mod_strings[self.mod_type]
        
        if 'MODL' in vals:
            # mod enable
            self.connection.write(f"MODL{vals.pop('MODL'):d}")
        if 'COUP' in vals:
            # set external input coupling
            self.connection.write(f"COUP{vals.pop('COUP'):d}")
        if 'FNC' in vals:
            self.connection.write(f"{mod_strings['FNC']}{vals.pop('FNC'):d}")
        if 'DEV' in vals:
            self.connection.write(f"{mod_strings['DEV']}{vals.pop('DEV'):e}")
        if 'RATE' in vals:
            self.connection.write(f"{mod_strings['RATE']}{vals.pop('RATE'):e}")
        
        return values
        
    def check_status(self):
        # no real info in stb, use esr instead
        esr = int(self.connection.query('*ESR?'))
        
        # if esr is non-zero, read out the error message and report
        # use mask to ignore non-error messages
        if (esr & self.esr_mask) != 0:
            err_list = []
            while True:
                err_code = int(self.connection.query('LERR?'))
                if err_code !=0:
                    err_list.append(err_code)
                else:
                    break
            msg = '{0:s} has errors\n	{1:}'
            raise LabscriptError(dedent(msg.format(self.VISA_name,err_list))) 
        
        return self.convert_register(esr)
