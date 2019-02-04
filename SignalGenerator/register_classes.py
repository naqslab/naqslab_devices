#####################################################################
#                                                                   #
# /naqslab_devices/SignalGenerator/register_classes.py              #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of naqslab_devices,                             #
# and is licensed under the                                         #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import labscript_devices

labscript_devices.register_classes(
    'RS_SMF100A',
    BLACS_tab='naqslab_devices.SignalGenerator.BLACS.RS_SMF100A.RS_SMF100ATab',
    runviewer_parser='')

labscript_devices.register_classes(
    'RS_SMHU',
    BLACS_tab='naqslab_devices.SignalGenerator.BLACS.RS_SMHU.RS_SMHUTab',
    runviewer_parser='')
    
labscript_devices.register_classes(
    'HP8643A',
    BLACS_tab='naqslab_devices.SignalGenerator.BLACS.HP8643A.HP8643ATab',
    runviewer_parser='')
    
labscript_devices.register_classes(
    'HP8642A',
    BLACS_tab='naqslab_devices.SignalGenerator.BLACS.HP8642A.HP8642ATab',
    runviewer_parser='')
