#####################################################################
#                                                                   #
# /naqslab_devices/SR865/blacs_tab.py                               #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from naqslab_devices.VISA.blacs_tab import VISATab

from blacs.tab_base_classes import define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED 

class SR865Tab(VISATab):
    # Capabilities

    status_byte_labels = {'bit 7':'Power On', 
                          'bit 6':'Button Pressed',
                          'bit 5':'Illegal Command',
                          'bit 4':'Execution Error',
                          'bit 3':'Query Queue Overflow',
                          'bit 2':'unused',
                          'bit 1':'Input Queue Overflow',
                          'bit 0':'OPC'}
    
    def __init__(self,*args,**kwargs):
        # set the worker
        self.device_worker_class = 'naqslab_devices.SR865.blacs_worker.SR865Worker'
        VISATab.__init__(self,*args,**kwargs)

    def initialise_GUI(self):
        self.connection_table_properties = (
            self.settings["connection_table"].find_by_name(self.device_name).properties
        )
        use_enums_option = self.connection_table_properties['use_enums_option']

        if use_enums_option == True:
            eo_prop = {
                'sens':{
                    'options':[1,500e-3,200e-3,100e-3,50e-3,20e-3,10e-3,5e-3,2e-3,1e-3,
                    500e-6,200e-6,100e-6,50e-6,20e-6,10e-6,5e-6,2e-6,1e-6,
                    500e-9,200e-9,100e-9,50e-9,20e-9,10e-9,5e-9,2e-9,1e-9], # uses default 0-indexing
                    'return_index':True, # widget will return integer index instead of string value when queried
                },
                'tau':{
                    'options':[1e-6,3e-6,10e-6,30e-6,100e-6,300e-6,
                        1e-3,3e-3,10e-3,30e-3,100e-3,300e-3,
                        1,3,10,30,100,300,1e3,3e3,10e3,30e3],
                    'return_index':True,
                },
            }
            self.create_enum_outputs(eo_prop)
            eo_widgets = self.auto_create_enum_widgets()

            self.auto_place_widgets(('Settings', eo_widgets))
            ao_prop = {
                        'phase':{'base_unit':'deg',
                                'min':-180,
                                'max':180,
                                'step':1,
                                'decimals':6}}
            self.create_analog_outputs(ao_prop)
            ao_widgets = self.create_analog_widgets(ao_prop)
            self.auto_place_widgets(('Settings',ao_widgets))

        else:
            # use AO widgets to mimick functionality
            ao_prop = {'tau':{'base_unit':'s',
                            'min':1e-6,
                            'max':30e3,
                            'step':1,
                            'decimals':6},
                        'sens':{'base_unit':'V',
                                'min':1e-9,
                                'max':1,
                                'step':1e-3,
                                'decimals':9},
                        'phase':{'base_unit':'deg',
                                'min':-180,
                                'max':180,
                                'step':1,
                                'decimals':6}}
                                
            self.create_analog_outputs(ao_prop)
            ao_widgets = self.create_analog_widgets(ao_prop)
            self.auto_place_widgets(('Settings',ao_widgets))
        
        # call VISATab.initialise to create SR865 widget
        VISATab.initialise_GUI(self)

        # Set the capabilities of this device
        self.supports_remote_value_check(True)
        self.supports_smart_programming(True) 
        self.statemachine_timeout_add(5000, self.status_monitor)   
        
    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True,True)
    def tau_changed(self,widget=None):
        value = self.status_ui.tau_comboBox.currentIndex()
        new_value = yield(self.queue_work(self._primary_worker,'set_tau',value))
        
        # only update if value is different
        if new_value != value:
            # block signals for update
            self.status_ui.tau_comboBox.blockSignals(True)
            self.status_ui.tau_comboBox.setCurrentIndex(new_value)
            self.status_ui.tau_comboBox.blockSignals(False)
        
    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True,True)
    def sens_changed(self,widget=None):
        value = self.status_ui.sens_comboBox.currentIndex()
        new_value = yield(self.queue_work(self._primary_worker,'set_sens',value))
        
        # only update if value is different
        if new_value != value:
            # block signals for update
            self.status_ui.tau_comboBox.blockSignals(True)
            self.status_ui.tau_comboBox.setCurrentIndex(new_value)
            self.status_ui.tau_comboBox.blockSignals(False)

