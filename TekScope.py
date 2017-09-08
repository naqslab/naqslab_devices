#####################################################################
#                                                                   #
# /TekScope.py                                                      #
#                                                                   #
#                                                                   #
#####################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from labscript_devices.VISA import VISATab, VISAWorker
from labscript import Device, TriggerableDevice, AnalogIn, config, LabscriptError, set_passed_properties
import labscript_utils.properties

class ScopeChannel(AnalogIn):
    """Labscript device that handles acquisition stuff.
    Connection should be in list of TekScope channels list."""
    description = 'Scope Acquisition Channel Class'
    def __init__(self, name, parent_device, connection):
        Device.__init__(self,name,parent_device,connection)
        self.acquisitions = []
        
    def acquire(self):
        if self.acquisitions:
            raise LabscriptError('Scope Channel {0:s}:{1:s} can only have one acquisition!'.format(self.parent_device.name,self.name))
        else:
            self.acquisitions.append({'label': self.name})
      
@labscript_device              
class TekScope(TriggerableDevice):
    description = 'Tektronics Digital Oscilliscope'
    allowed_children = [ScopeChannel]
    trigger_duration = 1e-3
    
    @set_passed_properties(property_names = {
        "device_properties":["VISA_name"]}
        )
    def __init__(self, name,VISA_name, trigger_device, trigger_connection, **kwargs):
        '''VISA_name can be full VISA connection string or NI-MAX alias.
        Trigger Device should be fast clocked device. '''
        self.VISA_name = VISA_name
        self.BLACS_connection = VISA_name
        TriggerableDevice.__init__(self,name,trigger_device,trigger_connection,**kwargs)
        
        # initialize start_time variable
        self.trigger_time = None
        
        
    def generate_code(self, hdf5_file):
            
        Device.generate_code(self, hdf5_file)
        
        acquisitions = []
        for channel in self.child_devices:
            if channel.acquisitions:
                acquisitions.append((channel.connection,channel.acquisitions[0]['label']))
        acquisition_table_dtypes = np.dtype({'names':['connection','label'],'formats':['a256','a256']})
        acquisition_table = np.empty(len(acquisitions),dtype=acquisition_table_dtypes)
        for i, acq in enumerate(acquisitions):
            acquisition_table[i] = acq   
        
        grp = self.init_device_group(hdf5_file)
        # write table to h5file if non-empty
        if len(acquisition_table):
            grp.create_dataset('ACQUISITIONS',compression=config.compression,
                                data=acquisition_table)
            grp['ACQUISITIONS'].attrs['trigger_time'] = self.trigger_time
                                
    def acquire(self,start_time):
        '''Call to define time when trigger will happen for scope.'''
        if not self.child_devices:
            raise LabscriptError('No channels acquiring for trigger {0:s}'.format(self.name))
        else:
            self.parent_device.trigger(start_time,self.trigger_duration)
            self.trigger_time = start_time

@BLACS_tab
class TekScopeTab(VISATab):
    # Event Byte Label Definitions for TDS200/1000/2000 series scopes
    # Used bits set by '*ESE' command in setup string of worker class
    status_byte_labels = {'bit 7':'Unused', 
                          'bit 6':'Unused',
                          'bit 5':'Command Error',
                          'bit 4':'Execution Error',
                          'bit 3':'Device Error',
                          'bit 2':'Query Error',
                          'bit 1':'Unused',
                          'bit 0':'Unused'}
    
    def __init__(self,*args,**kwargs):
        if not hasattr(self,'device_worker_class'):
            self.device_worker_class = TekScopeWorker
        VISATab.__init__(self,*args,**kwargs)
    
    def initialise_GUI(self):
        # Call the VISATab parent to initialise the STB ui and set the worker
        VISATab.initialise_GUI(self)

        # Set the capabilities of this device
        self.supports_remote_value_check(False)
        self.supports_smart_programming(False) 
        self.statemachine_timeout_add(5000, self.status_monitor)        
       
@BLACS_worker
class TekScopeWorker(VISAWorker):   
    # define instrument specific read and write strings
    setup_string = ':HEADER OFF;*ESE 60;*SRE 32;*CLS;:DAT:ENC RIB;WID 2;'
    read_y_parameters_string = ':DAT:SOU CH%d;:WFMPRE:YZE?;YMU?;YOFF?'
    read_x_parameters_string = ':WFMPRE:XZE?;XIN?'
    read_waveform_string = 'CURV?'
    
    # define result parser
    def waveform_parser(self,raw_waveform_array,y0,dy,yoffset):
        '''Parses the numpy array from the CURV? query.'''
        return (raw_waveform_array - yoffset)*dy + y0
    
    def init(self):
        # import h5py with locks
        global h5py; import labscript_utils.h5_lock, h5py
        # Call the VISA init to initialise the VISA connection
        VISAWorker.init(self)
        # Override the timeout for longer scope waits
        self.connection.timeout = 10000
        
        # Query device name to ensure supported scope
        ident_string = self.connection.query('*IDN?')
        if ('TEKTRONIX,TDS 2' in ident_string) or ('TEKTRONIX,TDS 1' in ident_string):
            # Scope supported!
            pass
        else:
            raise LabscriptError('Device {0:s} with VISA name {1:s} not supported!'.format(ident_string,self.VISA_name))  
        
        # initialization stuff
        self.connection.write(self.setup_string)
            
    def transition_to_manual(self,abort = False):
        if not abort:         
            with h5py.File(self.h5_file,'r') as hdf5_file:
                try:
                    # get acquisitions table values so we can close the file
                    acquisitions = hdf5_file['/devices/'+self.device_name+'/ACQUISITIONS'].value
                    trigger_time = hdf5_file['/devices/'+self.device_name+'/ACQUISITIONS'].attrs['trigger_time']
                except:
                    # No acquisitions!
                    return True
            # close lock on h5 to read from scope, it takes a while            
            data = {}
            for connection,label in acquisitions:
                channel_num = int(connection.split(' ')[-1])
                [y0,dy,yoffset] = self.connection.query_ascii_values(self.read_y_parameters_string % channel_num, container=np.array, separator=';')
                raw_data = self.connection.query_binary_values(self.read_waveform_string,
                datatype='h', is_big_endian=True, container=np.array)
                data[connection] = self.waveform_parser(raw_data,y0,dy,yoffset)
            # Need to calculate the time array
            num_points = len(raw_data)
            # read out the time parameters once outside the loop to save time
            [t0, dt] = self.connection.query_ascii_values(self.read_x_parameters_string,
                container=np.array, separator=';')
            data['time'] = np.arange(0,num_points,1,dtype=np.float64)*dt + t0
            # define the dtypes for the h5 arrays
            dtypes = np.dtype({'names':['t','values'],'formats':[np.float64,np.float32]})         
            
            # re-open lock on h5file to save data
            with h5py.File(self.h5_file,'a') as hdf5_file:
                try:
                    measurements = hdf5_file['/data/traces']
                except:
                    # Group doesn't exist yet, create it
                    measurements = hdf5_file.create_group('/data/traces')
                # write out the data to the h5file
                for connection,label in acquisitions:
                    values = np.empty(num_points,dtype=dtypes)
                    values['t'] = data['time']
                    values['values'] = data[connection]
                    measurements.create_dataset(label, data=values)
                    # and save some timing info for reference to labscript time
                    measurements[label].attrs['trigger_time'] = trigger_time
            
            
        return True
        
    def check_status(self):
        # Tek scopes don't say anything useful in the stb, using the event register instead
        results = {}
        esr = int(self.connection.query('*ESR?'))

        #get the events and convert to binary, and take off the '0b' header:
        status = bin(esr)[2:]
        # if the event is less than 8 bits long, pad the start with zeros!
        while len(status)<8:
            status = '0'+status
        # reverse the status string so bit 0 is first indexed
        status = status[::-1]
        # fill the status byte dictionary
        for i in range(0,8):
            results['bit '+str(i)] = bool(int(status[i]))
        # if esr is non-zero, read out the error message and report
        if esr != 0:
            errors = self.connection.query('ALLEV?')
            raise LabscriptError('Tek Scope VISA device {0:s} has Errors in Queue: \n{1:s}'.format(self.VISA_name,errors))
            
        return results

