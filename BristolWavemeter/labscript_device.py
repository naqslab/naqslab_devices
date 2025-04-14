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

__version__ = '0.1.0'
__author__ = ['Json-To-String']


# class _BristolWavemeterBackendAO(StaticAnalogOut):
#     def __init__()
#     pass
class BristolWavemeter(Device):
    description = 'BristolWavemeter'
    allowed_children = [StaticAnalogOut]
    
    # frequency = None

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

        # Prawn{Blaster, DO} devices do something like this
        self._analog_output_backend = StaticAnalogOut(
            name + "Internal",
            parent_device = self,
            connection = "Internal",
            limits=None, # TODO
            unit_conversion_class=None,
            unit_conversion_parameters=None,
            default_value=default_value,
        )

        # Device.add_device
        self.add_device(self._analog_output_backend) 
        # self._analog_output_backend.frequency = 8e5 # lowest value -> 375 nm

    # def set_wavelength(self, frequency, units='hz'):
    def set_frequency(self, frequency):

        # convert the requested frequency to nm since PID setpoint expressed in nm
        freq_to_wavelength = 3e8 / frequency

        # setpoints are ints
        freq_to_wavelength = int(freq_to_wavelength)
        print('Frequency to wavelength: %d\n' % freq_to_wavelength)
        ## call looks like: StaticAnalogQuantity.constant(value, units) ##
        
        self._analog_output_backend.constant(freq_to_wavelength)

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

        dtypes = np.dtype({
            'names':['setpoint'],
            # 'formats':[np.float64]
            'formats':['<f8']
            })
        
        out_table = np.zeros(1, dtype=dtypes)
        for i, devices in backend_devices.items():
            out_table['setpoint'][:] = devices.static_value 

        grp = hdf5_file.create_group('/devices/' + self.name)
        grp.create_dataset('PID_instructions', compression=config.compression, data=out_table) 
