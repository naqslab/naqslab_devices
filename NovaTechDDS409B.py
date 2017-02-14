#####################################################################
#                                                                   #
# /NovaTechDDS409B.py                                               #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

# This is a very rough attempt to do static only lines for 409B.
# I suspect there are still many errors.

from labscript_devices import runviewer_parser, labscript_device, BLACS_tab, BLACS_worker

from labscript import StaticDDS, Device, config, LabscriptError, set_passed_properties
from labscript_utils.unitconversions import NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion

import numpy as np
import labscript_utils.h5_lock, h5py
import labscript_utils.properties

        
@labscript_device
class NovaTechDDS409B(Device):
    description = 'NT-DDS409B'
    allowed_children = [StaticDDS]

    @set_passed_properties(
        property_names = {'connection_table_properties': ['update_mode']}
        )
    def __init__(self, name,
                 com_port = "", baud_rate=19200, update_mode='synchronous', **kwargs):

        Device.__init__(self, name, None, com_port, **kwargs)
        self.BLACS_connection = '%s,%s'%(com_port, str(baud_rate))
        if not update_mode in ['synchronous', 'asynchronous']:
            raise LabscriptError('update_mode must be \'synchronous\' or \'asynchronous\'')            
        
        self.update_mode = update_mode 
        
    def add_device(self, device):
        Device.add_device(self, device)
        # The Novatech doesn't support 0Hz output; set the default frequency of the DDS to 0.1 Hz:
        device.frequency.default_value = 0.1
            
    def get_default_unit_conversion_classes(self, device):
        """Child devices call this during their __init__ (with themselves
        as the argument) to check if there are certain unit calibration
        classes that they should apply to their outputs, if the user has
        not otherwise specified a calibration class"""
        if device.connection in ['channel 0', 'channel 1', 'channel 2', 'channel 3']:
            # Default calibration classes for the static channels:
            return NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion, None
        else:
            return None, None, None
        
        
    def quantise_freq(self, data, device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # Ensure that frequencies are within bounds:
        if np.any(data > 171.1276031e6 )  or np.any(data < 0.1 ):
            raise LabscriptError('%s %s '%(device.description, device.name) +
                              'can only have frequencies between 0.1Hz and 171MHz, ' + 
                              'the limit imposed by %s.'%self.name)
        # It's faster to add 0.5 then typecast than to round to integers first:
        data = np.array((1*data)+0.5,dtype=np.uint32)
        scale_factor = 1
        return data, scale_factor
        
    def quantise_phase(self, data, device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # ensure that phase wraps around:
        data %= 360
        # It's faster to add 0.5 then typecast than to round to integers first:
        data = np.array((45.511111111111113*data)+0.5,dtype=np.uint16)
        scale_factor = 45.511111111111113
        return data, scale_factor
        
    def quantise_amp(self,data,device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # ensure that amplitudes are within bounds:
        if np.any(data > 1 )  or np.any(data < 0):
            raise LabscriptError('%s %s '%(device.description, device.name) +
                              'can only have amplitudes between 0 and 1 (Volts peak to peak approx), ' + 
                              'the limit imposed by %s.'%self.name)
        # It's faster to add 0.5 then typecast than to round to integers first:
        data = np.array((1023*data)+0.5,dtype=np.uint16)
        scale_factor = 1023
        return data, scale_factor
        
    def generate_code(self, hdf5_file):
        DDSs = {}
        for output in self.child_devices:
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError('%s %s has invalid connection string: \'%s\'. '%(output.description,output.name,str(output.connection)) + 
                                     'Format must be \'channel n\' with n from 0 to 3.')
            DDSs[channel] = output
        for connection in DDSs:
            if connection in range(4):
                # Static DDS
                dds = DDSs[connection]   
                dds.frequency.raw_output, dds.frequency.scale_factor = self.quantise_freq(dds.frequency.static_value, dds)
                dds.phase.raw_output, dds.phase.scale_factor = self.quantise_phase(dds.phase.static_value, dds)
                dds.amplitude.raw_output, dds.amplitude.scale_factor = self.quantise_amp(dds.amplitude.static_value, dds)
            else:
                raise LabscriptError('%s %s has invalid connection string: \'%s\'. '%(dds.description,dds.name,str(dds.connection)) + 
                                     'Format must be \'channel n\' with n from 0 to 3.')
                 
        static_dtypes = [('freq%d'%i,np.uint32) for i in range(4)] + \
                        [('phase%d'%i,np.uint16) for i in range(4)] + \
                        [('amp%d'%i,np.uint16) for i in range(4)]
    
        
        static_table = np.zeros(1, dtype=static_dtypes)
        static_table['freq0'].fill(1)
        static_table['freq1'].fill(1)
        static_table['freq2'].fill(1)
        static_table['freq3'].fill(1)
        
        for connection in range(4):
            if not connection in DDSs:
                continue
            dds = DDSs[connection]
            static_table['freq%d'%connection] = dds.frequency.raw_output
            static_table['amp%d'%connection] = dds.amplitude.raw_output
            static_table['phase%d'%connection] = dds.phase.raw_output

        grp = self.init_device_group(hdf5_file)
        grp.create_dataset('STATIC_DATA',compression=config.compression,data=static_table) 
        self.set_property('frequency_scale_factor', 1, location='device_properties')
        self.set_property('amplitude_scale_factor', 1023, location='device_properties')
        self.set_property('phase_scale_factor', 45.511111111111113, location='device_properties')



import time

from blacs.tab_base_classes import Worker, define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED  

from blacs.device_base_class import DeviceTab

@BLACS_tab
class NovatechDDS409BTab(DeviceTab):
    def initialise_GUI(self):        
        # Capabilities
        self.base_units =    {'freq':'Hz',          'amp':'Arb',   'phase':'Degrees'}
        self.base_min =      {'freq':0.0,           'amp':0,       'phase':0}
        self.base_max =      {'freq':171.1*10.0**6, 'amp':1,       'phase':360}
        self.base_step =     {'freq':10**6,         'amp':1/1023., 'phase':1}
        self.base_decimals = {'freq':1,             'amp':4,       'phase':3} # TODO: find out what the phase precision is!
        self.num_DDS = 4
        
        # Create DDS Output objects
        dds_prop = {}
        for i in range(self.num_DDS): # 4 is the number of DDS outputs on this device
            dds_prop['channel %d'%i] = {}
            for subchnl in ['freq', 'amp', 'phase']:
                dds_prop['channel %d'%i][subchnl] = {'base_unit':self.base_units[subchnl],
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
        self.auto_place_widgets(("DDS Outputs",dds_widgets))
        
        connection_object = self.settings['connection_table'].find_by_name(self.device_name)
        
        # Store the COM port to be used
        blacs_connection =  str(connection_object.BLACS_connection)
        if ',' in blacs_connection:
            self.com_port, baud_rate = blacs_connection.split(',')
            self.baud_rate = int(baud_rate)
        else:
            self.com_port = blacs_connection
            self.baud_rate = 19200
        
        self.update_mode = connection_object.properties.get('update_mode', 'synchronous')
        
        # Create and set the primary worker
        self.create_worker("main_worker",NovatechDDS409BWorker,{'com_port':self.com_port,
                                                              'baud_rate': self.baud_rate,
                                                              'update_mode': self.update_mode})
        self.primary_worker = "main_worker"

        # Set the capabilities of this device
        self.supports_remote_value_check(True)
        self.supports_smart_programming(True) 

@BLACS_worker        
class NovatechDDS409BWorker(Worker):
    def init(self):
        global serial; import serial
        global h5py; import labscript_utils.h5_lock, h5py
        self.smart_cache = {'STATIC_DATA': None, 'TABLE_DATA': ''}
        
        self.connection = serial.Serial(self.com_port, baudrate = self.baud_rate, timeout=0.1)
        self.connection.readlines()
        
        self.connection.write('e d\r\n')
        response = self.connection.readline()
        if response == 'e d\r\n':
            # if echo was enabled, then the command to disable it echos back at us!
            response = self.connection.readline()
        if response != "OK\r\n":
            raise Exception('Error: Failed to execute command: "e d". Cannot connect to the device.')
        
        self.connection.write('I a\r\n')
        if self.connection.readline() != "OK\r\n":
            raise Exception('Error: Failed to execute command: "I a"')
        
        #self.connection.write('m 0\r\n')
        #if self.connection.readline() != "OK\r\n":
        #    raise Exception('Error: Failed to execute command: "m 0"')
        
        #return self.get_current_values()
        
    def check_remote_values(self):
        # Get the currently output values:
        self.connection.write('QUE\r\n')
        try:
            response = [self.connection.readline() for i in range(5)]
        except socket.timeout:
            raise Exception('Failed to execute command "QUE". Cannot connect to device.')
        results = {}
        for i, line in enumerate(response[:4]):
            results['channel %d'%i] = {}
            freq, phase, amp, ignore, ignore, ignore, ignore = line.split()
            # Convert hex multiple of 0.1 Hz to MHz:
            results['channel %d'%i]['freq'] = float(int(freq,16))/10.0
            # Convert hex to int:
            results['channel %d'%i]['amp'] = int(amp,16)/1023.0
            # Convert hex fraction of 16384 to degrees:
            results['channel %d'%i]['phase'] = int(phase,16)*360/16384.0
        return results
        
    def program_manual(self,front_panel_values):
        # TODO: Optimise this so that only items that have changed are reprogrammed by storing the last programmed values
        # For each DDS channel,
        for i in range(4):    
            # and for each subchnl in the DDS,
            for subchnl in ['freq','amp','phase']:     
                # Program the sub channel
                self.program_static(i,subchnl,front_panel_values['channel %d'%i][subchnl])
        return self.check_remote_values()

    def program_static(self,channel,type,value):
        if type == 'freq':
            command = 'F%d %.7f\r\n'%(channel,value/10.0**6)
            self.connection.write(command)
            if self.connection.readline() != "OK\r\n":
                raise Exception('Error: Failed to execute command: %s'%command)
        elif type == 'amp':
            command = 'V%d %u\r\n'%(channel,int(value*1023+0.5))
            self.connection.write(command)
            if self.connection.readline() != "OK\r\n":
                raise Exception('Error: Failed to execute command: %s'%command)
        elif type == 'phase':
            command = 'P%d %u\r\n'%(channel,value*16384.0/360)
            self.connection.write(command)
            if self.connection.readline() != "OK\r\n":
                raise Exception('Error: Failed to execute command: %s'%command)
        else:
            raise TypeError(type)
        # Now that a static update has been done, we'd better invalidate the saved STATIC_DATA:
        self.smart_cache['STATIC_DATA'] = None
     
    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # Store the initial values in case we have to abort and restore them:
        self.initial_values = initial_values
        # Store the final values to for use during transition_to_static:
        self.final_values = {}
        static_data = None
        with h5py.File(h5file) as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            # If there are values to set the unbuffered outputs to, set them now:
            if 'STATIC_DATA' in group:
                static_data = group['STATIC_DATA'][:][0]
        
        if static_data is not None:
            data = static_data
            if fresh or data != self.smart_cache['STATIC_DATA']:
                self.logger.debug('Static data has changed, reprogramming.')
                self.smart_cache['STATIC_DATA'] = data
                
                for i in range(4):
                    # write out each channel
                    self.connection.write('F%d %.7f\r\n'%(i,data['freq%d'%i]/10.0**6))
                    self.connection.readline()
                    self.connection.write('V%d %u\r\n'%(i,data['amp%d'%i]))
                    self.connection.readline()
                    self.connection.write('P%d %u\r\n'%(i,data['phase%d'%i]))
                    self.connection.readline()
                                
                # Save these values into final_values so the GUI can
                # be updated at the end of the run to reflect them:
                self.final_values = {'channel 0':{},'channel 1':{},'channel 2':{},'channel 3':{}}
                for i in range(4):
                    self.final_values['channel %d'%i]['freq'] = data['freq%d'%i]
                    self.final_values['channel %d'%i]['amp'] = data['amp%d'%i]/1023.0
                    self.final_values['channel %d'%i]['phase'] = data['phase%d'%i]*360/16384.0
            
        return self.final_values
    
    def abort_transition_to_buffered(self):
        return self.transition_to_manual(True)
        
    def abort_buffered(self):
        # TODO: untested
        return self.transition_to_manual(True)
    
    def transition_to_manual(self,abort = False):
        if abort:
            # If we're aborting the run, then we need to reset DDSs 2 and 3 to their initial values.
            # 0 and 1 will already be in their initial values. We also need to invalidate the smart
            # programming cache for them.
            values = self.initial_values
            DDSs = range(4)
            self.smart_cache['STATIC_DATA'] = None
        else:
            # if not aborting, final values already set so do nothing
            DDSs = []
            
        # only program the channels that we need to
        for ddsnumber in DDSs:
            channel_values = values['channel %d'%ddsnumber]
            for subchnl in ['freq','amp','phase']:            
                self.program_static(ddsnumber,subchnl,channel_values[subchnl])
            
        # return True to indicate we successfully transitioned back to manual mode
        return True
                     
    def shutdown(self):
        self.connection.close()
        
        
'''        
@runviewer_parser
class RunviewerClass(object):    
    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device
            
    def get_traces(self, add_trace, clock=None):
        if clock is None:
            # we're the master pseudoclock, software triggered. So we don't have to worry about trigger delays, etc
            raise Exception('No clock passed to %s. The NovaTechDDS9M must be clocked by another device.'%self.name)
        
        times, clock_value = clock[0], clock[1]
        
        clock_indices = np.where((clock_value[1:]-clock_value[:-1])==1)[0]+1
        # If initial clock value is 1, then this counts as a rising edge (clock should be 0 before experiment)
        # but this is not picked up by the above code. So we insert it!
        if clock_value[0] == 1:
            clock_indices = np.insert(clock_indices, 0, 0)
        clock_ticks = times[clock_indices]
        
        # get the data out of the H5 file
        data = {}
        with h5py.File(self.path, 'r') as f:
            #if 'TABLE_DATA' in f['devices/%s'%self.name]:
            #    table_data = f['devices/%s/TABLE_DATA'%self.name][:]
            #    for i in range(2):
            #        for sub_chnl in ['freq', 'amp', 'phase']:                        
            #            data['channel %d_%s'%(i,sub_chnl)] = table_data['%s%d'%(sub_chnl,i)][:]
                                
            if 'STATIC_DATA' in f['devices/%s'%self.name]:
                static_data = f['devices/%s/STATIC_DATA'%self.name][:]
                for i in range(4):
                    for sub_chnl in ['freq', 'amp', 'phase']:                        
                        data['channel %d_%s'%(i,sub_chnl)] = np.empty((len(clock_ticks),))
                        data['channel %d_%s'%(i,sub_chnl)].fill(static_data['%s%d'%(sub_chnl,i)][0])
            
        
        for channel, channel_data in data.items():
            data[channel] = (clock_ticks, channel_data)
        
        for channel_name, channel in self.device.child_list.items():
            for subchnl_name, subchnl in channel.child_list.items():
                connection = '%s_%s'%(channel.parent_port, subchnl.parent_port)
                if connection in data:
                    add_trace(subchnl.name, data[connection], self.name, connection)
        
        return {}
'''    
