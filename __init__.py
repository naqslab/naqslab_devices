#####################################################################
#                                                                   #
# /naqslab_devices/__init__.py                                      #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################

# basic init for naqslab_devices
# defines a version and author
# also confirms arbitrary subfolder support
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode
    
try:
    from labscript_utils import check_version
except ImportError:
    raise ImportError('Require labscript_utils > 2.1.0')
    
import labscript_devices
    
# require labscript_devices with arbitrary subfolder support
check_version('labscript_devices','2.2.0','3')
    
__version__ = '0.2.8'
__author__ = ['dihm']

##############################################
# define helper sub-classes of labscript defined channels

from labscript import Device, AnalogIn, StaticDDS, StaticAnalogQuantity, LabscriptError, set_passed_properties

class ScopeChannel(AnalogIn):
    """Subclass of labscript.AnalogIn that marks an acquiring scope channel.
    """
    description = 'Scope Acquisition Channel Class'
    def __init__(self, name, parent_device, connection):
        """This instantiates a scope channel to acquire during a buffered shot.
        
        Args:
            name (str): Name to assign channel
            parent_device (obj): Handle to parent device
            connection (str): Which physical scope channel is acquiring.
                              Generally of the form \'Channel n\' where n is
                              the channel label.
        """
        Device.__init__(self,name,parent_device,connection)
        self.acquisitions = []
        
    def acquire(self):
        """Inform BLACS to save data from this channel.
        
        Note that the parent_device controls when the acquisition trigger is sent.
        """
        if self.acquisitions:
            raise LabscriptError('Scope Channel {0:s}:{1:s} can only have one acquisition!'.format(self.parent_device.name,self.name))
        else:
            self.acquisitions.append({'label': self.name})
           
class CounterScopeChannel(ScopeChannel):
    """Subclass of :obj:`ScopeChannel` that allows for pulse counting."""
    description = 'Scope Acquisition Channel Class with Pulse Counting'
    def __init__(self, name, parent_device, connection):
        """This instantiates a counter scope channel to acquire during a buffered shot.
        
        Args:
            name (str): Name to assign channel
            parent_device (obj): Handle to parent device
            connection (str): Which physical scope channel is acquiring.
                              Generally of the form \'Channel n\' where n is
                              the channel label.
        """
        ScopeChannel.__init__(self,name,parent_device,connection)
        self.counts = []                       
        
    def count(self,typ,pol):
        """Register a pulse counter operation for this channel.
        
        Args:
            typ (str): count 'pulse' or 'edge' 
            pol (str): reference to 'pos' or 'neg' edges
        """
        # guess we can allow multiple types of counters per channel
        if (typ in ['pulse', 'edge']) and (pol in ['pos', 'neg']):
            self.counts.append({'type':typ,'polarity':pol})
        else:
            raise LabscriptError('Invalid counting parameters for {0:s}:{1:s}'.format(self.parent_name,self.name)) 

class StaticFreqAmp(StaticDDS):
    """A Static Frequency that supports frequency and amplitude control.
    
    If phase control is needed, use labscript.StaticDDS"""
    description = 'Frequency Source class for Signal Generators'
    allowed_children = [StaticAnalogQuantity]
       
    def __init__(self, name, parent_device, connection, freq_limits = None, freq_conv_class = None,freq_conv_params = {}, amp_limits = None, amp_conv_class = None, amp_conv_params = {}):
        """This instatiates a static frequency output channel.
        
        Frequency and amplitude limits set here will supercede those dictated 
        by the device class, but only when compiling a shot with runmanager. 
        Static update limits are enforced by the BLACS Tab for the parent device.
        
        Args:
            name (str): Name to assign output channel
            parent_device (obj): Handle to parent device
            connection (str): Which physical channel to use on parent device.
                              Typically only 'Channel 0' is available.
            freq_limits (tuple): Set (min,max) output frequencies in BLACS front panel units.
            freq_conv_class (obj): Custom conversion class to use
            freq_conv_params (dict): Parameters to conversion class
            amp_limits (tuple): Set (min,max) output amplitude in BLACS front panel units.
            amp_conv_class (obj): Custom convsersion class to use
            amp_conv_params (dict): Parameters to conversion class
        """
        Device.__init__(self,name,parent_device,connection)
        self.frequency = StaticAnalogQuantity(self.name+'_freq',self,'freq',freq_limits,freq_conv_class,freq_conv_params)
        self.amplitude = StaticAnalogQuantity(self.name+'_amp',self,'amp',amp_limits,amp_conv_class,amp_conv_params)
        # set default values within limits specified
        # if not specified, use limits from parent device
        if freq_limits is not None:
            self.frequency.default_value = freq_limits[0]
        else:
            self.frequency.default_value = parent_device.freq_limits[0]/parent_device.scale_factor
        if amp_limits is not None:
            self.amplitude.default_value = amp_limits[0]
        else:
            self.amplitude.default_value = parent_device.amp_limits[0]/parent_device.amp_scale_factor
        
    def setphase(self,value,units=None):
        """Overridden from StaticDDS so as not to provide phase control, which
        is generally not supported by :obj:`SignalGenerator` devices.
        """
        raise LabscriptError('StaticFreqAmp does not support phase control')
            
    def enable(self):       
        """overridden from StaticDDS so as not to provide time resolution -
        output can be enabled or disabled only at the start of the shot"""
        raise LabscriptError('StaticFreqAmp {:s} does not support a digital gate'.format(self.name))
                            
    def disable(self):
        """overridden from StaticDDS so as not to provide time resolution -
        output can be enabled or disabled only at the start of the shot"""
        raise LabscriptError('StaticFreqAmp {:s} does not support a digital gate'.format(self.name))

