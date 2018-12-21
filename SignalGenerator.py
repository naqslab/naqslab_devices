#####################################################################
#                                                                   #
# /Signal_Generator.py                                              #
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

import numpy as np
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from naqslab_devices.VISA import VISA, VISATab, VISAWorker
from labscript import Device, StaticDDS, StaticAnalogQuantity, config, LabscriptError, set_passed_properties
import labscript_utils.properties

__version__ = '0.1.0'
__author__ = ['dihm']

class StaticFreqAmp(StaticDDS):
    """A Static Frequency that supports frequency and amplitude control."""
    description = 'Frequency Source class for Signal Generators'
    allowed_children = [StaticAnalogQuantity]
    
    @set_passed_properties(property_names = {})    
    def __init__(self, name, parent_device, connection, freq_limits = (), freq_conv_class = None,freq_conv_params = {}, amp_limits = (), amp_conv_class = None, amp_conv_params = {}):
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
        raise LabscriptError('StaticFreqAmp {:s} does not support a digital gate'.format(self.name))
                            
    def disable(self):
        """overridden from StaticDDS so as not to provide time resolution -
        output can be enabled or disabled only at the start of the shot"""
        raise LabscriptError('StaticFreqAmp {:s} does not support a digital gate'.format(self.name))
        
@labscript_device              
class SignalGenerator(VISA):
    description = 'Signal Generator'
    allowed_children = [StaticFreqAmp]
    # define the scale factor - converts between BLACS front panel and instr
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6 # ensure that the BLACS worker class has same scale_factor
    freq_limits = () # set in scaled unit 
    amp_scale_factor = 1.0 # ensure that the BLACS worker class has same amp_scale_factor
    amp_limits = () # set in scaled unit

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
            raise LabscriptError('{:s} {:s} '.format(device.description, device.name) +
                                'can only have frequencies between {:E}Hz and {:E}Hz'.format(*self.freq_limits))
        return data, self.scale_factor
        
    def quantise_amp(self,data, device):
        # Keep as float since programming often done down to 0.1dBm (device is programmed in dBm):                       
        data = np.array((self.amp_scale_factor*data), dtype=np.float16)

        # Ensure that amplitudes are within bounds:        
        if any(data < self.amp_limits[0] )  or any(data > self.amp_limits[1] ):
            raise LabscriptError('{:s} {:s} '.format(device.description, device.name) +
                              'can only have amplitudes between {:.1f}dBm and {:.1f}dBm'.format(*self.amp_limits))
        return data, self.amp_scale_factor
    
    def generate_code(self, hdf5_file):
        for output in self.child_devices:
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError('{:s} {:s} has invalid connection string: \'{!s}\'. '.format(output.description,output.name,output.connection) + 
                                     'Format must be \'channel n\' with n equal 0.')
            if channel != 0:
                raise LabscriptError('{:s} {:s} has invalid connection string: \'{!s}\'. '.format(output.description,output.name,output.connection) + 
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
        static_dtypes = np.dtype({'names':['freq0','amp0'],'formats':[np.uint64,np.float16]})
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

    status_byte_labels = {'bit 7':'bit 7 label', 
                          'bit 6':'bit 6 label',
                          'bit 5':'bit 5 label',
                          'bit 4':'bit 4 label',
                          'bit 3':'bit 3 label',
                          'bit 2':'bit 2 label',
                          'bit 1':'bit 1 label',
                          'bit 0':'bit 0 label'}
    
    def __init__(self,*args,**kwargs):
        if not hasattr(self,'device_worker_class'):
            #raise LabscriptError('%s __init__ method not overridden!'%self)
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

@BLACS_worker
class SignalGeneratorWorker(VISAWorker):
    # define the scale factor
    # Writing: scale*desired_freq // Reading:desired_freq/scale
    scale_factor = 1.0e6
    amp_scale_factor = 1.0
    
    # define instrument specific read and write strings for Freq & Amp control
    freq_write_string = ''  
    freq_query_string = '' 
    def freq_parser(self,freq_string):
        '''Frequency Query string parser
        Needs to be over-ridden'''
        freq = float(freq_string)
        return freq
    amp_write_string = '' 
    amp_query_string = '' 
    def amp_parser(self,amp_string):
        '''Amplitude Query string parser
        Needs to be over-ridden'''
        amp = float(amp_string)
        return amp
    
    def init(self):
        # import h5py with locks
        global h5py; import labscript_utils.h5_lock, h5py
        # Call the VISA init to initialise the VISA connection
        VISAWorker.init(self)
        
        # initialize the smart cache
        self.smart_cache = {'STATIC_DATA': {'freq0':None,'amp0':None}}
    
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

        #program with scale factor
        fcommand = self.freq_write_string.format(freq*self.scale_factor)
        self.connection.write(fcommand)
        
        #program with scale factor
        acommand = self.amp_write_string.format(amp*self.amp_scale_factor)
        self.connection.write(acommand)
        
        # invalidate smart_cache after manual update
        self.smart_cache['STATIC_DATA'] = {'freq0':None,'amp0':None}
        
        return self.check_remote_values()        

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # call parent method to do basic preamble
        VISAWorker.transition_to_buffered(self,device_name,h5file,initial_values,fresh)
        data = None
        # Program static values
        with h5py.File(h5file) as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            # If there are values to set the unbuffered outputs to, set them now:
            if 'STATIC_DATA' in group:
                data = group['STATIC_DATA'][:][0]
                
        if data is not None:
            if fresh or data != self.smart_cache['STATIC_DATA']:
                
                # program freq and amplitude as necessary
                if data['freq0'] != self.smart_cache['STATIC_DATA']['freq0']:
                    self.connection.write(self.freq_write_string.format(data['freq0']))
                if data['amp0'] != self.smart_cache['STATIC_DATA']['amp0']:
                    self.connection.write(self.amp_write_string.format(data['amp0']))
                
                # update smart_cache
                self.smart_cache['STATIC_DATA'] = data

                # Save these values into final_values so the GUI can
                # be updated at the end of the run to reflect them:
                final_values = {'channel 0':{}}
                
                final_values['channel 0']['freq'] = data['freq0']/self.scale_factor
                final_values['channel 0']['amp'] = data['amp0']/self.amp_scale_factor
                
            else:
                final_values = self.initial_values
                
        return final_values

