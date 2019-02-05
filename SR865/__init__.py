#####################################################################
#                                                                   #
# /naqslab_devices/SR865/__init__.py                                #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of naqslab_devices,                             #
# and is licensed under the                                         #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

from labscript_devices import deprecated_import_alias


# For backwards compatibility with old experiment scripts:
SR865 = deprecated_import_alias("naqslab_devices.SR865.labscript_device.SR865")
