#####################################################################
#                                                                   #
# /naqslab_devices/Pulseblaster_No_DDS_200/runviewer_parser.py      #
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

from labscript_devices.PulseBlaster_No_DDS import PulseBlaster_No_DDS_Parser

class PulseBlaster_No_DDS_200_Parser(PulseBlaster_No_DDS_Parser):
    num_flags = 24 
