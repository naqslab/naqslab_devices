#####################################################################
#                                                                   #
# /naqslab_devices/BristolWavemeter/register_classes.py             #
#                                                                   #
# Copyright 2025, Jason Pruitt                                      #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
import labscript_devices

labscript_devices.register_classes(
    'BristolWavemeter',
    BLACS_tab='naqslab_devices.BristolWavemeter.blacs_tab.BristolWavemeterTab',
    runviewer_parser='')
