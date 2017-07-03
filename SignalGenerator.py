#####################################################################
#                                                                   #
# /Signal Generator.py                                              #
#                                                                   #
#                                                                   #
#####################################################################

import numpy as np
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from labscript_devices.VISA import VISA, VISATab, VISAWorker
from labscript import Device, StaticDDS, StaticAnalogQuantity, config, LabscriptError, set_passed_properties
import labscript_utils.properties

class StaticFreqAmp(StaticDDS):
    """A Static Frequency that supports frequency and amplitude control."""
    description = 'Frequency Source class for Signal Generators'
    allowed_children = [StaticAnalogQuantity]
    
    @set_passed_properties()    
    def __init__(self, name, parent_device, connection, freq_limits = (0.1,1057.5), freq_conv_class = None,freq_conv_params = {}, amp_limits = (-140,20), amp_conv_class = None, amp_conv_params = {}):
        """Frequency and amplitude limits should be respected to ensure device is not sent out of range."""
        Device.__init__(self,name,parent_device,connection)
        self.frequency = StaticAnalogQuantity(self.name+'_freq',self,'freq',freq_limits,freq_conv_class,freq_conv_params)
        self.frequency.default_value = freq_limits[0]
        self.amplitude = StaticAnalogQuantity(self.name+'_amp',self,'amp',amp_limits,amp_conv_class,amp_conv_params)
        self.amplitude.default_value = amp_limits[0]
        
    def setphase(self,value,units=None):
        raise LabscriptError('StaticFreqAmp does not support phase control')
            
    def enable(self):       
        """overridden from StaticDDS so as not to provide time resolution -
        output can be enabled or disabled only at the start of the shot"""
        #self.gate.go_high() # don't think this is needed
        raise LabscriptError('StaticFreqAmp %s does not support a digital gate'%(self.name))
                            
    def disable(self):
        """overridden from StaticDDS so as not to provide time resolution -
        output can be enabled or disabled only at the start of the shot"""
        #self.gate.go_low() # don't think this is needed
        raise LabscriptError('StaticFreqAmp %s does not support a digital gate'%(self.name))
        
@labscript_device              
class SignalGenerator(VISA):
    description = 'Signal Generator'
    allowed_children = [StaticFreqAmp]
    # define the scale factor - converts between BLACS front panel and 
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    freq_limits = (100e3, 1057.5e6) # set in scaled unit (Hz)
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = (-140, 20) # set in scaled unit (dBm)
    # Output limits depend on frequency. Can be as low as 17 dBm

    @set_passed_properties()
    def __init__(self, name, VISA_name):
        '''VISA_name can be full VISA connection string or NI-MAX alias'''
        # Signal Generators do not have a parent device
        VISA.__init__(self,name,None,VISA_name)
        
    def quantise_freq(self,data, device):
        # It's faster to add 0.5 then typecast than to round to integers first (device is programmed in Hz):    
        data = np.array((self.scale_factor*data)+0.5, dtype=np.uint64)
        
        # Ensure that frequencies are within bounds:
        if any(data < self.freq_limits[0] )  or any(data > self.freq_limits[1] ):
            raise LabscriptError('%s %s '%(device.description, device.name) +
                                'can only have frequencies between %EHz and %EHz, '%self.freq_limits)
        return data, self.scale_factor
        
    def quantise_amp(self,data, device):
        # Keep as float since programming often done down to 0.1dBm (device is programmed in dBm):                       
        data = np.array((self.amp_scale_factor*data), dtype=np.float16)

        # Ensure that amplitudes are within bounds:        
        if any(data < self.amp_limits[0] )  or any(data > self.amp_limits[1] ):
            raise LabscriptError('%s %s '%(device.description, device.name) +
                              'can only have amplitudes between %.1fdBm and %.1fdBm, '%self.amp_limits)
        return data, self.amp_scale_factor
    
    def generate_code(self, hdf5_file):
        for output in self.child_devices:
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError('%s %s has invalid connection string: \'%s\'. '%(output.description,output.name,str(output.connection)) + 
                                     'Format must be \'channel n\' with n equal 0.')
            if channel != 0:
                raise LabscriptError('%s %s has invalid connection string: \'%s\'. '%(output.description,output.name,str(output.connection)) + 
                                     'Format must be \'channel n\' with n equal 0.')
            dds = output
        # Call these functions to finalise stuff:
        ignore = dds.frequency.get_change_times()
        dds.frequency.make_timeseries([])
        dds.frequency.expand_timeseries()
        
        ignore = dds.amplitude.get_change_times()
        dds.amplitude.make_timeseries([])
        dds.amplitude.expand_timeseries()
        
        dds.frequency.raw_output, dds.frequency.scale_factor = self.quantise_freq(dds.frequency.raw_output, dds)
        dds.amplitude.raw_output, dds.amplitude.scale_factor = self.quantise_amp(dds.amplitude.raw_output, dds)
        static_dtypes = [('freq0', np.uint64)] + \
                        [('amp0', np.float16)]
        static_table = np.zeros(1, dtype=static_dtypes)   
        static_table['freq0'].fill(1)
        static_table['freq0'] = dds.frequency.raw_output[0]
        static_table['amp0'].fill(1)
        static_table['amp0'] = dds.amplitude.raw_output[0]
        grp = hdf5_file.create_group('/devices/'+self.name)
        grp.create_dataset('STATIC_DATA',compression=config.compression,data=static_table) 
        self.set_property('frequency_scale_factor', self.scale_factor, location='device_properties')
        self.set_property('amplitude_scale_factor', self.amp_scale_factor, location='device_properties')

@BLACS_tab
class SignalGeneratorTab(VISATab):
    # Capabilities
    base_units = {'freq':'MHz', 'amp':'dBm'}
    base_min = {'freq':0.1,   'amp':-140}
    base_max = {'freq':1057.5,  'amp':20}
    base_step = {'freq':1,    'amp':0.1}
    base_decimals = {'freq':6, 'amp':1}
    # Status Byte Label Definitions for HP8642A
    status_byte_labels = {'bit 7':'Parameter Changed', 
                          'bit 6':'RQS',
                          'bit 5':'Error',
                          'bit 4':'Ready',
                          'bit 3':'Local/Remote',
                          'bit 2':'Execution Error',
                          'bit 1':'Hardware Error',
                          'bit 0':'End of Sweep'}
    
    def __init__(self,*args,**kwargs):
        if not hasattr(self,'device_worker_class'):
                self.device_worker_class = SignalGeneratorWorker
        VISATab.__init__(self,*args,**kwargs)
    
    def initialise_GUI(self):
        # Create the dds channel                                
        dds_prop = {} 
        dds_prop['channel 0'] = {} #HP signal generators only have one output
        for subchnl in ['freq', 'amp']:
            dds_prop['channel 0'][subchnl] = {'base_unit':self.base_units[subchnl],
                                              'min':self.base_min[subchnl],
                                              'max':self.base_max[subchnl],
                                              'step':self.base_step[subchnl],
                                              'decimals':self.base_decimals[subchnl]
                                              }

       
        # Create the output objects    
        self.create_dds_outputs(dds_prop)        
        # Create widgets for output objects
        dds_widgets,ao_widgets,do_widgets = self.auto_create_widgets()
        # and auto place the widgets in the UI
        self.auto_place_widgets(("Frequency Output",dds_widgets))
        
        # call VISATab.initialise to create STB widget
        VISATab.initialise_GUI(self)

        # Set the capabilities of this device
        self.supports_remote_value_check(True)
        self.supports_smart_programming(True) 
        self.statemachine_timeout_add(5000, self.status_monitor)       

import h5py
@BLACS_worker
class SignalGeneratorWorker(VISAWorker):
    # define the scale factor
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6
    amp_scale_factor = 1.0
    
    # define instrument specific read and write strings for Freq & Amp control
    freq_write_string = 'FR %d HZ'  #HP8642A can only accept 10 digits, in Hz
    freq_query_string = 'FROA' #HP8642A returns 'FR sdddddddddd.0 HZ', in Hz
    def freq_parser(self,freq_string):
        '''Frequency Query string parser for HP8642A
        freq_string format is FR sdddddddddd.0 HZ
        Returns float in instrument units, Hz (i.e. needs scaling to base_units)'''
        return float(freq_string.split()[1])
    amp_write_string = 'AP %.1f DM' #HP8642A accepts one decimal, in dBm
    amp_query_string = 'APOA' #HP8642A returns 'AP sddd.d DM'
    def amp_parser(self,amp_string):
        '''Amplitude Query string parser for HP8642A
        amp_string format is AP sddd.d DM
        Returns float in instrument units, dBm'''
        # values less than -200 indicate instrument errors 
        # -201: RF OFF
        # -202: reverse power is tripped
        amp = float(amp_string.split()[1])
        if amp <= -200:
            raise LabscriptError('RF of HP8642A is off!')
        return amp
    
    def check_remote_values(self):
        # Get the currently output values:

        results = {'channel 0':{}}
        
        # these query strings and parsers depend heavily on device
        freq = self.connection.query(self.freq_query_string)
        amp = self.connection.query(self.amp_query_string)
            
        # Convert string to MHz:
        results['channel 0']['freq'] = self.freq_parser(freq)/self.scale_factor
            
        results['channel 0']['amp'] = self.amp_parser(amp)/self.amp_scale_factor

        return results
    
    def program_manual(self,front_panel_values):
        freq = front_panel_values['channel 0']['freq']
        amp = front_panel_values['channel 0']['amp']
        # NOTE: HP Sig. Gen. can have long switching times (>100ms)
        #program with scale factor
        fcommand = self.freq_write_string%(freq*self.scale_factor)
        self.connection.write(fcommand)
        
        #program with scale factor
        acommand = self.amp_write_string%(amp*self.amp_scale_factor)
        self.connection.write(acommand)
        
        return self.check_remote_values()        

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # call parent method to do basic preamble
        VISAWorker.transition_to_buffered(self,device_name,h5file,initial_values,fresh)
        # Program static values
        with h5py.File(h5file) as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            # If there are values to set the unbuffered outputs to, set them now:
            if 'STATIC_DATA' in group:
                data = group['STATIC_DATA'][:][0]
                
        self.connection.write(self.freq_write_string%(data['freq0']))
       
        self.connection.write(self.amp_write_string%(data['amp0']))
        
        
        # Save these values into final_values so the GUI can
        # be updated at the end of the run to reflect them:
        final_values = {'channel 0':{}}
        
        final_values['channel 0']['freq'] = data['freq0']/self.scale_factor
        final_values['channel 0']['amp'] = data['amp0']/self.amp_scale_factor
                
        return final_values

