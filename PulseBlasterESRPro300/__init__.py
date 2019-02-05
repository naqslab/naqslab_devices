#####################################################################
#                                                                   #
# /naqslab_devices/PulseBlasterESRPro300/__init__.py                #
#                                                                   #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode

from labscript_devices import deprecated_import_alias


# For backwards compatibility with old experiment scripts:
PulseBlasterESRPro300 = deprecated_import_alias(
    "naqslab_devices.PulseBlasterESRPro300.labscript_device.PulseBlasterESRPro300")
