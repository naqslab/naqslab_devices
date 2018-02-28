# README #

This repository contains various 3rd-party device implementations for use with the [labscript suite](https://bitbucket.org/labscript_suite) experiment control system.

### How do I get set up? ###

Clone this repository into the labscript suite directory. Invoke in labscript scripts like other labscript\_devices
```python
from naqslab_devices.TekScope import TekScope, ScopeChannel
```

As of now BLACS will only look in the labscript\_devices repository for device classes. 
A quick workaround for this until a more permanant solution is implemented is this diff applied to \_\_init\_\_.py in labscript\_devices

```diff
@@ -11,6 +11,8 @@
 check_version('labscript', '2.1', '3')
 check_version('blacs', '2.1', '3')
 
+lab_repo = 'naqslab_devices'
+
 
 class ClassRegister(object):
     """A register for looking up classes by module name.  Provides a
@@ -49,6 +51,11 @@
             importlib.import_module('.' + name, __name__)
             print 'imported', name, 'ok!'
         except ImportError:
-            sys.stderr.write('Error importing module %s.%s whilst looking for classes for device %s. '%(__name__, name, name) +
+            # next try looking in the lab's device folder
+            try:
+                importlib.import_module('.' + name, lab_repo)
+            
+            except ImportError:
+                sys.stderr.write('Error importing module %s.%s whilst looking for classes for device %s. '%(__name__, name, name) +
                              'Check that the module exists, is named correctly, and can be imported with no errors. ' +
                              'Full traceback follows:\n')
@@ -53,6 +60,6 @@
                              'Check that the module exists, is named correctly, and can be imported with no errors. ' +
                              'Full traceback follows:\n')
-            raise
+                raise
         # Class definitions in that module have executed now, check to see if class is in our register:
         try:
             return self.registered_classes[name]

```

Usage of individual devices varies somewhat. Here is an example connectiontable showing some of their instantiation
```python
from labscript import *
from naqslab_devices.PulseBlasterESRPro300 import PulseBlasterESRPro300
from naqslab_devices.NovaTechDDS409B import NovaTechDDS409B
from naqslab_devices.NovaTechDDS409B_AC import NovaTechDDS409B_AC
from labscript_devices.NI_DAQmx import NI_DAQmx
from naqslab_devices.SignalGenerator import StaticFreqAmp
from naqslab_devices.RS_SMHU import RS_SMHU
from naqslab_devices.RS_SMF100A import RS_SMF100A
from naqslab_devices.SR865 import SR865
from naqslab_devices.TekScope import TekScope, ScopeChannel
from labscript_devices.Camera import Camera

PulseBlasterESRPro300(name='pulseblaster_0', board_number=0, programming_scheme='pb_start/BRANCH')
ClockLine(name='pulseblaster_0_clockline_fast', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 0')
ClockLine(name='pulseblaster_0_clockline_slow', pseudoclock=pulseblaster_0.pseudoclock, connection='flag 1')
	    
NI_DAQmx(name='ni_6343', parent_device=pulseblaster_0_clockline_fast, clock_terminal='/ni_usb_6343/PFI0',
	    MAX_name='ni_usb_6343',
	    num_AO = 4,
	    sample_rate_AO = 700e3,
	    num_DO = 32,
	    sample_rate_DO = 1e6,
	    num_AI = 32,
	    clock_terminal_AI = '/ni_usb_6343/PFI0',
	    mode_AI = 'labscript',
	    sample_rate_AI = 250e3, # 500 kS/s max aggregate
	    num_PFI=16,
	    DAQmx_waits_counter_bug_workaround=False)

NovaTechDDS409B(name='novatech_static', com_port="com4", baud_rate = 115200)
NovaTechDDS409B_AC(name='novatech', parent_device=pulseblaster_0_clockline_slow, com_port="com3", update_mode='asynchronous', baud_rate = 115200)

# using NI-MAX alias instead of full VISA name
RS_SMHU(name='SMHU',VISA_name='SMHU58')
RS_SMF100A(name='SMF100A', VISA_name='SMF100A')

# add Lock-In Amplifier
SR865(name='LockIn', VISA_name='SR865')

# call the scope, use NI-MAX alias instead of full name
TekScope(name='Scope',VISA_name='TDS2014B',
	trigger_device=pulseblaster_0.direct_outputs,trigger_connection='flag 3')
ScopeChannel('LockInX',Scope,'Channel 1')
ScopeChannel('LockInY',Scope,'Channel 2')
ScopeChannel('PSK_Scope',Scope,'Channel 3')

# Define Cameras
# note that Basler cameras can overlap frames if 
# second exposure does not end before frame transfer of first finishes
Camera('CCD_1',parent_device=pulseblaster_0.direct_outputs,connection='flag 6',
		serial_number=21646180,effective_pixel_size=3.75E-6,
		exposure_time=100E-6,BIAS_port=1027,
		minimum_recovery_time=31.635E-3,orientation='side')
# 31.635ms is full sensor readout time for Basler acA1300-30um

# Define the Wait Monitor for the AC-Line Triggering
# note that connections used here cannot be used elsewhere
# 'connection' needs to be physically connected to 'acquisition_connection'
# for M-Series DAQs, ctr0 gate is on PFI9
WaitMonitor(name='wait_monitor', parent_device=ni_6343, connection='port0/line0', acquisition_device=ni_6343, acquisition_connection='ctr0', timeout_device=ni_6343, timeout_connection='PFI1')

DigitalOut( 'AC_trigger_arm', pulseblaster_0.direct_outputs, 'flag 2')

# define the PB digital outputs
DigitalOut( 'probe_AOM', pulseblaster_0.direct_outputs, 'flag 4')
DigitalOut( 'blue_AOM', pulseblaster_0.direct_outputs, 'flag 5')
#DigitalOut( 'PB_6', pulseblaster_0.direct_outputs, 'flag 6')
DigitalOut( 'PB_7', pulseblaster_0.direct_outputs, 'flag 7')
DigitalOut( 'PB_8', pulseblaster_0.direct_outputs, 'flag 8')
DigitalOut( 'PB_9', pulseblaster_0.direct_outputs, 'flag 9')
DigitalOut( 'PB_10', pulseblaster_0.direct_outputs, 'flag 10')
DigitalOut( 'PB_11', pulseblaster_0.direct_outputs, 'flag 11')
DigitalOut( 'PB_12', pulseblaster_0.direct_outputs, 'flag 12')
DigitalOut( 'PB_13', pulseblaster_0.direct_outputs, 'flag 13')
DigitalOut( 'PB_14', pulseblaster_0.direct_outputs, 'flag 14')
DigitalOut( 'PB_15', pulseblaster_0.direct_outputs, 'flag 15')
DigitalOut( 'PB_16', pulseblaster_0.direct_outputs, 'flag 16')
DigitalOut( 'PB_17', pulseblaster_0.direct_outputs, 'flag 17')
DigitalOut( 'PB_18', pulseblaster_0.direct_outputs, 'flag 18')
DigitalOut( 'PB_19', pulseblaster_0.direct_outputs, 'flag 19')
DigitalOut( 'PB_20', pulseblaster_0.direct_outputs, 'flag 20')

# short pulse control channels
DigitalOut(  'bit21', pulseblaster_0.direct_outputs, 'flag 21')
DigitalOut(  'bit22', pulseblaster_0.direct_outputs, 'flag 22')
DigitalOut(  'bit23', pulseblaster_0.direct_outputs, 'flag 23')

AnalogOut( 'ProbeAmpLock', ni_6343, 'ao0')
AnalogOut( 'PSK', ni_6343, 'ao1')
AnalogOut( 'ni_6343_ao2', ni_6343, 'ao2')
AnalogOut( 'ni_6343_ao3', ni_6343, 'ao3')

AnalogIn( 'LockIn_X', ni_6343, 'ai0')
AnalogIn( 'LockIn_Y', ni_6343, 'ai1')
AnalogIn( 'PSK_Phase', ni_6343, 'ai2')
AnalogIn( 'AI3', ni_6343, 'ai3')

# this dummy line necessary to balance the digital out for the wait monitor
DigitalOut( 'P0_1', ni_6343, 'port0/line1')

StaticDDS( 'blueAOM', novatech_static, 'channel 0')
StaticDDS( 'ProbeBeatNote', novatech_static, 'channel 1')
StaticDDS( 'ProbeAOM', novatech_static, 'channel 2')
StaticDDS( 'static3', novatech_static, 'channel 3')

DDS( 'dds0', novatech, 'channel 0')
DDS( 'dds1', novatech, 'channel 1')
StaticDDS( 'dds2', novatech, 'channel 2')
StaticDDS( 'dds3', novatech, 'channel 3')

StaticFreqAmp( 'blueEOM', SMHU, 'channel 0', freq_limits=(0.1,4320), amp_limits=(-140,13))
StaticFreqAmp( 'uWaves', SMF100A, 'channel 0', freq_limits=(100e-6,22), amp_limits=(-26,18))

start()

stop(1)
```

### Contribution guidelines ###

* Submitted code should follow labscript\_suite style and guidelines
* Submitted code should also be backwards compatible where possible
