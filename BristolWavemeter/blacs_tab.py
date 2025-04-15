#####################################################################
#                                                                   #
# /naqslab_devices/BristolWavemeter/blacs_tab.py                    #
#                                                                   #
# Copyright 2025, Jason Pruitt                                      #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from blacs.device_base_class import DeviceTab

from blacs.tab_base_classes import define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED 
from qtutils import UiLoader
import os

# Imports for handling icons in STBstatus.ui
from qtutils.qt import QtCore
from qtutils.qt import QtGui

class BristolWavemeterTab(DeviceTab):
    status_widget = 'STBstatus.ui'
    STBui_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),status_widget)

    # Event Status Register (ESR) Labels
    status_byte_labels = {
                        'bit 7':'Power On', 
                        'bit 6':'unused',
                        'bit 5':'Command Error',
                        'bit 4':'Execution Error',
                        'bit 3':'Device Dependent Error',
                        'bit 2':'Query Error',
                        'bit 1':'unused',
                        'bit 0':'OPC'
                        }
    # instrument status bytes
    status_byte_labels = {
                        'bit 7':'unused', 
                        'bit 6':'unused',
                        'bit 5':'Bit exists in questionable register',
                        'bit 4':'unused',
                        'bit 3':'Errors in error queue',
                        'bit 2':'Bit exists in event status register',
                        'bit 1':'unused',
                        'bit 0':'unused'
                        }

    def __init__(self,*args,**kwargs):
        # set the worker
        self.device_worker_class = 'naqslab_devices.BristolWavemeter.blacs_worker.BristolWavemeterWorker'
        DeviceTab.__init__(self,*args,**kwargs)
    
    # stole this from VISA gui logic
    def initialise_GUI(self):
        self.status_ui = UiLoader().load(self.STBui_path)
        self.get_tab_layout().addWidget(self.status_ui)
        
        # generate the dictionaries
        self.status_bits = ['bit 0', 'bit 1', 'bit 2', 'bit 3', 'bit 4', 'bit 5', 'bit 6', 'bit 7']
        self.bit_labels_widgets = {}
        self.bit_values_widgets = {}
        self.status = {}
        for bit in self.status_bits:
            self.status[bit] = False
            self.bit_values_widgets[bit] = getattr(self.status_ui, 'status_{0:s}'.format(bit.split()[1]))
            self.bit_labels_widgets[bit] = getattr(self.status_ui, 'status_label_{0:s}'.format(bit.split()[1]))
        
        # Dynamically update status bits with correct names           
        for key in self.status_bits:
            self.bit_labels_widgets[key].setText(self.status_byte_labels[key])
        self.status_ui.clear_button.clicked.connect(self.send_clear)

        # Store the VISA name to be used
        self.address = str(self.settings['connection_table'].find_by_name(self.settings["device_name"]).BLACS_connection)
        
        # use AO widgets to mimick functionality
        analog_properties = {
            # 'frequency':{
            #     'base_unit':'Hz',
            #     'min':2.14285714e13, # freq -> 14,000 nm
            #     'max':8.57142857e14, # freq -> 350 nm
            #     'step':1e-3,
            #     'decimals':6
            #     },
            'wavelength':{
                'base_unit':'nm',
                'min':14000, # freq -> 14,000 nm
                'max':350, # freq -> 350 nm
                'step':1e-6,
                'decimals':6
                },
            }
      
        self.create_analog_outputs(analog_properties)
        ao_widgets = self.create_analog_widgets(analog_properties)
        self.auto_place_widgets(('wavelength',ao_widgets))
        
        # call VISATab.initialise to create BristolWavemeter widget
        DeviceTab.initialise_GUI(self)

        # # Set the capabilities of this device
        self.supports_remote_value_check(False)
        self.supports_smart_programming(True)
        # # self.statemachine_timeout_add(5000, self.status_monitor)   
                
        # add entries to worker kwargs
        # this allows inheritors to initialize with added entries for their own workers
        if not hasattr(self,'worker_init_kwargs'):
            self.worker_init_kwargs = {}
            
        self.worker_init_kwargs['address'] = self.address
        self.worker_init_kwargs['device_name'] = self.device_name

        # Create and set the primary worker
        self.create_worker("main_worker",
                            self.device_worker_class,
                            {'address':self.address,
                            })
        self.primary_worker = "main_worker"       

    # # TODO - I think we said to move away from this
    # # This function gets the status,
    # # and updates the front panel widgets!
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
