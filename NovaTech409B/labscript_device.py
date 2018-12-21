#####################################################################
#                                                                   #
# /naqslab_devices/NovaTech409B/labscript_device.py                 #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of naqslab_devices,                             #
# and is licensed under the                                         #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
# Source borrows heavily from labscript_devices/NovaTechDDS9m       #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

from labscript import IntermediateDevice, DDS, StaticDDS, Device, config, LabscriptError, set_passed_properties
from labscript_utils.unitconversions import NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion

import numpy as np
import labscript_utils.h5_lock, h5py


class NovaTech409B_AC(IntermediateDevice):
    description = 'NT-DDS409B-AC'
    allowed_children = [DDS, StaticDDS]
    clock_limit = 9990 # This is a realistic estimate of the max clock rate 
    # (100us for TS/pin10 processing to load next value into buffer and 
    # 100ns pipeline delay on pin 14 edge to update output values)

    @set_passed_properties(
        property_names = {'connection_table_properties': ['update_mode',
                                    'synchronous_first_line_repeat']}
        )
    def __init__(self, name, parent_device, 
                 com_port = "", baud_rate=19200, 
                 update_mode='synchronous', synchronous_first_line_repeat=False, 
                 **kwargs):
        '''Labscript device class for NovaTech 409B-AC variant DDS.
        This device has two dynamic channels (0,1) and two static channels (2,3).'''

        IntermediateDevice.__init__(self, name, parent_device, **kwargs)
        self.BLACS_connection = '%s,%s' % (com_port, str(baud_rate))
        if not update_mode in ['synchronous', 'asynchronous']:
            raise LabscriptError('update_mode must be \'synchronous\' or \'asynchronous\'')            
        
        self.update_mode = update_mode
        self.synchronous_first_line_repeat = synchronous_first_line_repeat        
        
    def add_device(self, device):
        Device.add_device(self, device)
        # The Novatech doesn't support 0Hz output; set the default frequency of the DDS to 0.1 Hz:
        device.frequency.default_value = 0.1
            
    def get_default_unit_conversion_classes(self, device):
        """Child devices call this during their __init__ (with themselves
        as the argument) to check if there are certain unit calibration
        classes that they should apply to their outputs, if the user has
        not otherwise specified a calibration class"""
        if device.connection in ['channel 0', 'channel 1', 'channel 2', 'channel 3']:
            # Default calibration classes for the non-static channels:
            return NovaTechDDS9mFreqConversion, NovaTechDDS9mAmpConversion, None
        else:
            return None, None, None
        
        
    def quantise_freq(self, data, device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # Ensure that frequencies are within bounds:
        if np.any(data > 171.1276031e6 )  or np.any(data < 0.1 ):
            raise LabscriptError('%s %s ' % (device.description, device.name) +
                              'can only have frequencies between 0.1Hz and 171MHz, ' + 
                              'the limit imposed by %s.' % self.name)
        # It's faster to add 0.5 then typecast than to round to integers first:
        data = np.array((10*data)+0.5,dtype=np.uint32)
        scale_factor = 10
        return data, scale_factor
        
    def quantise_phase(self, data, device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # ensure that phase wraps around:
        data %= 360
        # It's faster to add 0.5 then typecast than to round to integers first:
        scale_factor = 16384/360.0
        data = np.array((scale_factor*data)+0.5,dtype=np.uint16)
        return data, scale_factor
        
    def quantise_amp(self,data,device):
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        # ensure that amplitudes are within bounds:
        if np.any(data > 1 )  or np.any(data < 0):
            raise LabscriptError('%s %s ' % (device.description, device.name) +
                              'can only have amplitudes between 0 and 1 (Volts peak to peak approx), ' + 
                              'the limit imposed by %s.' % self.name)
        # It's faster to add 0.5 then typecast than to round to integers first:
        data = np.array((1023*data)+0.5,dtype=np.uint16)
        scale_factor = 1023
        return data, scale_factor
        
    def generate_code(self, hdf5_file):
        DDSs = {}
        for output in self.child_devices:
            # Check that the instructions will fit into RAM:
            if isinstance(output, DDS) and len(output.frequency.raw_output) > 16384 - 2: # -2 to include space for dummy instructions
                raise LabscriptError('%s can only support 16383 instructions. ' % self.name +
                                     'Please decrease the sample rates of devices on the same clock, ' + 
                                     'or connect %s to a different pseudoclock.' % self.name)
            try:
                prefix, channel = output.connection.split()
                channel = int(channel)
            except:
                raise LabscriptError('%s %s has invalid connection string: \'%s\'. ' % (output.description,output.name,str(output.connection)) + 
                                     'Format must be \'channel n\' with n from 0 to 4.')
            DDSs[channel] = output
            
        if not DDSs:
            # if no channels are being used, no need to continue
            return            

        for connection in DDSs:
            if connection in range(4):
                dds = DDSs[connection]   
                dds.frequency.raw_output, dds.frequency.scale_factor = self.quantise_freq(dds.frequency.raw_output, dds)
                dds.phase.raw_output, dds.phase.scale_factor = self.quantise_phase(dds.phase.raw_output, dds)
                dds.amplitude.raw_output, dds.amplitude.scale_factor = self.quantise_amp(dds.amplitude.raw_output, dds)
            else:
                raise LabscriptError('%s %s has invalid connection string: \'%s\'. ' % (dds.description,dds.name,str(dds.connection)) + 
                                     'Format must be \'channel n\' with n from 0 to 4.')
        
        # determine what types of channels are needed
        stat_DDSs = set(DDSs)&set(range(2,4)) 
        if set(DDSs)&set(range(2)):
            dyn_DDSs = range(2)
        else:
            dyn_DDSs = []
        
        if dyn_DDSs:
            # only do dynamic channels if needed    
            dtypes = {'names':['freq%d' % i for i in dyn_DDSs] +
                                ['amp%d' % i for i in dyn_DDSs] +
                                ['phase%d' % i for i in dyn_DDSs],
                                'formats':[np.uint32 for i in dyn_DDSs] +
                                [np.uint16 for i in dyn_DDSs] + 
                                [np.uint16 for i in dyn_DDSs]}  
             
            clockline = self.parent_clock_line
            pseudoclock = clockline.parent_device
            times = pseudoclock.times[clockline]
           
            out_table = np.zeros(len(times),dtype=dtypes)
            out_table['freq0'].fill(1)
            out_table['freq1'].fill(1)
            
            for connection in range(2):
                if not connection in DDSs:
                    continue
                dds = DDSs[connection]
                # The last two instructions are left blank, for BLACS
                # to fill in at program time.
                out_table['freq%d' % connection][:] = dds.frequency.raw_output
                out_table['amp%d' % connection][:] = dds.amplitude.raw_output
                out_table['phase%d' % connection][:] = dds.phase.raw_output
                
            if self.update_mode == 'asynchronous' or self.synchronous_first_line_repeat:
                # Duplicate the first line of the table. Otherwise, we are one step
                # ahead in the table from the start of a run. In asynchronous
                # updating mode, this is necessary since the first line of the
                # table is already being output before the first trigger from
                # the master clock. When using a simple delay line for synchronous
                # output, this also seems to be required, in which case
                # synchronous_first_line_repeat should be set to True.
                # However, when a tristate driver is used as described at
                # http://labscriptsuite.org/blog/implementation-of-the-novatech-dds9m/
                # then is is not neccesary to duplicate the first line. Use of a
                # tristate driver in this way is the correct way to use
                # the novatech DDS, as per its instruction manual, and so is likely
                # to be the most reliable. However, through trial and error we've
                # determined that duplicating the first line like this gives correct
                # output in asynchronous mode and in synchronous mode when using a
                # simple delay line, at least for the specific device we tested.
                # Your milage may vary.
                out_table = np.concatenate([out_table[0:1], out_table])
            
        if stat_DDSs:
            # only do static channels if needed
            static_dtypes = {'names':['freq%d' % i for i in stat_DDSs] +
                                ['amp%d' % i for i in stat_DDSs] +
                                ['phase%d' % i for i in stat_DDSs],
                                'formats':[np.uint32 for i in stat_DDSs] +
                                [np.uint16 for i in stat_DDSs] + 
                                [np.uint16 for i in stat_DDSs]}            
            
            static_table = np.zeros(1, dtype=static_dtypes)
                
            for connection in range(2,4):
                if not connection in DDSs:
                    continue
                dds = DDSs[connection]
                static_table['freq%d' % connection] = dds.frequency.raw_output[0]
                static_table['amp%d' % connection] = dds.amplitude.raw_output[0]
                static_table['phase%d' % connection] = dds.phase.raw_output[0]
            
        # write out data tables
        grp = self.init_device_group(hdf5_file)
        if dyn_DDSs:
            grp.create_dataset('TABLE_DATA',compression=config.compression,data=out_table) 
        if stat_DDSs: 
            grp.create_dataset('STATIC_DATA',compression=config.compression,data=static_table) 
        self.set_property('frequency_scale_factor', dds.frequency.scale_factor, location='device_properties')
        self.set_property('amplitude_scale_factor', dds.amplitude.scale_factor, location='device_properties')
        self.set_property('phase_scale_factor', dds.phase.scale_factor, location='device_properties')


class NovaTech409B(NovaTech409B_AC):
    description = 'NT-DDS409B'
    allowed_children = [StaticDDS]
    clock_limit = 1
    # this is not a triggerable device

    def __init__(self, name,
                 com_port = "", baud_rate=19200, **kwargs):
        '''Labscript class for NovaTech 409B DDS.
        This device has four static DDS output channels.'''

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
