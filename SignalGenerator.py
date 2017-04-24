#####################################################################
#                                                                   #
# /Signal Generator.py                                              #
#                                                                   #
#                                                                   #
#####################################################################

import numpy as np
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker

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
class SignalGenerator(Device):
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
    def __init__(self, name,VISA_name):
        '''VISA_name can be full VISA connection string or NI-MAX alias'''
        Device.__init__(self, name, None, VISA_name)
        self.BLACS_connection = VISA_name
        
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
        
        
        
from blacs.tab_base_classes import Worker, define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED  
from blacs.device_base_class import DeviceTab
from qtutils import UiLoader
import os

@BLACS_tab
class SignalGeneratorTab(DeviceTab):
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
        '''You MUST override this class in order to define the device worker for any child devices.
        You then call this parent method to finish initialization.'''
        if not hasattr(self,'device_worker_class'):
            self.device_worker_class = SignalGeneratorWorker
        DeviceTab.__init__(self,*args,**kwargs)
    
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
        
        self.status_ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)),'sgstatus.ui'))
        self.get_tab_layout().addWidget(self.status_ui)
                   
        # generate the dictionaries
        self.status_bits = ['bit 0', 'bit 1', 'bit 2', 'bit 3', 'bit 4', 'bit 5', 'bit 6', 'bit 7']
        self.bit_labels_widgets = {}
        self.bit_values_widgets = {}
        self.status = {}
        for bit in self.status_bits:
            self.status[bit] = False
            self.bit_values_widgets[bit] = getattr(self.status_ui, 'status_%s'%bit.split()[1])
            self.bit_labels_widgets[bit] = getattr(self.status_ui, 'status_label_%s'%bit.split()[1])
        
        # Dynamically update status bits with correct names           
        for key in self.status_bits:
            self.bit_labels_widgets[key].setText(self.status_byte_labels[key])
        self.status_ui.clear_button.clicked.connect(self.send_clear)
        
        
        # Store the VISA name to be used
        self.address = str(self.settings['connection_table'].find_by_name(self.settings["device_name"]).BLACS_connection)
        
        # Create and set the primary worker
        self.create_worker("main_worker",self.device_worker_class,{'address':self.address})
        self.primary_worker = "main_worker"

        # Set the capabilities of this device
        self.supports_remote_value_check(True)
        self.supports_smart_programming(True) 
        self.statemachine_timeout_add(5000, self.status_monitor)        

    
    # This function gets the status of the HP Signal Generator,
    # and updates the front panel widgets!
    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True)  
    def status_monitor(self):
        # When called with a queue, this function writes to the queue
        # when the pulseblaster is waiting. This indicates the end of
        # an experimental run.
        self.status = yield(self.queue_work(self._primary_worker,'check_status'))

        for key in self.status_bits:
            self.bit_values_widgets[key].setText(str(self.status[key]))
        
        
    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True,True)
    def send_clear(self,widget=None):
        value = self.status_ui.clear_button.isChecked()
        yield(self.queue_work(self._primary_worker,'clear',value))
       

@BLACS_worker
class SignalGeneratorWorker(Worker):
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
    
    def init(self):
        global visa; import visa
        global h5py; import labscript_utils.h5_lock, h5py
        global time; import time
    
        self.VISA_name = self.address
        self.resourceMan = visa.ResourceManager()
        self.connection = self.resourceMan.open_resource(self.VISA_name)
        self.connection.timeout = 2000
        
        # initialization stuff would go here
    
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
    
    def check_status(self):
        results = {}
        stb = self.connection.read_stb()

        #get the status and convert to binary, and take off the '0b' header:
        status = bin(stb)[2:]
        # if the status is less than 8 bits long, pad the start with zeros!
        while len(status)<8:
            status = '0'+status
        # reverse the status string so bit 0 is first indexed
        status = status[::-1]
        # fill the status byte dictionary
        for i in range(0,8):
            results['bit '+str(i)] = bool(int(status[i]))
        
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
        
        
    def clear(self,value):
        self.connection.clear()
        

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # Store the initial values in case we have to abort and restore them:
        self.initial_values = initial_values
        # Store the final values to for use during transition_to_static:
        self.final_values = {}
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
        
    def abort_transition_to_buffered(self):
        return self.transition_to_manual(True)
        
    def abort_buffered(self):
        return self.transition_to_manual(True)
    

    
    def transition_to_manual(self,abort = False):
        if abort:
            # If we're aborting the run, reset to original value
            self.program_manual(self.initial_values)
        # If we're not aborting the run, stick with buffered value. Nothing to do really!
        # return the current values in the device
        return True
        
    def shutdown(self):
        self.connection.close()

