Devices
=======

Directory of all device classes in this repository. 

The labscript primitive subclasses are derivatives of the labscript-provided children classes used by devices in this repository. 

There are two parent classes that are not directly used, but rather provide templates for creating new devices. First is the :doc:`VISA` class that templates communication with devices through the VISA communication protocol. This uses the :std:doc:`PyVISA python wrapper <pyvisa:index>`.

.. toctree::
	:maxdepth: 3
	
	primitives

	VISA
	SignalGenerator

	KeysightXSeries
	NovaTechDDS
	PulseBlasterESRPro300
	SR865
	TektronixTDS
