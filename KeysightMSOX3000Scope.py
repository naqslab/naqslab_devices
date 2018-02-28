#####################################################################
#                                                                   #
# /KeysightMSOX3000.py                                              #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

import numpy as np
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from naqslab_devices.VISA import VISATab, VISAWorker
from naqslab_devices.TekScope import ScopeChannel
from labscript import Device, TriggerableDevice, AnalogIn, DigitalQuantity, config, LabscriptError, set_passed_properties
import labscript_utils.properties

class CounterScopeChannel(ScopeChannel):
    """Labscript device that handles acquisition stuff.
    Also specifies if pulse counting on analog channel.
    counting assumes tuple with (type,polarity)"""
    description = 'Scope Acquisition Channel Class with Pulse Counting'
    def __init__(self, name, parent_device, connection):
        ScopeChannel.__init__(self,name,parent_device,connection)
        self.counts = []                       
        
    def count(self,typ,pol):
        # guess we can allow multiple types of counters per channel
        if (typ in ['pulse', 'edge']) and (pol in ['pos', 'neg']):
            self.counts.append({'type':typ,'polarity':pol})
        else:
            raise LabscriptError('Invalid counting parameters for {0:s}:{1:s}'.format(self.parent_name,self.name))        
        
      
@labscript_device              
class KeysightMSOX3000Scope(TriggerableDevice):
    description = 'Keysight MSO-X3000 Series Digital Oscilliscope'
    allowed_children = [ScopeChannel]
    
    @set_passed_properties(property_names = {
        "device_properties":["VISA_name"]}
        )
    def __init__(self, name, VISA_name, trigger_device, trigger_connection, 
        num_AI=4, DI=True, trigger_duration=1e-3, **kwargs):
        '''VISA_name can be full VISA connection string or NI-MAX alias.
        Trigger Device should be fast clocked device. 
        num_AI sets number of analog input channels, default 4
        DI sets if DI are present, default True
        trigger_duration set scope trigger duration, default 1ms'''
        self.VISA_name = VISA_name
        self.BLACS_connection = VISA_name
        TriggerableDevice.__init__(self,name,trigger_device,trigger_connection,**kwargs)
        
        self.trigger_duration = trigger_duration
        self.allowed_analog_chan = ['Channel {0:d}'.format(i) for i in range(1,num_AI+1)]
        if DI:
            self.allowed_pod1_chan = ['Digital {0:d}'.format(i) for i in range(0,8)]
            self.allowed_pod2_chan = ['Digital {0:d}'.format(i) for i in range(8,16)]        
        
    def generate_code(self, hdf5_file):
            
        Device.generate_code(self, hdf5_file)
        trans = {'pulse':'PUL','edge':'EDG','pos':'P','neg':'N'}
        
        acqs = {'ANALOG':[],'POD1':[],'POD2':[]}
        for channel in self.child_devices:
            if channel.acquisitions:
                # make sure channel is allowed
                if channel.connection in self.allowed_analog_chan:
                    acqs['ANALOG'].append((channel.connection,channel.acquisitions[0]['label']))
                elif channel.connection in self.allowed_pod1_chan:
                    acqs['POD1'].append((channel.connection,channel.acquisitions[0]['label']))
                elif channel.connection in self.allowed_pod2_chan:
                    acqs['POD2'].append((channel.connection,channel.acquisitions[0]['label']))
                else:
                    raise LabscriptError('{0:s} is not a valid channel.'.format(channel.connection))
        
        acquisition_table_dtypes = np.dtype({'names':['connection','label'],'formats':['a256','a256']})
        
        grp = self.init_device_group(hdf5_file)
        # write tables if non-empty to h5_file                        
        for acq_group, acq_chan in acqs.items():
            if len(acq_chan):
                table = np.empty(len(acq_chan),dtype=acquisition_table_dtypes)
                for i, acq in enumerate(acq_chan):
                    table[i] = acq
                grp.create_dataset(acq_group+'_ACQUISITIONS',compression=config.compression,
                                    data=table)
                grp[acq_group+'_ACQUISITIONS'].attrs['trigger_time'] = self.trigger_time
                                    
        # now do the counters
        counts = []
        for channel in self.child_devices:
            if hasattr(channel, 'counts'):
                for counter in channel.counts:
                    counts.append((channel.connection,
                                    trans[counter['type']],
                                    trans[counter['polarity']]))
        counts_table_dtypes = np.dtype({'names':['connection','type','polarity'],'formats':['a256','a256','a256']})
        counts_table = np.empty(len(counts),dtype=counts_table_dtypes)
        for i,count in enumerate(counts):
            counts_table[i] = count
        if len(counts_table):
            grp.create_dataset('COUNTERS',compression=config.compression,data=counts_table)
            grp['COUNTERS'].attrs['trigger_time'] = self.trigger_time
                                
    def acquire(self,start_time):
        '''Call to define time when trigger will happen for scope.'''
        if not self.child_devices:
            raise LabscriptError('No channels acquiring for trigger {0:s}'.format(self.name))
        else:
            self.parent_device.trigger(start_time,self.trigger_duration)
            self.trigger_time = start_time

@BLACS_tab
class KeysightMSOX3000ScopeTab(VISATab):
    # Event Byte Label Definitions for MSO-X3000 series scopes
    # Used bits set by '*ESE' command in setup string of worker class
    status_byte_labels = {'bit 7':'Powered On', 
                          'bit 6':'Button Pressed',
                          'bit 5':'Command Error',
                          'bit 4':'Execution Error',
                          'bit 3':'Device Error',
                          'bit 2':'Query Error',
                          'bit 1':'Unused',
                          'bit 0':'Operation Complete'}
    
    def __init__(self,**kwargs):
        if not hasattr(self,'device_worker_class'):
            self.device_worker_class = KeysightMSOX3000Worker
        VISATab.__init__(self,**kwargs)
    
    def initialise_GUI(self):
        # Call the VISATab parent to initialise the STB ui and set the worker
        VISATab.initialise_GUI(self)

        # Set the capabilities of this device
        self.supports_remote_value_check(False)
        self.supports_smart_programming(True) 
        self.statemachine_timeout_add(5000, self.status_monitor)        
       
@BLACS_worker
class KeysightMSOX3000Worker(VISAWorker):   
    # define instrument specific read and write strings
    setup_string = '*ESE 60;*SRE 32;*CLS;:WAV:BYT MSBF;UNS ON;POIN:MODE RAW'
    # *ESE does not disable bits in ESR, just their reporting to STB
    # need to use our own mask
    esr_mask = 60
    # note that analog & digital channels require different :WAV:FORM commands
    read_analog_parameters_string = ':WAV:FORM WORD;SOUR CHAN{0:d};PRE?'
    read_dig_parameters_string = ':WAV:FORM BYTE;SOUR POD{0:d};PRE?'
    read_waveform_string = ':WAV:DATA?'
    read_counter_string = ':MEAS:{0:s}{1:s}? CHAN{2:d}'
    model_ident = 'MSO-X 3'
    
    # define result parser
    def analog_waveform_parser(self,raw_waveform_array,y0,dy,yoffset):
        '''Parses the numpy array from the analog waveform query.'''
        return (raw_waveform_array - yoffset)*dy + y0
        
    def digital_pod_parser(self,raw_pod_array):
        '''Unpacks the bits for a pod array
        Columns returned are in bit order [7,6,5,4,3,2,1,0]'''
        return np.unpackbits(raw_pod_array.astype(np.uint8),axis=0).reshape((-1,8),order='C')
        
    def error_parser(self,error_return_string):
        '''Parses the strings returned by :SYST:ERR?
        Returns int_code, err_string'''
        return int(error_return_string.split(',')[0]), error_return_string        
    
    def init(self):
        # import h5py with locks
        global h5py; import labscript_utils.h5_lock, h5py
        # Call the VISA init to initialise the VISA connection
        VISAWorker.init(self)
        # Override the timeout for longer scope waits
        self.connection.timeout = 10000
        
        # Query device name to ensure supported scope
        ident_string = self.connection.query('*IDN?')
        if ('KEYSIGHT' in ident_string) and (model_ident in ident_string):
            # Scope supported!
            pass
        else:
            raise LabscriptError('Device {0:s} with VISA name {0:s} not supported!'.format(ident_string,self.VISA_name))  
        
        # initialization stuff
        self.connection.write(self.setup_string)
        # initialize smart cache
        self.smart_cache = {'COUNTERS': None}
        
    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        '''This only configures counters, if any are defined'''
        VISAWorker.transition_to_buffered(self,device_name,h5file,initial_values,fresh)
        
        data = None
        refresh = False
        send_trigger = False
        with h5py.File(h5file) as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            if 'COUNTERS' in group:
                data = group['COUNTERS'][:]
            if len(group):
                send_trigger = True

        if data is not None:
            #check if refresh needed
            if not fresh:
                try:
                    refresh = not np.all(np.equal(data,self.smart_cache['COUNTERS']))
                except ValueError:
                    # arrays not of same size
                    refresh = True
            if fresh or refresh:
                for connection,typ,pol in data:
                    chan_num = int(connection.split(' ')[-1])
                    self.connection.write(':MEAS:{0:s}{1:s} CHAN{2:d}'.format(pol,typ,chan_num))
                    
                    self.smart_cache['COUNTERS'] = data
        
        if send_trigger:            
            # put scope into single mode
            # necessary since :WAV:DATA? clears data and wait for fresh data
            # when in continuous run mode
            self.connection.write(':DIG')
        
        return self.final_values        
            
    def transition_to_manual(self,abort = False):
        if not abort:         
            with h5py.File(self.h5_file,'r') as hdf5_file:
                # get acquisitions table values so we can close the file
                try:
                    location = '/devices/'+self.device_name+'/ANALOG_ACQUISITIONS'
                    analog_acquisitions = hdf5_file[location].value
                    trigger_time = hdf5_file[location].attrs['trigger_time']
                except:
                    # No analog acquisitions!
                    analog_acquisitions = np.empty(0)
                try:
                    location = '/devices/'+self.device_name+'/POD1_ACQUISITIONS'
                    pod1_acquisitions = hdf5_file[location].value
                    trigger_time = hdf5_file[location].attrs['trigger_time']
                except:
                    # No acquisitions in first digital Pod
                    pod1_acquisitions = np.empty(0)
                try:
                    location = '/devices/'+self.device_name+'/POD2_ACQUISITIONS'
                    pod2_acquisitions = hdf5_file[location].value
                    trigger_time = hdf5_file[location].attrs['trigger_time']
                except:
                    # No acquisitions in second digital Pod
                    pod2_acquisitions = np.empty(0)
                try:
                    location = '/devices/'+self.device_name+'/COUNTERS'
                    counters = hdf5_file[location].value
                    trigger_time = hdf5_file[location].attrs['trigger_time']
                except:
                    # no counters
                    counters = np.empty(0)
                # return if no acquisitions at all
                if not len(analog_acquisitions) and not len(pod1_acquisitions) and not len(pod2_acquisitions) and not len(counters):
                    return True
            # close lock on h5 to read from scope, it takes a while
            
            data = {}
            # read analog channels if they exist
            if len(analog_acquisitions):           
                for connection,label in analog_acquisitions:
                    channel_num = int(connection.split(' ')[-1])
                    # read an analog channel
                    # use larger chunk size for faster large data reads
                    [form,typ,Apts,cnt,Axinc,Axor,Axref,yinc,yor,yref] = self.connection.query_ascii_values(self.read_analog_parameters_string.format(channel_num))
                    if Apts*2+11 >= 400000:   # Note that +11 accounts for IEEE488.2 waveform header, not true in unicode (ie Python 3+)
                        default_chunk = self.connection.chunk_size
                        self.connection.chunk_size = int(Apts*2+11)
                    raw_data = self.connection.query_binary_values(self.read_waveform_string,datatype='H', is_big_endian=True, container=np.array)
                    if Apts*2+11 >= 400000:
                        self.connection.chunk_size = default_chunk
                    data[connection] = self.analog_waveform_parser(raw_data,yor,yinc,yref)
                # create the time array
                data['Analog Time'] = np.arange(Axref,Axref+Apts,1,dtype=np.float64)*Axinc + Axor
           
            # read pod 1 channels if necessary     
            if len(pod1_acquisitions):
                # use larger chunk size for faster large data reads
                [form,typ,Dpts,cnt,Dxinc,Dxor,Dxref,yinc,yor,yref] = self.connection.query_ascii_values(self.read_dig_parameters_string.format(1))
                if Dpts+11 >= 400000:
                    default_chunk = self.connection.chunk_size
                    self.connection.chunk_size = int(Dpts+11)
                raw_data = self.connection.query_binary_values(self.read_waveform_string,datatype='B',is_big_endian=True,container=np.array)
                if Dpts+11 >= 400000:
                    self.connection.chunk_size = default_chunk
                conv_data = self.digital_pod_parser(raw_data)
                # parse out desired channels
                for connection,label in pod1_acquisitions:
                    channel_num = int(connection.split(' ')[-1])
                    data[connection] = conv_data[:,(7-channel_num)%8]
                    
            # read pod 2 channels if necessary     
            if len(pod2_acquisitions):     
                # use larger chunk size for faster large data reads
                [form,typ,Dpts,cnt,Dxinc,Dxor,Dxref,yinc,yor,yref] = self.connection.query_ascii_values(self.read_dig_parameters_string.format(2))
                if Dpts+11 >= 400000:
                    default_chunk = self.connection.chunk_size
                    self.connection.chunk_size = int(Dpts+11)
                raw_data = self.connection.query_binary_values(self.read_waveform_string,datatype='B',is_big_endian=True,container=np.array)
                if Dpts+11 >= 400000:
                    self.connection.chunk_size = default_chunk
                conv_data = self.digital_pod_parser(raw_data)
                # parse out desired channels
                for connection,label in pod2_acquisitions:
                    channel_num = int(connection.split(' ')[-1])
                    data[connection] = conv_data[:,(15-channel_num)%8]
                    
            if len(pod1_acquisitions) or len(pod2_acquisitions):
                # create the digital time array if needed
                # Note that digital traces always have fewer pts than analog
                data['Digital Time'] = np.arange(Dxref,Dxref+Dpts,1,dtype=np.float64)*Dxinc + Dxor
                    
            # read counters if necesary
            count_data = {}
            if len(counters):
                for connection,typ,pol in counters:
                    chan_num = int(connection.split(' ')[-1])
                    count_data[connection] = float(self.connection.query(self.read_counter_string.format(pol,typ,chan_num)))                     
            
            # define the dtypes for the h5 arrays
            dtypes_analog = np.dtype({'names':['t','values'],'formats':[np.float64,np.float32]})  
            dtypes_digital = np.dtype({'names':['t','values'],'formats':[np.float64,np.uint8]})      
            
            # re-open lock on h5file to save data
            with h5py.File(self.h5_file,'a') as hdf5_file:
                try:
                    measurements = hdf5_file['/data/traces']
                except:
                    # Group doesn't exist yet, create it
                    measurements = hdf5_file.create_group('/data/traces')
                # write out the data to the h5file
                for connection,label in analog_acquisitions:
                    values = np.empty(len(data[connection]),dtype=dtypes_analog)
                    values['t'] = data['Analog Time']
                    values['values'] = data[connection]
                    measurements.create_dataset(label, data=values)
                    # and save some timing info for reference to labscript time
                    measurements[label].attrs['trigger_time'] = trigger_time
                for connection,label in pod1_acquisitions:
                    values = np.empty(len(data[connection]),dtype=dtypes_digital)
                    values['t'] = data['Digital Time']
                    values['values'] = data[connection]
                    measurements.create_dataset(label, data=values)
                    # and save some timing info for reference to labscript time
                    measurements[label].attrs['trigger_time'] = trigger_time  
                for connection,label in pod2_acquisitions:
                    values = np.empty(len(data[connection]),dtype=dtypes_digital)
                    values['t'] = data['Digital Time']
                    values['values'] = data[connection]
                    measurements.create_dataset(label, data=values)
                    # and save some timing info for reference to labscript time
                    measurements[label].attrs['trigger_time'] = trigger_time   
            
                # Now read out the counters if they exist
                if len(counters):
                    try:
                        counts = hdf5_file['/data/'+self.device_name]
                    except:
                        counts = hdf5_file.create_group('/data/'+self.device_name)
                        
                    for connection,typ,pol in counters:
                        counts.attrs['{0:s}:{1:s}{2:s}'.format(connection,pol,typ)] = count_data[connection]
                        counts.attrs['trigger_time'] = trigger_time                                 
            
        return True
        
    def check_status(self):
        # Scope don't say anything useful in the stb, using the event register instead
        esr = int(self.connection.query('*ESR?'))

        # if esr is non-zero, read out the error message and report
        if (esr & self.esr_mask) != 0:
            # read out errors from queue until response == 0
            err_string = ''
            while True:
                code, return_string = self.error_parser(self.connection.query(':SYST:ERR?'))
                if code != 0:
                    err_string += return_string
                else:
                    break
                
            raise LabscriptError('Keysight Scope VISA device {0:s} has Errors in Queue: \n{1:s}'.format(self.VISA_name,err_string)) 
        return self.convert_register(esr)

