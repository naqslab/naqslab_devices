#####################################################################
#                                                                   #
# /naqslab_devices/VISA/labscript_device.py                         #
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

from labscript import Device, LabscriptError, set_passed_properties

__version__ = '0.1.1'
__author__ = ['dihm']
                  
class VISA(Device):
    description = 'VISA Compatible Instrument'
    allowed_children = []
    
    @set_passed_properties(property_names = {
        "device_properties":["VISA_name"]}
        )
    def __init__(self, name, parent_device, VISA_name, **kwargs):
        '''VISA_name can be full VISA connection string or NI-MAX alias.
        Trigger Device should be fast clocked device. '''
        self.VISA_name = VISA_name
        self.BLACS_connection = VISA_name
        Device.__init__(self, name, parent_device, VISA_name)
        
    def generate_code(self, hdf5_file):
        # over-ride this method for child classes
        # it should not return anything
        raise LabscriptError('generate_code() must be overridden for {0:s}'.format(self.name))

