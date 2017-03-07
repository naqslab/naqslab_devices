#####################################################################
#                                                                   #
# /PulseblasterESRpro500.py                                         #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_devices import labscript_device, BLACS_tab, BLACS_worker, runviewer_parser
from labscript_devices.PulseBlaster_No_DDS import PulseBlaster_No_DDS, Pulseblaster_No_DDS_Tab, PulseblasterNoDDSWorker, PulseBlaster_No_DDS_Parser

# note that ESR-Pro boards only have 21 channels
# bits 21-23 are short pulse control bits
# STATE        |  23 22 21
# OFF          |    000
# ONE_PERIOD   |    001
# TWO_PERIOD   |    010
# THREE_PERIOD |    011
# FOUR_PERIOD  |    100
# FIVE_PERIOD  |    101
# SIX_PERIOD   |    110  not defined in manual, defined in spinapi.h
# ON           |    111

@labscript_device
class PulseBlasterESRPro300(PulseBlaster_No_DDS):
    description = 'SpinCore PulseBlaster ESR-PRO-300'
    clock_limit = 30.0e6 # can probably go faster
    clock_resolution = 4e-9
    n_flags = 24


@BLACS_tab    
class pulseblasteresrpro300(Pulseblaster_No_DDS_Tab):
    # Capabilities
    num_DO = 24
    def __init__(self,*args,**kwargs):
        self.device_worker_class = PulseblasterESRPro300Worker 
        Pulseblaster_No_DDS_Tab.__init__(self,*args,**kwargs)
    
    
@BLACS_worker
class PulseblasterESRPro300Worker(PulseblasterNoDDSWorker):
    core_clock_freq = 300.0
    ESRPro = True
    
@runviewer_parser
class PulseBlasterESRPro300_Parser(PulseBlaster_No_DDS_Parser):
    num_DO = 24 # only 21 usable, flags 21-23 used for short pulses
    
     
