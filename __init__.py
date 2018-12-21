# basic init for naqslab_devices
# defines a version and uses labscript_devices __init__ for setup
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
    
__version__ = '0.0.2'




