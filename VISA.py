#####################################################################
#                                                                   #
# /VISA.py                                                          #
#                                                                   #
#                                                                   #
#####################################################################

from labscript_devices import labscript_device, BLACS_tab, BLACS_worker

from labscript import Device, LabscriptError, set_passed_properties
import labscript_utils.properties
      
@labscript_device              
class VISA(Device):
    description = 'VISA Compatible Instrument'
    allowed_children = []
    
    @set_passed_properties()
    def __init__(self, name, parent_device, VISA_name, **kwargs):
        '''VISA_name can be full VISA connection string or NI-MAX alias.
        Trigger Device should be fast clocked device. '''
        self.BLACS_connection = VISA_name
        Device.__init__(self, name, parent_device, VISA_name)
        
    def generate_code(self, hdf5_file):
        # over-ride this method for child classes
        # it should not return anything
        raise LabscriptError('generate_code() must be overridden for %s'%name)
        
        
from blacs.tab_base_classes import Worker, define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED  
from blacs.device_base_class import DeviceTab
from qtutils import UiLoader
import os
import sys

# Imports for handling icons in STBstatus.ui
if 'PySide' in sys.modules.copy():
    from PySide import QtCore
    from PySide import QtGui
else:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

@BLACS_tab
class VISATab(DeviceTab):
    # Define the Status Byte labels with this dictionary structure
    status_byte_labels = {'bit 7':'bit 7 label', 
                          'bit 6':'bit 6 label',
                          'bit 5':'bit 5 label',
                          'bit 4':'bit 4 label',
                          'bit 3':'bit 3 label',
                          'bit 2':'bit 2 label',
                          'bit 1':'bit 1 label',
                          'bit 0':'bit 0 label'}
    
    def __init__(self,*args,**kwargs):
        '''You MUST override this class in order to define the device worker for any child devices.
        You then call this parent method to finish initialization.'''
        if not hasattr(self,'device_worker_class'):
            raise LabscriptError('BLACS worker not set for device: %s'% self)
        DeviceTab.__init__(self,*args,**kwargs)
    
    def initialise_GUI(self):
        '''Loads the standard STBstatus.ui widget and sets the worker defined in __init__'''
        # load the status_ui for the STB register
        self.status_ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)),'STBstatus.ui'))
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

    
    # This function gets the status,
    # and updates the front panel widgets!
    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True)  
    def status_monitor(self):
        # When called with a queue, this function writes to the queue
        # when the pulseblaster is waiting. This indicates the end of
        # an experimental run.
        self.status = yield(self.queue_work(self._primary_worker,'check_status'))

        for key in self.status_bits:
            if self.status[key]:
                icon = QtGui.QIcon(':/qtutils/fugue/tick')
            else:
                icon = QtGui.QIcon(':/qtutils/fugue/cross')
            pixmap = icon.pixmap(QtCore.QSize(16,16))
            self.bit_values_widgets[key].setPixmap(pixmap)
        
        
    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True,True)
    def send_clear(self,widget=None):
        value = self.status_ui.clear_button.isChecked()
        yield(self.queue_work(self._primary_worker,'clear',value))

import visa      
@BLACS_worker
class VISAWorker(Worker):   
    def init(self):
        '''Initializes basic worker and opens VISA connection to device.'''    
        self.VISA_name = self.address
        self.resourceMan = visa.ResourceManager()
        self.connection = self.resourceMan.open_resource(self.VISA_name)
        self.connection.timeout = 2000
    
    def check_remote_values(self):
        # over-ride this method if remote value check is supported
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
        # over-ride this method if remote programming supported
        # should return self.check_remote_values() to confirm program success
        return self.check_remote_values()
        
    def clear(self,value):
        '''Sends standard *CLR to clear registers of device.'''
        self.connection.clear()
        
    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        '''Stores various device handles for use in transition_to_manual method.'''
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
        '''Simple transition_to_manual method where no data is saved.'''         
        if abort:
            # If we're aborting the run, reset to original value
            self.program_manual(self.initial_values)
        # If we're not aborting the run, stick with buffered value. Nothing to do really!
        # return the current values in the device
        return True
        
    def shutdown(self):
        '''Closes VISA connection to device.'''
        self.connection.close()

