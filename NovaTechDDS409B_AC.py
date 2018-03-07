#####################################################################
#                                                                   #
# /NovaTechDDS409B_AC.py                                            #
#                                                                   #
# This code borrows very heavily from NovaTechDDS9m.py              #
# at https://bitbucket.org/labscript_suite/labscript_devices        #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode
    
from labscript_devices import runviewer_parser, labscript_device, BLACS_tab, BLACS_worker

from labscript import IntermediateDevice, DDS, StaticDDS, Device, config, LabscriptError, set_passed_properties
from labscript_utils.unitconversions import NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion

import numpy as np
import labscript_utils.h5_lock, h5py
import labscript_utils.properties

        
@labscript_device
class NovaTechDDS409B_AC(IntermediateDevice):
    description = 'NT-DDS409B-AC'
    allowed_children = [DDS, StaticDDS]
    clock_limit = 9990 # This is a realistic estimate of the max clock rate (100us for TS/pin10 processing to load next value into buffer and 100ns pipeline delay on pin 14 edge to update output values)

    @set_passed_properties(
        property_names = {'connection_table_properties': ['update_mode']}
        )
    def __init__(self, name, parent_device, 
                 com_port = "", baud_rate=19200, update_mode='synchronous', **kwargs):

        IntermediateDevice.__init__(self, name, parent_device, **kwargs)
        self.BLACS_connection = '{:s},{:s}'.format(com_port, str(baud_rate))
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
            # Default calibration classes for the non-static channels:
            return NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion, None
        else:
            return None, None, None
        
        
    def quantise_freq(self, data, device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # Ensure that frequencies are within bounds:
        if np.any(data > 171.1276031e6 )  or np.any(data < 0.1 ):
            raise LabscriptError('{:s} {:s} '.format(device.description, device.name) +
                              'can only have frequencies between 0.1Hz and 171MHz, ' + 
                              'the limit imposed by {:s}.'.format(self.name))
        # It's faster to add 0.5 then typecast than to round to integers first:
        data = np.array((10*data)+0.5,dtype=np.uint32)
        scale_factor = 10
        return data, scale_factor
        
    def quantise_phase(self, data, device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # ensure that phase wraps around:
        data %= 360
        # It's faster to add 0.5 then typecast than to round to integers first:
        scale_factor = 16384/360.0
        data = np.array((scale_factor*data)+0.5,dtype=np.uint16)
        return data, scale_factor
        
    def quantise_amp(self,data,device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # ensure that amplitudes are within bounds:
        if np.any(data > 1 )  or np.any(data < 0):
            raise LabscriptError('{:s} {:s} '.format(device.description, device.name) +
                              'can only have amplitudes between 0 and 1 (Volts peak to peak approx), ' + 
                              'the limit imposed by {:s}.'.format(self.name))
        # It's faster to add 0.5 then typecast than to round to integers first:
        data = np.array((1023*data)+0.5,dtype=np.uint16)
        scale_factor = 1023
        return data, scale_factor
        
    def generate_code(self, hdf5_file):
        DDSs = {}
        for output in self.child_devices:
            # Check that the instructions will fit into RAM:
            if isinstance(output, DDS) and len(output.frequency.raw_output) > 16384 - 2: # -2 to include space for dummy instructions
                raise LabscriptError('{:s} can only support 16383 instructions. '.format(self.name) +
                                     'Please decrease the sample rates of devices on the same clock, ' + 
                                     'or connect {:s} to a different pseudoclock.'.format(self.name))
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError('{:s} {:s} has invalid connection string: \'{:s}\'. '.format(output.description,output.name,str(output.connection)) + 
                                     'Format must be \'channel n\' with n from 0 to 4.')
            DDSs[channel] = output
            
        if not DDSs:
            # if no channels are being used, no need to continue
            return            

        for connection in DDSs:
            if connection in range(4):
                dds = DDSs[connection]   
                dds.frequency.raw_output, dds.frequency.scale_factor = self.quantise_freq(dds.frequency.raw_output, dds)
                dds.phase.raw_output, dds.phase.scale_factor = self.quantise_phase(dds.phase.raw_output, dds)
                dds.amplitude.raw_output, dds.amplitude.scale_factor = self.quantise_amp(dds.amplitude.raw_output, dds)
            else:
                raise LabscriptError('{:s} {:s} has invalid connection string: \'{:s}\'. '.format(dds.description,dds.name,str(dds.connection)) + 
                                     'Format must be \'channel n\' with n from 0 to 4.')
        
        # determine what types of channels are needed
        stat_DDSs = set(DDSs)&set(range(2,4)) 
        if set(DDSs)&set(range(2)):
            dyn_DDSs = range(2)
        else:
            dyn_DDSs = []
        
        if dyn_DDSs:
            # only do dynamic channels if needed    
            dtypes = {'names':['freq{:d}'.format(i) for i in dyn_DDSs] +
                                ['amp{:d}'.format(i) for i in dyn_DDSs] +
                                ['phase{:d}'.format(i) for i in dyn_DDSs],
                                'formats':[np.uint32 for i in dyn_DDSs] +
                                [np.uint16 for i in dyn_DDSs] + 
                                [np.uint16 for i in dyn_DDSs]}  
             
            clockline = self.parent_clock_line
            pseudoclock = clockline.parent_device
            times = pseudoclock.times[clockline]
           
            out_table = np.zeros(len(times),dtype=dtypes)
            out_table['freq0'].fill(1)
            out_table['freq1'].fill(1)
            
            for connection in range(2):
                if not connection in DDSs:
                    continue
                dds = DDSs[connection]
                # The last two instructions are left blank, for BLACS
                # to fill in at program time.
                out_table['freq{:d}'.format(connection)][:] = dds.frequency.raw_output
                out_table['amp{:d}'.format(connection)][:] = dds.amplitude.raw_output
                out_table['phase{:d}'.format(connection)][:] = dds.phase.raw_output
                
            if self.update_mode == 'asynchronous':
                # Duplicate the first line. Otherwise, we are one step ahead in the table
                # from the start of a run. This problem is not completely understood, but this
                # fixes it:
                out_table = np.concatenate([out_table[0:1], out_table])
            
        if stat_DDSs:
            # only do static channels if needed
            static_dtypes = {'names':['freq{:d}'.format(i) for i in stat_DDSs] +
                                ['amp{:d}'.format(i) for i in stat_DDSs] +
                                ['phase{:d}'.format(i) for i in stat_DDSs],
                                'formats':[np.uint32 for i in stat_DDSs] +
                                [np.uint16 for i in stat_DDSs] + 
                                [np.uint16 for i in stat_DDSs]}            
            
            static_table = np.zeros(1, dtype=static_dtypes)
                
            for connection in range(2,4):
                if not connection in DDSs:
                    continue
                dds = DDSs[connection]
                static_table['freq{:d}'.format(connection)] = dds.frequency.raw_output[0]
                static_table['amp{:d}'.format(connection)] = dds.amplitude.raw_output[0]
                static_table['phase{:d}'.format(connection)] = dds.phase.raw_output[0]
            
        # write out data tables
        grp = self.init_device_group(hdf5_file)
        if dyn_DDSs:
            grp.create_dataset('TABLE_DATA',compression=config.compression,data=out_table) 
        if stat_DDSs: 
            grp.create_dataset('STATIC_DATA',compression=config.compression,data=static_table) 
        self.set_property('frequency_scale_factor', dds.frequency.scale_factor, location='device_properties')
        self.set_property('amplitude_scale_factor', dds.amplitude.scale_factor, location='device_properties')
        self.set_property('phase_scale_factor', dds.phase.scale_factor, location='device_properties')



import time

from blacs.tab_base_classes import Worker, define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED  

from blacs.device_base_class import DeviceTab

@BLACS_tab
class NovaTechDDS409B_ACTab(DeviceTab):

    def __init__(self,*args,**kwargs):
        if not hasattr(self,'device_worker_class'):
            self.device_worker_class = NovaTechDDS409B_ACWorker
        DeviceTab.__init__(self,*args,**kwargs)

    def initialise_GUI(self):        
        # Capabilities
        self.base_units =    {'freq':'Hz',          'amp':'Arb',   'phase':'Degrees'}
        self.base_min =      {'freq':0.0,           'amp':0,       'phase':0}
        self.base_max =      {'freq':170.0*10.0**6, 'amp':1,       'phase':360}
        self.base_step =     {'freq':10**6,         'amp':1/1023., 'phase':1}
        self.base_decimals = {'freq':1,             'amp':4,       'phase':3} # TODO: find out what the phase precision is!
        self.num_DDS = 4
        
        # Create DDS Output objects
        dds_prop = {}
        for i in range(self.num_DDS): # 4 is the number of DDS outputs on this device
            dds_prop['channel {:d}'.format(i)] = {}
            for subchnl in ['freq', 'amp', 'phase']:
                dds_prop['channel {:d}'.format(i)][subchnl] = {'base_unit':self.base_units[subchnl],
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
        self.create_worker("main_worker",self.device_worker_class,{'com_port':self.com_port,
                                                              'baud_rate': self.baud_rate,
                                                              'update_mode': self.update_mode})
        self.primary_worker = "main_worker"

        # Set the capabilities of this device
        self.supports_remote_value_check(True)
        self.supports_smart_programming(True) 


@BLACS_worker        
class NovaTechDDS409B_ACWorker(Worker):
    def init(self):
        global serial; import serial
        global h5py; import labscript_utils.h5_lock, h5py
        self.smart_cache = {'STATIC_DATA': None, 'TABLE_DATA': '',
                                'CURRENT_DATA':None}
        self.baud_dict = {9600:'78', 19200:'3c', 38400:'1e',57600:'14',115200:'0a'}
        
        # conversion dictionaries for program_static from 
        # program_manual                      
        self.conv = {'freq':10**(-6),'amp':1023.0,'phase':16384.0/360.0}
        # and from transition_to_buffered
        self.conv_buffered = {'freq':10**(-7),'amp':1,'phase':1}
        
        self.connection = serial.Serial(self.com_port, baudrate = self.baud_rate, timeout=0.1)
        self.connection.readlines()
        
        # to configure baud rate, must determine current device baud rate
        # first check desired, since it's most likely
        connected, response = self.check_connection()
        if not connected:
            # not already set
            bauds = self.baud_dict.keys()
            if self.baud_rate in bauds:
                bauds.remove(self.baud_rate)
            else:
                raise LabscriptError('{:d} baud rate not supported by Novatech 409B'.format(self.baud_rate))
                
            # iterate through other baud-rates to find current
            for rate in bauds:
                self.connection.baudrate = rate
                connected, response = self.check_connection()
                if connected:
                    # found it!
                    break
            
            # now we can set the desired baud rate
            baud_string = b'Kb {:s}\r\n'.format(self.baud_dict[self.baud_rate])
            self.connection.write(baud_string)
            # ensure command finishes before switching rates in pyserial
            time.sleep(0.1)
            self.connection.baudrate = self.baud_rate
            connected, response = self.check_connection()
            if not connected:
                raise LabscriptError('Error: Failed to execute command {:s}'.format(baud_string))           
        
        self.connection.write(b'e d\r\n')
        response = self.connection.readline()
        if response == 'e d\r\n':
            # if echo was enabled, then the command to disable it echos back at us!
            response = self.connection.readline()
        if response != "OK\r\n":
            raise Exception('Error: Failed to execute command: "e d". Cannot connect to the device.')
        
        self.connection.write(b'I a\r\n')
        if self.connection.readline() != "OK\r\n":
            raise Exception('Error: Failed to execute command: "I a"')
        
        self.connection.write(b'm 0\r\n')
        if self.connection.readline() != "OK\r\n":
            raise Exception('Error: Failed to execute command: "m 0"')
        
        # populate the 'CURRENT_DATA' dictionary    
        self.check_remote_values()
        
    def check_connection(self):
        '''Sends non-command and tests for correct response
        returns tuple of connection state and reponse string'''
        # check twice since false positive possible on first check
        # use readlines in case echo is on
        self.connection.write(b'\r\n')
        self.connection.readlines()       
        self.connection.write(b'\r\n')
        response = self.connection.readlines()[-1]
        connected = response == 'OK\r\n'
        
        return connected, response
        
    def check_remote_values(self):
        # Get the currently output values:
        self.connection.write(b'QUE\r\n')
        try:
            response = [self.connection.readline() for i in range(5)]
        except socket.timeout:
            raise Exception('Failed to execute command "QUE". Cannot connect to device.')
        results = {}
        for i, line in enumerate(response[:4]):
            results['channel {:d}'.format(i)] = {}
            freq, phase, amp, ignore, ignore, ignore, ignore = line.split()
            # Convert hex multiple of 0.1 Hz to MHz:
            results['channel {:d}'.format(i)]['freq'] = float(int(freq,16))/10.0
            # Convert hex to int:
            results['channel {:d}'.format(i)]['amp'] = int(amp,16)/1023.0
            # Convert hex fraction of 16384 to degrees:
            results['channel {:d}'.format(i)]['phase'] = int(phase,16)*360/16384.0
            
            self.smart_cache['CURRENT_DATA'] = results
        return results
        
    def program_manual(self,front_panel_values):
        for i in range(4):    
            # and for each subchnl in the DDS,
            for subchnl in ['freq','amp','phase']:
                # don't program if setting is the same
                if self.smart_cache['CURRENT_DATA']['channel {:d}'.format(i)][subchnl] == front_panel_values['channel {:d}'.format(i)][subchnl]:
                    continue       
                # Program the sub channel
                self.program_static(i,subchnl,
                    front_panel_values['channel {:d}'.format(i)][subchnl]*self.conv[subchnl])
                # Now that a static update has been done, 
                # we'd better invalidate the saved STATIC_DATA for the channel:
                self.smart_cache['STATIC_DATA'] = None
        return self.check_remote_values()

    def program_static(self,channel,type,value):            
        if type == 'freq':
            command = b'F{:d} {:.7f}\r\n'.format(channel,value)
            self.connection.write(command)
            if self.connection.readline() != "OK\r\n":
                raise Exception('Error: Failed to execute command: {:s}'.format(command))
        elif type == 'amp':
            command = b'V{:d} {:d}\r\n'.format(channel,int(value))
            self.connection.write(command)
            if self.connection.readline() != "OK\r\n":
                raise Exception('Error: Failed to execute command: {:s}'.format(command))
        elif type == 'phase':
            command = b'P{:d} {:d}\r\n'.format(channel,int(value))
            self.connection.write(command)
            if self.connection.readline() != "OK\r\n":
                raise Exception('Error: Failed to execute command: {:s}'.format(command))
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
                                
                # need to infer which channels to program
                num_chan = len(data)//3
                channels = [int(name[-1]) for name in data.dtype.names[0:num_chan]]
                
                for i in channels:
                    for subchnl in ['freq','amp','phase']:
                        curr_value = self.smart_cache['CURRENT_DATA']['channel {:d}'.format(i)][subchnl]*self.conv[subchnl]
                        value = data[subchnl+str(i)]*self.conv_buffered[subchnl]
                        if value == curr_value:
                            continue
                        self.program_static(i,subchnl,value)
                        self.final_values['channel {:d}'.format(i)][subchnl] = value/self.conv[subchnl]
                    
        # Now program the buffered outputs:
        if table_data is not None:
            data = table_data
            for i, line in enumerate(data):
                st = time.time()
                oldtable = self.smart_cache['TABLE_DATA']
                for ddsno in range(2):
                    if fresh or i >= len(oldtable) or (line['freq%d'%ddsno],line['phase%d'%ddsno],line['amp%d'%ddsno]) != (oldtable[i]['freq%d'%ddsno],oldtable[i]['phase%d'%ddsno],oldtable[i]['amp%d'%ddsno]):
                        self.connection.write(b't%d %04x %08x,%04x,%04x,ff\r\n'%(ddsno, i,line['freq%d'%ddsno],line['phase%d'%ddsno],line['amp%d'%ddsno]))
                        self.connection.readline()
                et = time.time()
                tt=et-st
                self.logger.debug('Time spent on line {:s}: {:s}'.format(i,tt))
            # Store the table for future smart programming comparisons:
            try:
                self.smart_cache['TABLE_DATA'][:len(data)] = data
                self.logger.debug('Stored new table as subset of old table')
            except: # new table is longer than old table
                self.smart_cache['TABLE_DATA'] = data
                self.logger.debug('New table is longer than old table and has replaced it.')
                
            # Get the final values of table mode so that the GUI can
            # reflect them after the run:
            self.final_values['channel 0'] = {}
            self.final_values['channel 1'] = {}
            self.final_values['channel 0']['freq'] = data[-1]['freq0']/10.0
            self.final_values['channel 1']['freq'] = data[-1]['freq1']/10.0
            self.final_values['channel 0']['amp'] = data[-1]['amp0']/1023.0
            self.final_values['channel 1']['amp'] = data[-1]['amp1']/1023.0
            self.final_values['channel 0']['phase'] = data[-1]['phase0']*360/16384.0
            self.final_values['channel 1']['phase'] = data[-1]['phase1']*360/16384.0
            
            # Transition to table mode:
            self.connection.write(b'm t\r\n')
            self.connection.readline()
            if self.update_mode == 'synchronous':
                # Transition to hardware synchronous updates:
                self.connection.write(b'I e\r\n')
                self.connection.readline()
                # We are now waiting for a rising edge to trigger the output
                # of the second table pair (first of the experiment)
            elif self.update_mode == 'asynchronous':
                # Output will now be updated on falling edges.
                pass
            else:
                raise ValueError('invalid update mode {:s}'.format(str(self.update_mode)))
                
            
        return self.final_values
    
    def abort_transition_to_buffered(self):
        return self.transition_to_manual(True)
        
    def abort_buffered(self):
        # TODO: untested
        return self.transition_to_manual(True)
    
    def transition_to_manual(self,abort = False):
        self.connection.write(b'm 0\r\n')
        if self.connection.readline() != "OK\r\n":
            raise Exception('Error: Failed to execute command: "m 0"')
        self.connection.write(b'I a\r\n')
        if self.connection.readline() != "OK\r\n":
            raise Exception('Error: Failed to execute command: "I a"')
        if abort:
            # If we're aborting the run, then we need to reset DDSs 2 and 3 to their initial values.
            # 0 and 1 will already be in their initial values. We also need to invalidate the smart
            # programming cache for them.
            values = self.initial_values
            DDSs = [2,3]
            self.smart_cache['STATIC_DATA'] = None
        else:
            # If we're not aborting the run, then we need to set DDSs 0 and 1 to their final values.
            # 2 and 3 will already be in their final values.
            values = self.final_values
            DDSs = [0,1]
            
        # only program the channels that we need to
        for channel in values:
            ddsnum = int(channel.split(' ')[-1])
            if ddsnum not in DDSs:
                continue
            for subchnl in ['freq','amp','phase']:            
                self.program_static(ddsnum,subchnl,values[channel][subchnl]*self.conv[subchnl])
            
        # return True to indicate we successfully transitioned back to manual mode
        return True
                     
    def shutdown(self):
        self.connection.close()        
        
        
@runviewer_parser
class NovaTechDDS409B_ACParser(object):    
    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device
        self.dyn_chan = [0,1]
        self.static_chan = [2,3]
            
    def get_traces(self, add_trace, clock=None):
        if clock is None:
            # we're the master pseudoclock, software triggered. So we don't have to worry about trigger delays, etc
            raise Exception('No clock passed to {:s}. The NovaTechDDS409B_AC must be clocked by another device.'.format(self.name))
        
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
            if 'TABLE_DATA' in hdf5_file['devices/{:s}'.format(self.name)]:
                table_data = hdf5_file['devices/{:s}/TABLE_DATA'.format(self.name)][:]
                connection_table_properties = labscript_utils.properties.get(hdf5_file, self.name, 'connection_table_properties')
                update_mode = getattr(connection_table_properties, 'update_mode', 'synchronous')
                synchronous_first_line_repeat = getattr(connection_table_properties, 'synchronous_first_line_repeat', False)
                if update_mode == 'asynchronous' or synchronous_first_line_repeat:
                    table_data = table_data[1:]
                for i in self.dyn_chan:
                    for sub_chnl in ['freq', 'amp', 'phase']:
                        data['channel {:d}_{:s}'.format(i,sub_chnl)] = table_data['{:s}{:d}'.format(sub_chnl,i)][:]
                                
            if 'STATIC_DATA' in hdf5_file['devices/{:s}'.format(self.name)]:
                static_data = hdf5_file['devices/{:s}/STATIC_DATA'.format(self.name)][:]
                num_chan = len(static_data)//3
                channels = [int(name[-1]) for name in static_data.dtype.names[0:num_chan]]
                for i in channels:
                    for sub_chnl in ['freq', 'amp', 'phase']:
                        data['channel {:d}_{:s}'.format(i,sub_chnl)] = np.empty((len(clock_ticks),))
                        data['channel {:d}_{:s}'.format(i,sub_chnl)].fill(static_data['{:s}{:d}'.format(sub_chnl,i)][0])
            
        
        for channel, channel_data in data.items():
            data[channel] = (clock_ticks, channel_data)
        
        for channel_name, channel in self.device.child_list.items():
            for subchnl_name, subchnl in channel.child_list.items():
                connection = '{:s}_{:s}'.format(channel.parent_port, subchnl.parent_port)
                if connection in data:
                    add_trace(subchnl.name, data[connection], self.name, connection)
        
        return {}
    
