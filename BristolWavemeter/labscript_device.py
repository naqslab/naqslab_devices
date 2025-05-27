#####################################################################
#                                                                   #
# /naqslab_devices/BristolWavemeter/labscript_device.py             #
#                                                                   #
# Copyright 2025, Jason Pruitt                                      #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
import numpy as np

# from naqslab_devices.VISA.labscript_device import VISA
from labscript import Device, StaticAnalogOut, config, LabscriptError, set_passed_properties
# from labscript_utils.unitconversions import UnitConversionBase
from labscript_utils.unitconversions.UnitConversionBase import UnitConversion

__version__ = '0.1.0'
__author__ = ['Json-To-String']

class BristolWavemeterConversion(UnitConversion):
    """
    Conversion class to ensure the setpoints are sent as nm.
    This is used in the instantiation of the backend StaticAnalogOut device. 
    """

    # This must be defined outside of init, and must match the default hardware unit specified within the BLACS tab
    base_unit = 'nm'

    def __init__(self, calibration_parameters = None):
        self.parameters = calibration_parameters
        if hasattr(self, 'derived_units'):
            self.derived_units += ['Hz', 'kHz', 'MHz', 'GHz', 'THz']
        else:
            self.derived_units = ['Hz', 'kHz', 'MHz', 'GHz', 'THz']
        UnitConversion.__init__(self, self.parameters)
    
    # Could reuse this for DRY
    def Hz_to_base(self, Hz):
        nm = 3e8 / Hz
        return nm
    
    def Hz_from_base(self, nm):
        Hz = 3e8 / nm
        return Hz
    
    def kHz_to_base(self, kHz):
        Hz = kHz * 1e3
        nm = 3e8 / Hz
        return nm

    def kHz_from_base(self, nm):
        Hz = 3e8 / nm
        kHz = Hz * 1e-3
        return kHz

    def MHz_to_base(self, MHz):
        Hz = MHz * 1e6
        nm = 3e8 / Hz
        return nm

    def MHz_from_base(self, nm):
        Hz = 3e8 / nm
        MHz = Hz * 1e-6
        return MHz

    def GHz_to_base(self, GHz):
        Hz = GHz * 1e9
        nm = 3e8 / Hz
        return nm

    def GHz_from_base(self, nm):
        Hz = 3e8 / nm
        GHz = Hz * 1e-9
        return GHz
    
    def THz_to_base(self, THz):
        Hz = THz * 1e12
        nm = 3e8 / Hz
        return nm

    def THz_from_base(self, nm):
        Hz = 3e8 / nm
        THz = Hz * 1e-12
        return THz
    
class BristolWavemeter(Device):
    """
    The main device class for the Bristol Wavemeter, 
    currently only tested with 872 model.
    """

    description = 'BristolWavemeter'
    allowed_children = [StaticAnalogOut]

    @set_passed_properties(
        property_names={
            'connection_table_properties': [
                'ip_address',
            ]
        }
    )
    def __init__(
            self, name, ip_address,
            default_value = 0.0,
            **kwargs):
        # does not have a parent device
        
        Device.__init__(self, name, None, ip_address, **kwargs)
        self.name = name
        self.BLACS_connection = ip_address ## double check this
        self.setpoint_type = None

        # We attach a child device only accessed via backend processes here to set 
        # outputs whose values sent to the h5 file.
        # Prawn{Blaster, DO} devices do something like this
        self._analog_output_backend = StaticAnalogOut(
            name + "Internal",
            parent_device = self,
            connection = "Internal",
            limits=None, # TODO
            unit_conversion_class=BristolWavemeterConversion,
            unit_conversion_parameters={'magnitudes': ['k', 'M', 'G', 'T']},
            default_value=default_value,
        )

        ## Is it better to overload the add_device method here?
        # Device.add_device(self, device)
        self.add_device(self._analog_output_backend)

    def get_default_unit_conversion_classes(self, device):
        """Child devices call this during their __init__ (with themselves
        as the argument) to check if there are certain unit calibration
        classes that they should apply to their outputs, if the user has
        not otherwise specified a calibration class"""

        return BristolWavemeterConversion

    def set_setpoint(self, value: float, units = None):
        """
        PID setpoint will be converted to nm if not specified as such.
        User can specify values in {'Hz', 'MHz', 'GHz', 'THz'}, or if 
        desired in nm omit units. Since device is a child device, the unit
        conversions are handled in the instantiation.
        """

        self._analog_output_backend.constant(value, units)

    def generate_code(self, hdf5_file):
        '''Generates the transition to buffered code in the h5 file.
        If parameter is not specified in shot, NaN and -1 values are set
        to tell worker not to change the value when programming.'''

        backend_devices = {}
        for output in self.child_devices:
            index = output.connection
            backend_devices[index] = output

        if not backend_devices:
            return

        columns = ['setpoint']
        dtypes = np.dtype({
            'names': columns,
            'formats': ['<f8']
            })
        
        out_table = np.zeros(1, dtype=dtypes)
        for i, devices in backend_devices.items():
            out_table['setpoint'][:] = devices.static_value 

        grp = hdf5_file.create_group('/devices/' + self.name)
        grp.create_dataset('PID_instructions', compression=config.compression, data=out_table) 

