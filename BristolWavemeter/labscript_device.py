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

# class FreqConversion(UnitConversion):
#     """
#     A Generic frequency conversion class that covers standard SI prefixes from a base of Hz.
#     """

#     base_unit = 'Hz' # must be defined here and match default hardware unit in BLACS tab

#     def __init__(self, calibration_parameters = None):
#         self.parameters = calibration_parameters
#         if hasattr(self, 'derived_units'):
#             self.derived_units += ['kHz', 'MHz', 'GHz', 'THz']
#         else:
#             self.derived_units = ['kHz', 'MHz', 'GHz', 'THz']
#         UnitConversion.__init__(self,self.parameters)
    
#     def kHz_to_base(self,kHz):
#         Hz = kHz*1e3
#         return Hz

#     def kHz_from_base(self,Hz):
#         kHz = Hz*1e-3
#         return kHz

#     def MHz_to_base(self,MHz):
#         Hz = MHz*1e6
#         return Hz

#     def MHz_from_base(self,Hz):
#         MHz = Hz*1e-6
#         return MHz

#     def GHz_to_base(self,GHz):
#         Hz = GHz*1e9
#         return Hz

#     def GHz_from_base(self,Hz):
#         GHz = Hz*1e-9
#         return GHz
    
#     def THz_to_base(self,THz):
#         Hz = THz*1e12
#         return Hz

#     def THz_from_base(self,Hz):
#         THz = Hz*1e-12
#         return THz

class BristolWavemeterConversion(UnitConversion):
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

        # Prawn{Blaster, DO} devices do something like this
        self._analog_output_backend = StaticAnalogOut(
            name + "Internal",
            parent_device = self,
            connection = "Internal",
            limits=None, # TODO
            unit_conversion_class=BristolWavemeterConversion,
            unit_conversion_parameters={'magnitudes': ['M', 'G', 'T']},
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

    # def set_setpoint(self, type: str, value: float, units = None):
    def set_setpoint(self, value: float, units = None):
        
        ## -- some unit conversions here -- ##
        self._analog_output_backend.constant(value, units)

    # def set_frequency(self, frequency, units = None):
    #     ##
    #     # convert the requested frequency to nm since PID setpoint expressed in nm
    #     freq_to_wavelength = 3e8 / frequency

    #     freq_to_wavelength = freq_to_wavelength
    #     print('Frequency to wavelength: %d\n' % freq_to_wavelength)
    #     ## call looks like: StaticAnalogQuantity.constant(value, units) ##
        
    #     self._analog_output_backend.constant(freq_to_wavelength, units)
    #     ##
    #     print(f'Got frequency: {frequency}')
    #     self._analog_output_backend.constant(frequency, units)

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

