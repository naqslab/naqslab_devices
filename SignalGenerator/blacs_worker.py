#####################################################################
#                                                                   #
# /naqslab_devices/SignalGenerator/blacs_worker.py                  #
#                                                                   #
# Copyright 2018, David Meyer                                       #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
from naqslab_devices.VISA.blacs_worker import VISAWorker
from labscript import LabscriptError 

import labscript_utils.h5_lock, h5py

# note, when adding a new model, put the labscript_device inheritor class
# into Models.py and the BLACS classes into a file named for the device
# in the BLACS subfolder. Update register_classes.py and __init__.py
# accordingly.


class enable_on_off_formatter(str):
    '''Class overload that converts input bools to ON or OFF string'''

    def format(self, state, chan):
        if state == 0:
            s = 'OFF'
        elif state == 1:
            s = 'ON'
        else:
            raise ValueError('Argument must be 0 or 1 equivalent.')

        return super().format(s, chan=chan)


class SignalGeneratorWorker(VISAWorker):    

    # define instrument specific read and write strings for Freq & Amp control
    freq_write_string = ''
    freq_query_string = ''
    def freq_parser(self,freq_string):
        '''Frequency Query string parser

        Converts string to float; should be be over-ridden
        if that is insufficient.

        Args:
            freq_string (str): String result from query.

        Returns:
            float: Frequency as a float.
        '''
        freq = float(freq_string)
        return freq
    amp_write_string = ''
    amp_query_string = ''
    def amp_parser(self,amp_string):
        '''Amplitude Query string parser

        Converts string to float; should be be over-ridden
        if that is insufficient.

        Args:
            amp_string (str): String result from query.

        Returns:
            float: Amplitude as a float.
        '''
        amp = float(amp_string)
        return amp
    enable_write_string = ''
    enable_query_string = ''
    def enable_parser(self,enable_string):
        '''Output Enable Query string parser.

        Converts the string to bool; should be over-ridden
        if that is insufficient.

        Args:
            enable_string (str): String result from query.

        Returns:
            bool: Boolean that indicates if output is enabled or not.
        '''
        enable = bool(int(enable_string))
        return enable
    
    def update_cache_from_dict(self, front_panel):
        '''Update the STATIC smart cache from a front_panel dictionary'''

        for chan, d in front_panel.items():
            chan_n = chan.split(' ')[-1]
            self.smart_cache['STATIC_DATA']['freq'+chan_n] = d['freq']*self.scale_factor
            self.smart_cache['STATIC_DATA']['amp'+chan_n] = d['amp']*self.amp_scale_factor
            self.smart_cache['STATIC_DATA']['gate'+chan_n] = d['gate']

    def init(self):
        # Call the VISA init to initialise the VISA connection
        VISAWorker.init(self)

        # initialize the smart cache
        self.smart_cache = {'STATIC_DATA': {}}
        self.subchnls = ['freq', 'amp', 'gate']

        # set static smart cache to current state
        current_state = self.check_remote_values()
        self.update_cache_from_dict(current_state)
        print(self.smart_cache)

    def check_remote_values(self):
        # Get the currently output values:

        results = {}

        for i in self.allowed_chans:
            # these query strings and parsers depend heavily on device
            freq = self.connection.query(
                self.freq_query_string.format(chan=i)
            )
            amp = self.connection.query(
                self.amp_query_string.format(chan=i)
            )
            enable = self.connection.query(
                self.enable_query_string.format(chan=i)
            )

            # apply scale factors to go between interface units and BLACS units
            chan_dict = {}
            chan_dict['freq'] = self.freq_parser(freq)/self.scale_factor
            chan_dict['amp'] = self.amp_parser(amp)/self.amp_scale_factor
            chan_dict['gate'] = self.enable_parser(enable)
            results[f'channel {i:d}'] = chan_dict

        return results
    
    def program_static_value(self, channel, typ, value):
        
        if typ == 'freq':
            self.connection.write(
                self.freq_write_string.format(value*self.scale_factor, chan=channel)
            )
        elif typ == 'amp':
            self.connection.write(
                self.amp_write_string.format(value*self.amp_scale_factor, chan=channel)
            )
        elif typ == 'gate':
            self.connection.write(
                self.enable_write_string.format(value, chan=channel)
            )
        else:
            raise ValueError(typ)

    def program_manual(self,front_panel_values):

        for i in self.allowed_chans:
            freq = front_panel_values[f'channel {i:d}']['freq']
            amp = front_panel_values[f'channel {i:d}']['amp']
            enable = front_panel_values[f'channel {i:d}']['gate']

            curr_freq = self.smart_cache['STATIC_DATA'][f'freq{i:d}']
            curr_amp = self.smart_cache['STATIC_DATA'][f'amp{i:d}']
            curr_enable = self.smart_cache['STATIC_DATA'][f'gate{i:d}']

            if freq != curr_freq:
                # program with scale factor
                fcommand = self.freq_write_string.format(freq*self.scale_factor, chan=i)
                self.connection.write(fcommand)

            if amp != curr_amp:
                # program with scale factor
                acommand = self.amp_write_string.format(amp*self.amp_scale_factor, chan=i)
                self.connection.write(acommand)

            if enable != curr_enable:
                # set output state
                ecommand = self.enable_write_string.format(enable, chan=i)
                self.connection.write(ecommand)

        # update smart_cache after manual update
        updated_state = self.check_remote_values()
        self.update_cache_from_dict(updated_state)

        return updated_state

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # call parent method to do basic preamble
        VISAWorker.transition_to_buffered(self,device_name,h5file,initial_values,fresh)

        self.final_values = initial_values

        data = None
        # Program static values
        with h5py.File(h5file,'r') as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            # If there are values to set the unbuffered outputs to, set them now:
            if 'STATIC_DATA' in group:
                data = group['STATIC_DATA'][0]

        if data is not None:

            # need to infer which channels are programming
            num_chan = len(data)//len(self.subchnls)
            channels = [int(name[-1]) for name in data.dtype.names[0:num_chan]]

            if fresh or data != self.smart_cache['STATIC_DATA']:

                sub_sf = {'freq': self.scale_factor,
                          'amp': self.amp_scale_factor,
                          'gate': 1}  # converts programming units to BLACS units

                for i in channels:
                    for sub in self.subchnls:
                        # program freq and amplitude as necessary
                        desired_value = data[sub+str(i)]
                        curr_value = self.smart_cache['STATIC_DATA'][sub+str(i)]
                        if curr_value != desired_value or fresh:
                            self.program_static_value(i, sub, desired_value)
                            # update smart cache to reflect programmed changes
                            self.smart_cache['STATIC_DATA'][sub+str(i)] = desired_value
                            # update final values to reflect programmed values
                            self.final_values[f'channel {i:d}'][sub] = desired_value / sub_sf[sub]

        return self.final_values


class MockSignalGeneratorWorker(SignalGeneratorWorker):
    """Mock Signal Generator Class

    Mock class for testing Signal Generator Tab functionality.
    It does not communicate with any hardware.
    """

    def init(self):
        # initialize the smart cache
        self.smart_cache = {'STATIC_DATA': {'freq0':0,'amp0':1,'gate0':False}}

    def check_remote_values(self):
        return {'channel 0':self.smart_cache['STATIC_DATA']}

    def check_status(self):
        stb = 128

        return self.convert_register(stb)

    def program_manual(self,front_panel_values):
        self.smart_cache['STATIC_DATA'] = front_panel_values['channel 0']
        return self.check_remote_values()

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        VISAWorker.transition_to_buffered(self,device_name,h5file,initial_values,fresh)

    def clear(self,value):
        pass

    def shutdown(self):
        pass
