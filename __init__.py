# basic init for naqslab_devices
# defines a version and uses labscript_devices __init__ for setup
from __future__ import division, unicode_literals, print_function, absolute_import
from labscript_utils import PY2
if PY2:
    str = unicode
    
import labscript_devices
    
__version__ = '0.0.1'




