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
    
__version__ = '0.2.0'
__author__ = ['dihm']

##############################################
# define helper sub-classes of labscript defined channels

from labscript import Device, AnalogIn, StaticDDS, StaticAnalogQuantity, LabscriptError, set_passed_properties

class ScopeChannel(AnalogIn):
    """Labscript device that handles acquisition stuff.
    Connection should be in channels list."""
    description = 'Scope Acquisition Channel Class'
    def __init__(self, name, parent_device, connection):
        Device.__init__(self,name,parent_device,connection)
        self.acquisitions = []
        
    def acquire(self):
        if self.acquisitions:
            raise LabscriptError('Scope Channel {0:s}:{1:s} can only have one acquisition!'.format(self.parent_device.name,self.name))
        else:
            self.acquisitions.append({'label': self.name})
           
class CounterScopeChannel(ScopeChannel):
    """Labscript device that handles acquisition stuff.
    Also specifies if pulse counting on analog channel.
    counting assumes tuple with (type,polarity)"""
    description = 'Scope Acquisition Channel Class with Pulse Counting'
    def __init__(self, name, parent_device, connection):
        ScopeChannel.__init__(self,name,parent_device,connection)
        self.counts = []                       
        
    def count(self,typ,pol):
        # guess we can allow multiple types of counters per channel
        if (typ in ['pulse', 'edge']) and (pol in ['pos', 'neg']):
            self.counts.append({'type':typ,'polarity':pol})
        else:
            raise LabscriptError('Invalid counting parameters for {0:s}:{1:s}'.format(self.parent_name,self.name)) 

class StaticFreqAmp(StaticDDS):
    """A Static Frequency that supports frequency and amplitude control."""
    description = 'Frequency Source class for Signal Generators'
    allowed_children = [StaticAnalogQuantity]
    
    @set_passed_properties(property_names = {})    
    def __init__(self, name, parent_device, connection, freq_limits = (), freq_conv_class = None,freq_conv_params = {}, amp_limits = (), amp_conv_class = None, amp_conv_params = {}):
        """Frequency and amplitude limits should be respected to ensure device is not sent out of range."""
        Device.__init__(self,name,parent_device,connection)
        self.frequency = StaticAnalogQuantity(self.name+'_freq',self,'freq',freq_limits,freq_conv_class,freq_conv_params)
        self.frequency.default_value = freq_limits[0]
        self.amplitude = StaticAnalogQuantity(self.name+'_amp',self,'amp',amp_limits,amp_conv_class,amp_conv_params)
        self.amplitude.default_value = amp_limits[0]
        
    def setphase(self,value,units=None):
        raise LabscriptError('StaticFreqAmp does not support phase control')
            
    def enable(self):       
        """overridden from StaticDDS so as not to provide time resolution -
        output can be enabled or disabled only at the start of the shot"""
        raise LabscriptError('StaticFreqAmp {:s} does not support a digital gate'.format(self.name))
                            
    def disable(self):
        """overridden from StaticDDS so as not to provide time resolution -
        output can be enabled or disabled only at the start of the shot"""
        raise LabscriptError('StaticFreqAmp {:s} does not support a digital gate'.format(self.name))

