#####################################################################
#                                                                   #
# /KeysightDSOX1000.py                                              #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

import numpy as np
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from naqslab_devices.TekScope import ScopeChannel
from naqslab_devices.KeysightMSOX3000Scope import KeysightMSOX3000Scope, KeysightMSOX3000ScopeTab, KeysightMSOX3000Worker
from labscript import LabscriptError      
        
      
@labscript_device              
class KeysightDSOX1000Scope(KeysightMSOX3000Scope):
    description = 'Keysight DSO-X1000 Series Digital Oscilliscope'
    allowed_children = [ScopeChannel]
    allowed_analog_chan = ['Channel {0:d}'.format(i) for i in range(1,5)]
    allowed_pod1_chan = []
    allowed_pod2_chan = []
    trigger_duration = 1e-3

@BLACS_tab
class KeysightDSOX1000ScopeTab(KeysightMSOX3000ScopeTab):
    
    def __init__(self,*args,**kwargs):
        self.device_worker_class = KeysightDSOX1000Worker
        KeysightMSOX3000ScopeTab.__init__(self,*args,**kwargs)
       
@BLACS_worker
class KeysightDSOX1000Worker(KeysightMSOX3000Worker):   
    
    model_ident = 'DSO-X 1'
        
    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        '''This only configures counters, if any are defined'''
        VISAWorker.transition_to_buffered(self,device_name,h5file,initial_values,fresh)
        
        # DSOX1000 series scopes do not have counters, skip to save h5 lookup
        
        if send_trigger:            
            # put scope into single mode
            # necessary since :WAV:DATA? clears data and wait for fresh data
            # when in continuous run mode
            self.connection.write(':DIG')
        
        return self.final_values

