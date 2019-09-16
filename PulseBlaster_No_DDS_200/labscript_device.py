#####################################################################
#                                                                   #
# /naqslab_devices/Pulseblaster_No_DDS_200/labscript_device.py      #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode 

from labscript_devices.PulseBlaster_No_DDS import PulseBlaster_No_DDS

class PulseBlaster_No_DDS_200(PulseBlaster_No_DDS):
    description = 'SpinCore PulseBlaster USB with 200 MHz clock'
    clock_limit = 17.2e6 # can probably go faster
    clock_resolution = 10e-9
    core_clock_freq = 200
    n_flags = 24
    
     
