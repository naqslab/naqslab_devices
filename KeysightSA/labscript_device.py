#####################################################################
#                                                                   #
# /naqslab_devices/KeysightSA/labscript_device.py                   #
#                                                                   #
# Copyright 2020, David Meyer                                       #
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

import numpy as np

from naqslab_devices import ScopeChannel, CounterScopeChannel
from labscript import Device, TriggerableDevice, config, LabscriptError, set_passed_properties

__version__ = '0.1.0'
__author__ = ['dihm']      
                      
class KeysightSA(TriggerableDevice):
    description = 'Keysight X Series Spectrum Analyzer'
    allowed_children = [ScopeChannel]
    
    @set_passed_properties(property_names = {
        "device_properties":["VISA_name",
                            "compression","compression_opts","shuffle"]}
        )
    def __init__(self, name, VISA_name, trigger_device, trigger_connection, 
        num_traces=6, trigger_duration=1e-3,
        compression=None, compression_opts=None, shuffle=False, **kwargs):
        '''VISA_name can be full VISA connection string or NI-MAX alias.
        Trigger Device should be fast clocked device. 
        num_traces gives number of individual traces we can acquire to, default is 6.
        trigger_duration sets trigger duration, default 1ms
        Compression of traces in h5 file controlled by:
        compression: \'lzf\', \'gzip\', None 
        compression_opts: 0-9 for gzip
        shuffle: True/False '''
        self.VISA_name = VISA_name
        self.BLACS_connection = VISA_name
        TriggerableDevice.__init__(self,name,trigger_device,trigger_connection,**kwargs)
        
        self.compression = compression
        if (compression == 'gzip') and (compression_opts == None):
            # set default compression level if needed
            self.compression_opts = 4
        else:
            self.compression_opts = compression_opts
        self.shuffle = shuffle
        
        self.trigger_duration = trigger_duration

        self.allowed_traces = ['Trace {0:d}'.format(i) for i in range(1,num_traces+1)]   
        
    def generate_code(self, hdf5_file):
        '''Automatically called by compiler to write acquisition instructions
        to h5 file. Configures acquisition parameters.'''    
        Device.generate_code(self, hdf5_file)
        
        acqs = {'SWEEP':[]}
        for trace in self.child_devices:
            if trace.acquisitions:
                # make sure channel is allowed
                if trace.connection in self.allowed_traces:
                    acqs['SWEEP'].append((trace.connection,trace.acquisitions[0]['label']))
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
                                
    def acquire(self,start_time):
        '''Call to define time when trigger will happen for scope.'''
        if not self.child_devices:
            raise LabscriptError('No channels acquiring for trigger {0:s}'.format(self.name))
        else:
            self.parent_device.trigger(start_time,self.trigger_duration)
            self.trigger_time = start_time
