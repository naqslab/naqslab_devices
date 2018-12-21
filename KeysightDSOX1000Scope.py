#####################################################################
#                                                                   #
# /KeysightDSOX1000Scope.py                                         #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from naqslab_devices.VISA import VISAWorker
from naqslab_devices.TekScope import ScopeChannel
from naqslab_devices.KeysightMSOX3000Scope import KeysightMSOX3000Scope, KeysightMSOX3000ScopeTab, KeysightMSOX3000Worker
from labscript import LabscriptError

__version__ = '0.1.0'
__author__ = ['dihm']      
        
      
@labscript_device              
class KeysightDSOX1000Scope(KeysightMSOX3000Scope):
    description = 'Keysight DSO-X1000 Series Digital Oscilliscope'
    allowed_children = [ScopeChannel]
    
    def __init__(self, name, VISA_name, trigger_device, trigger_connection, 
        num_AI=2, DI=False, trigger_duration=1e-3, **kwargs):
        KeysightMSOX3000Scope.__init__(self,name,VISA_name,
        trigger_device,trigger_connection,
        num_AI,DI,trigger_duration,**kwargs)

@BLACS_tab
class KeysightDSOX1000ScopeTab(KeysightMSOX3000ScopeTab):
    
    def __init__(self,*args,**kwargs):
        self.device_worker_class = KeysightDSOX1000Worker
        KeysightMSOX3000ScopeTab.__init__(self,*args,**kwargs)
       
@BLACS_worker
class KeysightDSOX1000Worker(KeysightMSOX3000Worker):   
    
    model_ident = 'DSO-X 1'
    # Our DSO-X1102G does not like :DIG, so using :SING instead
    dig_command = ':SING'
