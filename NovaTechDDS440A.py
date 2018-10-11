#####################################################################
#                                                                   #
# /NovaTechDDS440A.py                                               #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode
    
from labscript_devices import runviewer_parser, labscript_device, BLACS_tab, BLACS_worker

from labscript import StaticDDS, Device, config, LabscriptError, set_passed_properties

from naqslab_devices.NovaTechDDS409B_AC import *

import numpy as np
import labscript_utils.h5_lock, h5py
import labscript_utils.properties
        
@labscript_device
class NovaTechDDS440A(NovaTechDDS409B_AC):
    description = 'NT-DDS440A'
    allowed_children = [StaticDDS]
    clock_limit = 1
    # this is not a triggerable device

    def __init__(self, name,
                 com_port = "", baud_rate=19200, **kwargs):

        Device.__init__(self, name, None, com_port, **kwargs)
        self.BLACS_connection = '{:s},{:s}'.format(com_port, str(baud_rate))   
        
    def quantise_freq(self, data, device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # Ensure that frequencies are within bounds:
        if np.any(data > 402.653183e6 )  or np.any(data < 0.2e3 ):
            raise LabscriptError('%s %s ' % (device.description, device.name) +
                              'can only have frequencies between 200kHz and 402MHz, ' + 
                              'the limit imposed by %s.' % self.name)
        # It's faster to add 0.5 then typecast than to round to integers first:
        data = np.array((data)+0.5,dtype=np.uint32)
        scale_factor = 10
        return data, scale_factor
        
    def generate_code(self, hdf5_file):
        DDSs = {}
        for output in self.child_devices:
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError('{:s} {:s} has invalid connection string: \'{:s}\'. '.format(output.description,output.name,str(output.connection)) + 
                                     'Format must be \'channel 0\'.')
            DDSs[channel] = output
            
        if not DDSs:
            # if no channels are being used, no need to continue
            return
            
        for connection in DDSs:
            if connection in range(1):
                # Static DDS
                dds = DDSs[connection]   
                dds.frequency.raw_output, dds.frequency.scale_factor = self.quantise_freq(dds.frequency.static_value, dds)
                dds.phase.raw_output, dds.phase.scale_factor = self.quantise_phase(dds.phase.static_value, dds)
            else:
                raise LabscriptError('{:s} {:s} has invalid connection string: \'{:s}\'. '.format(dds.description,dds.name,str(dds.connection)) + 
                                     'Format must be \'channel 0\'.')
                                     
        if dds.amplitude.static_value != 0.0:
            # user has tried to set amplitude away from default
            raise LabscriptError('{:s}:{:s} does not have controllable amplitude'.format(self.name, dds.name))
                 
        static_dtypes = {'names':['freq{:d}'.format(i) for i in DDSs] +
                            ['phase{:d}'.format(i) for i in DDSs],
                            'formats':[np.uint32 for i in DDSs] +
                            [np.uint16 for i in DDSs] + 
                            [np.uint16 for i in DDSs]}  
        
        static_table = np.zeros(1, dtype=static_dtypes)            
        
        for connection in DDSs:
            dds = DDSs[connection]
            static_table['freq{:d}'.format(connection)] = dds.frequency.raw_output
            static_table['phase{:d}'.format(connection)] = dds.phase.raw_output

        grp = self.init_device_group(hdf5_file)
        grp.create_dataset('STATIC_DATA',compression=config.compression,data=static_table) 
        self.set_property('frequency_scale_factor', dds.frequency.scale_factor, location='device_properties')
        self.set_property('phase_scale_factor', dds.phase.scale_factor, location='device_properties') 

@BLACS_tab
class NovaTechDDS440ATab(NovaTechDDS409B_ACTab):
    
    def __init__(self,*args,**kwargs):
        if not hasattr(self,'device_worker_class'):
            self.device_worker_class = NovaTechDDS440AWorker
        DeviceTab.__init__(self,*args,**kwargs)
        
    def initialise_GUI(self):        
        # Capabilities
        self.base_units =    {'freq':'Hz',               'phase':'Degrees'}
        self.base_min =      {'freq':200e3,              'phase':0}
        self.base_max =      {'freq':402.653183*10.0**6, 'phase':360}
        self.base_step =     {'freq':10**6,              'phase':1}
        self.base_decimals = {'freq':0,                  'phase':3} # TODO: find out what the phase precision is!
        self.num_DDS = 1
        
        # Create DDS Output objects
        dds_prop = {}
        for i in range(self.num_DDS): # only 1 DDS output
            dds_prop['channel %d' % i] = {}
            for subchnl in ['freq', 'phase']:
                dds_prop['channel %d' % i][subchnl] = {'base_unit':self.base_units[subchnl],
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
        
        # Create and set the primary worker
        self.create_worker("main_worker",self.device_worker_class,{'com_port':self.com_port,
                                                              'baud_rate': self.baud_rate
                                                              })
        self.primary_worker = "main_worker"

        # Set the capabilities of this device
        self.supports_remote_value_check(True)
        self.supports_smart_programming(True) 


@BLACS_worker        
class NovaTechDDS440AWorker(NovaTechDDS409B_ACWorker):
    
    def init(self):
        global serial; import serial
        global h5py; import labscript_utils.h5_lock, h5py
        self.smart_cache = {'STATIC_DATA': None,'CURRENT_DATA':None}
        
        # conversion dictionaries for program_static from 
        # program_manual                      
        self.conv = {'freq':10**(-6),'phase':16384.0/360.0}
        # and from transition_to_buffered
        self.conv_buffered = {'freq':10**(-6),'phase':1}
        
        self.connection = serial.Serial(self.com_port, baudrate = self.baud_rate, timeout=0.1)
        self.connection.readlines()
        
        self.connection.write(b'e d\r\n')
        response = self.connection.readline()
        
        if response == b'e d\r\n':
            # if echo was enabled, then the command to disable it echos back at us!
            response = self.connection.readline()
        if response != b'OK\r\n':
            raise Exception('Error: Failed to execute command: "e d". Cannot connect to the device.')
            
        # populate the 'CURRENT_DATA' dictionary    
        self.check_remote_values()
        
    def check_remote_values(self):
        # Get the currently output values:
        self.connection.write(b'QUE\r\n')
        try:
            response = self.connection.readline()
        except socket.timeout:
            raise Exception('Failed to execute command "QUE". Cannot connect to device.')
        
        results = {}
        results['channel 0'] = {}
        phase, freq, ignore, ignore, ignore, ignore = response.split()
        # Convert hex multiple of 1 Hz to MHz:
        # needs /4 for some reason to convert correctly
        results['channel 0']['freq'] = float(int(freq,16))/4

        # Convert hex fraction of 16384 to degrees:
        results['channel 0']['phase'] = int(phase,16)*360/16384.0
            
        self.smart_cache['CURRENT_DATA'] = results
        
        return results
        
    def program_manual(self,front_panel_values):
        #for each subchnl in the DDS,
        for subchnl in ['freq','phase']:
            # don't program if setting is the same
            if self.smart_cache['CURRENT_DATA']['channel 0'][subchnl] == front_panel_values['channel 0'][subchnl]:
                continue       
            # Program the sub channel
            self.program_static(0,subchnl,
                front_panel_values['channel 0'][subchnl]*self.conv[subchnl])
            # Now that a static update has been done, 
            # we'd better invalidate the saved STATIC_DATA for the channel:
            self.smart_cache['STATIC_DATA'] = None
        return self.check_remote_values()
        
    def program_static(self,channel,type,value):            
        if type == 'freq':
            command = b'F%d %.6f\r\n' % (channel,value)
            self.connection.write(command)
            if self.connection.readline() != b'OK\r\n':
                raise Exception('Error: Failed to execute command: %s' % command)
        elif type == 'amp':
            raise Exception('Error: Novatech 440A cannot control amp')
        elif type == 'phase':
            command = b'P%d %d\r\n' % (channel,int(value))
            self.connection.write(command)
            if self.connection.readline() != b'OK\r\n':
                raise Exception('Error: Failed to execute command: %s' % command)
        else:
            raise TypeError(type)
        
    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):        
        # Store the initial values in case we have to abort and restore them:
        self.initial_values = initial_values
        # Store the final values for use during transition_to_static:
        self.final_values = initial_values
        static_data = None
        table_data = None
        with h5py.File(h5file) as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            # If there are values to set the unbuffered outputs to, set them now:
            if 'STATIC_DATA' in group:
                static_data = group['STATIC_DATA'][:][0]
            # Now program the buffered outputs:
            if 'TABLE_DATA' in group:
                table_data = group['TABLE_DATA'][:]
                
        if static_data is not None:
            data = static_data
            if fresh or data != self.smart_cache['STATIC_DATA']:
                self.smart_cache['STATIC_DATA'] = data
                                
                for subchnl in ['freq','phase']:
                    curr_value = self.smart_cache['CURRENT_DATA']['channel 0'][subchnl]*self.conv[subchnl]
                    value = data[subchnl+str(0)]*self.conv_buffered[subchnl]
                    if value == curr_value:
                        continue
                    self.program_static(0,subchnl,value)
                    self.final_values['channel 0'][subchnl] = value/self.conv[subchnl]
                        
        return self.final_values
    
    def transition_to_manual(self,abort = False):
        if abort:
            # If we're aborting the run, then we need to reset DDSs to their initial values.
            # We also need to invalidate the smart programming cache for them.
            self.smart_cache['STATIC_DATA'] = None
            for channel in self.initial_values:
                ddsnum = int(channel.split(' ')[-1])
                for subchnl in ['freq','amp','phase']:
                    self.program_static(ddsnum,subchnl,self.initial_values[channel][subchnl]*self.conv[subchnl])
        else:
            # if not aborting, final values already set so do nothing
            pass
        # return True to indicate we successfully transitioned back to manual mode
        return True
        
        
      
@runviewer_parser
class NovaTechDDS440AParser(NovaTechDDS409B_ACParser):    
    def __init__(self, path, device):
        NovaTechDDS409B_ACParser.__init__(self,path,device)
        self.dyn_chan = []
        self.static_chan = [0]
            
    def get_traces(self, add_trace, clock=None):
        if clock is None:
            # we're the master pseudoclock, software triggered. So we don't have to worry about trigger delays, etc
            raise Exception('No clock passed to %s. The NovaTechDDS440A must be clocked by another device.' % self.name)
        
        times, clock_value = clock[0], clock[1]
        
        clock_indices = np.where((clock_value[1:]-clock_value[:-1])==1)[0]+1
        # If initial clock value is 1, then this counts as a rising edge (clock should be 0 before experiment)
        # but this is not picked up by the above code. So we insert it!
        if clock_value[0] == 1:
            clock_indices = np.insert(clock_indices, 0, 0)
        clock_ticks = times[clock_indices]
        
        # get the data out of the H5 file
        data = {}
        with h5py.File(self.path, 'r') as hdf5_file:                          
            if 'STATIC_DATA' in hdf5_file['devices/%s' % self.name]:
                static_data = hdf5_file['devices/%s/STATIC_DATA' % self.name][:]
                num_chan = len(static_data)//3
                channels = [int(name[-1]) for name in static_data.dtype.names[0:num_chan]]
                for i in channels:
                    for sub_chnl in ['freq', 'phase']:
                        data['channel %d_%s' % (i,sub_chnl)] = np.empty((len(clock_ticks),))
                        data['channel %d_%s' % (i,sub_chnl)].fill(static_data['%s%d' % (sub_chnl,i)][0])
            
        
        for channel, channel_data in data.items():
            data[channel] = (clock_ticks, channel_data)
        
        for channel_name, channel in self.device.child_list.items():
            for subchnl_name, subchnl in channel.child_list.items():
                connection = '%s_%s' % (channel.parent_port, subchnl.parent_port)
                if connection in data:
                    add_trace(subchnl.name, data[connection], self.name, connection)
        
        return {} 
