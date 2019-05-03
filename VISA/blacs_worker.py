#####################################################################
#                                                                   #
# /naqslab_devices/VISA/blacs_worker.py                             #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2,dedent
if PY2:
    str = unicode

from blacs.tab_base_classes import Worker

from labscript import LabscriptError

import visa      

class VISAWorker(Worker):   
    def init(self):
        '''Initializes basic worker and opens VISA connection to device.'''    
        self.VISA_name = self.address
        self.resourceMan = visa.ResourceManager()
        try:
            self.connection = self.resourceMan.open_resource(self.VISA_name)
        except visa.VisaIOError:
            msg = '''{:s} not found! Is it connected?'''.format(self.VISA_name)
            if PY2:
                raise LabscriptError(dedent(msg))
            else:
                # in PY3, suppress the full visa error for a simpler one
                raise LabscriptError(dedent(msg)) from None
        self.connection.timeout = 2000
    
    def check_remote_values(self):
        # over-ride this method if remote value check is supported
        return None
    
    def convert_register(self,register):
        '''Converts register value to dict of bools'''
        results = {}
        #get the status and convert to binary, and take off the '0b' header:
        status = bin(register)[2:]
        # if the status is less than 8 bits long, pad the start with zeros!
        while len(status)<8:
            status = '0'+status
        # reverse the status string so bit 0 is first indexed
        status = status[::-1]
        # fill the status byte dictionary
        for i in range(0,8):
            results['bit '+str(i)] = bool(int(status[i]))
        
        return results
    
    def check_status(self):
        '''Reads the Status Byte Register of the VISA device.
        Returns dictionary of bit values.'''
        results = {}
        stb = self.connection.read_stb()
        
        return self.convert_register(stb)
    
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

