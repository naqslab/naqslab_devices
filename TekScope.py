#####################################################################
#                                                                   #
# /TekScope.py                                                      #
#                                                                   #
#                                                                   #
#####################################################################

import numpy as np
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker

from labscript import Device, TriggerableDevice, AnalogIn, config, LabscriptError, set_passed_properties
import labscript_utils.properties

class ScopeChannel(AnalogIn):
    """Labscript device that handles acquisition stuff.
    Connection should be in list of TekScope channels list."""
    description = 'Scope Acquisition Channel Class'
    def __init__(self, name, parent_device, connection):
        Device.__init__(self,name,parent_device,connection)
        self.acquisitions = []
        
    def acquire(self,label,start_time):
        if self.acquisitions:
            raise LabscriptError('Scope Channel %s:%s can only have one acquisition!' % (self.parent_device.name,self.name))
        else:
            self.acquisitions.append({'start_time': start_time,
                                    'label': label})
      
@labscript_device              
class TekScope(TriggerableDevice):
    description = 'Tektronics Digital Oscilliscope'
    allowed_children = [ScopeChannel]
    trigger_duration = 1e-3
    
    @set_passed_properties()
    def __init__(self, name,VISA_name, trigger_device, trigger_connection, **kwargs):
        '''VISA_name can be full VISA connection string or NI-MAX alias.
        Trigger Device should be fast clocked device. '''
        self.BLACS_connection = VISA_name
        TriggerableDevice.__init__(self,name,trigger_device,trigger_connection,**kwargs)
        
        
    def generate_code(self, hdf5_file):
            
        Device.generate_code(self, hdf5_file)
        
        acquisitions = []
        for channel in self.child_devices:
            if channel.acquisitions:
                acquisitions.append((channel.connection,channel.acquisitions[0]['label'],
                channel.acquisitions[0]['start_time']))
        acquisition_table_dtypes = [('connection','a256'),('label','a256'),
                                        ('start_time',float)]
        acquisition_table = np.empty(len(self.child_devices),dtype=acquisition_table_dtypes)
        for i, acq in enumerate(acquisitions):
            acquisition_table[i] = acq   
        
        grp = self.init_device_group(hdf5_file)
        # write table to h5file if non-empty
        if len(acquisition_table):
            grp.create_dataset('ACQUISITIONS',compression=config.compression,
                                data=acquisition_table)
                                
    def acquire(self,start_time):
        '''Call to define time when trigger will happen for scope.'''
        if not self.child_devices:
            raise LabscriptError('No channels acquiring for trigger %s'%self.name)
        else:
            self.parent_device.trigger(start_time,self.trigger_duration)
            for channel in self.child_devices:
                channel.acquire(channel.name,start_time)
            
        
        
from blacs.tab_base_classes import Worker, define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED  
from blacs.device_base_class import DeviceTab
from qtutils import UiLoader
import os

@BLACS_tab
class TekScopeTab(DeviceTab):
    # Status Byte Label Definitions for TDS200/1000/2000 series scopes
    status_byte_labels = {'bit 7':'Power On', 
                          'bit 6':'URQ',
                          'bit 5':'Command Error',
                          'bit 4':'Execution Error',
                          'bit 3':'Device Error',
                          'bit 2':'Query Error',
                          'bit 1':'RQC',
                          'bit 0':'Operation Complete'}
    
    def __init__(self,*args,**kwargs):
        '''You MUST override this class in order to define the device worker for any child devices.
        You then call this parent method to finish initialization.'''
        if not hasattr(self,'device_worker_class'):
            self.device_worker_class = TekScopeWorker
        DeviceTab.__init__(self,*args,**kwargs)
    
    def initialise_GUI(self):
        # load the status_ui for the STB register
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
        self.supports_remote_value_check(False)
        self.supports_smart_programming(True) 
        self.statemachine_timeout_add(5000, self.status_monitor)        

    
    # This function gets the status,
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
class TekScopeWorker(Worker):   
    # define instrument specific read and write strings
    setup_string = ':HEADER OFF;*ESE 60;*SRE 32; *CLS;'
    read_setup_string = ':DATA:SOURCE CH%d;:DAT:ENC RPB;WID 2;'
    read_waveform_parameters_string = ':WFMPRE:XZE?;XIN?;YZE?;YMU?;YOFF?;'
    read_waveform_string = 'CURV?'
    
    # define result parsers, if necessary
    def waveform_parser(self,raw_waveform_array,y0,dy,yoffset):
        '''Parses the numpy array from the CURV? query.'''
        return (raw_waveform_array - yoffset)*dy + y0
    
    def init(self):
        global visa; import visa
        global h5py; import labscript_utils.h5_lock, h5py
        global time; import time
    
        self.VISA_name = self.address
        self.resourceMan = visa.ResourceManager()
        self.connection = self.resourceMan.open_resource(self.VISA_name)
        self.connection.timeout = 10000
        
        # initialization stuff would go here
        self.connection.write(self.setup_string)
        
        # Query device name to ensure supported scope
        ident_string = self.connection.query('*IDN?')
        if ('TEKTRONIX,TDS 2' in ident_string) or ('TEKTRONIX,TDS 1' in ident_string):
            # Scope supported!
            return
        else:
            raise LabscriptError('Device %s with VISA name %s not supported!' % (ident_string,self.VISA_name))
    
    def check_remote_values(self):

        return None
    
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
        
        return self.check_remote_values()
        
        
    def clear(self,value):
        self.connection.clear()
        

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # Store the initial values in case we have to abort and restore them:
        self.initial_values = initial_values
        # Store the final values to for use during transition_to_static:
        self.final_values = {}
        # Store some parameters for saving data later
        self.h5_file = h5file
        self.device_name = device_name
                
        return self.final_values
        
    def abort_transition_to_buffered(self):
        return self.transition_to_manual(True)
        
    def abort_buffered(self):
        return self.transition_to_manual(True)
            
    def transition_to_manual(self,abort = False):
        if not abort:         
            with h5py.File(self.h5_file,'r') as hdf5_file:
                try:
                    # get acquisitions table values so we can close the file
                    acquisitions = hdf5_file['/devices/'+self.device_name+'/ACQUISITIONS'].value
                except:
                        # No acquisitions!
                        return
            # close lock on h5 to read from scope, it takes a while            
            data = {}
            for connection,label,start_time in acquisitions:
                channel_num = int(connection.split(' ')[-1])
                [t0,dt,y0,dy,yoffset] = self.connection.query_ascii_values(self.read_setup_string % channel_num +
                self.read_waveform_parameters_string, container=np.array, separator=';')
                raw_data = self.connection.query_binary_values(self.read_waveform_string,
                datatype='H', is_big_endian=True)
                data[connection] = self.waveform_parser(raw_data,y0,dy,yoffset)
            # Need to calculate the time array
            num_points = len(raw_data)
            tarray = np.arange(0,num_points,1,dtype=np.float64)*dt - t0
            data['time'] = tarray  
            # define the dtypes for the h5 arrays
            dtypes = [('t', np.float64),('values', np.float32)]          
            
            # re-open lock on h5file to save data
            with h5py.File(self.h5_file,'a') as hdf5_file:
                try:
                    measurements = hdf5_file['/data/traces']
                except:
                    # Group doesn't exist yet, create it
                    measurements = hdf5_file.create_group('/data/traces')
                # write out the data to the h5file
                for connection,label,start_time in acquisitions:
                    values = np.empty(num_points,dtype=dtypes)
                    values['t'] = tarray
                    values['values'] = data[connection]
                    measurements.create_dataset(label, data=values)
                    # and save some timing info for reference to labscript time
                    measurements[label].attrs['start_time'] = start_time
            
            
        return True
        
    def shutdown(self):
        self.connection.close()

