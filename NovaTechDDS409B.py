#####################################################################
#                                                                   #
# /NovaTechDDS409B.py                                               #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode
    
from labscript_devices import runviewer_parser, labscript_device, BLACS_tab, BLACS_worker

from labscript import StaticDDS, Device, config, LabscriptError, set_passed_properties

from naqslab_devices.NovaTechDDS409B_AC import *

import numpy as np
import labscript_utils.h5_lock, h5py
import labscript_utils.properties
        
@labscript_device
class NovaTechDDS409B(NovaTechDDS409B_AC):
    description = 'NT-DDS409B'
    allowed_children = [StaticDDS]
    clock_limit = 1
    # this is not a triggerable device

    def __init__(self, name,
                 com_port = "", baud_rate=19200, **kwargs):

        Device.__init__(self, name, None, com_port, **kwargs)
        self.BLACS_connection = '{:s},{:s}'.format(com_port, str(baud_rate))                   
        
    def generate_code(self, hdf5_file):
        DDSs = {}
        for output in self.child_devices:
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError('{:s} {:s} has invalid connection string: \'{:s}\'. '.format(output.description,output.name,str(output.connection)) + 
                                     'Format must be \'channel n\' with n from 0 to 3.')
            DDSs[channel] = output
            
        if not DDSs:
            # if no channels are being used, no need to continue
            return
            
        for connection in DDSs:
            if connection in range(4):
                # Static DDS
                dds = DDSs[connection]   
                dds.frequency.raw_output, dds.frequency.scale_factor = self.quantise_freq(dds.frequency.static_value, dds)
                dds.phase.raw_output, dds.phase.scale_factor = self.quantise_phase(dds.phase.static_value, dds)
                dds.amplitude.raw_output, dds.amplitude.scale_factor = self.quantise_amp(dds.amplitude.static_value, dds)
            else:
                raise LabscriptError('{:s} {:s} has invalid connection string: \'{:s}\'. '.format(dds.description,dds.name,str(dds.connection)) + 
                                     'Format must be \'channel n\' with n from 0 to 3.')
                 
        static_dtypes = {'names':['freq{:d}'.format(i) for i in DDSs] +
                            ['amp{:d}'.format(i) for i in DDSs] +
                            ['phase{:d}'.format(i) for i in DDSs],
                            'formats':[np.uint32 for i in DDSs] +
                            [np.uint16 for i in DDSs] + 
                            [np.uint16 for i in DDSs]}  
        
        static_table = np.zeros(1, dtype=static_dtypes)            
        
        for connection in DDSs:
            dds = DDSs[connection]
            static_table['freq{:d}'.format(connection)] = dds.frequency.raw_output
            static_table['amp{:d}'.format(connection)] = dds.amplitude.raw_output
            static_table['phase{:d}'.format(connection)] = dds.phase.raw_output

        grp = self.init_device_group(hdf5_file)
        grp.create_dataset('STATIC_DATA',compression=config.compression,data=static_table) 
        self.set_property('frequency_scale_factor', dds.frequency.scale_factor, location='device_properties')
        self.set_property('amplitude_scale_factor', dds.amplitude.scale_factor, location='device_properties')
        self.set_property('phase_scale_factor', dds.phase.scale_factor, location='device_properties') 

@BLACS_tab
class NovaTechDDS409BTab(NovaTechDDS409B_ACTab):
    
    def __init__(self,*args,**kwargs):
        self.device_worker_class = NovaTechDDS409BWorker
        NovaTechDDS409B_ACTab.__init__(self,*args,**kwargs)


@BLACS_worker        
class NovaTechDDS409BWorker(NovaTechDDS409B_ACWorker):
    
    def transition_to_manual(self,abort = False):
        if abort:
            # If we're aborting the run, then we need to reset DDSs to their initial values.
            # We also need to invalidate the smart programming cache for them.
            self.smart_cache['STATIC_DATA'] = None
            for channel in self.initial_values:
                ddsnum = int(channel.split(' ')[-1])
                for subchnl in ['freq','amp','phase']:
                    self.program_static(ddsnum,subchnl,self.initial_values[channel][subchnl]*self.conv[subchnl])
        else:
            # if not aborting, final values already set so do nothing
            pass
        # return True to indicate we successfully transitioned back to manual mode
        return True
        
        
      
@runviewer_parser
class NovaTechDDS409BParser(NovaTechDDS409B_ACParser):    
    def __init__(self, path, device):
        NovaTechDDS409B_ACParser.__init__(self,path,device)
        self.dyn_chan = []
        self.static_chan = [0,1,2,3]
            
 
