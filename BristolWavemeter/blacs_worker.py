#####################################################################
#                                                                   #
# /naqslab_devices/BristolWavemeter/blacs_worker.py                 #
#                                                                   #
# Copyright 2025, Jason Pruitt                                      #
#                                                                   #
# This file is part of the naqslab devices extension to the         #
# labscript_suite. It is licensed under the Simplified BSD License. #
#                                                                   #
#                                                                   #
#####################################################################
import numpy as np
# from naqslab_devices.VISA.blacs_worker import VISAWorker
from labscript import LabscriptError
from blacs.tab_base_classes import Worker

import labscript_utils.h5_lock, h5py
import labscript_utils.properties

# # import sensitivity and tau settings from labscript device
# from naqslab_devices.BristolWavemeter.labscript_device import sens, tau

from struct import unpack

class BristolWavemeterInterface(object):
    def __init__(self, ip_address):
        global telnetlib; import telnetlib

        try:
            self.timeout = 3
            self.conn = telnetlib.Telnet(ip_address)
            self.conn.set_debuglevel(0)
            # self.skipOpeningMessage(0.5)
        except Exception as e:
            raise e

        all_meas = self.get_all_meas()
        print(f'Scan index, instrument status, wavelength, power')
        print(f'{all_meas}')

        current_status = self.check_status()
        print(f'Current status is: {current_status}')
        
        if current_status != 0:
            question_byte = self.check_questionable()
            print(f'Questionable byte is: {question_byte}')

    def send_msg(self, msg):
        """
        Main method to invoke to send a SCPI command, returns response
        """
        read_msg = msg + b'\r\n'
        self.conn.write(read_msg)
        out = b''
        while(True):
            out = self.conn.read_some()
            # if out != b'' and out != b'1':
            if out != b'':
                return out
            
    def send_msg_no_read(self, msg):
        """
        SCPI command send, without response
        """
        read_msg = msg + b'\r\n'
        self.conn.write(read_msg)

    # def get_identity(self):
    #     msg = b'*IDN?\r\n'
    #     out = self.send_msg(msg)
    #     return out

    def get_wavelength(self):
        msg = b':READ:WAV?\r\n'
        out = self.send_msg(msg)
        out.replace(b'\n\r',b'')
        return float(out.decode('ascii'))
    
    def get_all_meas(self):
        msg = b':READ:ALL?\r\n'
        out = self.send_msg(msg)
        out.replace(b'\n\r',b'')
        return(out.decode('ascii'))
        # return out

    def convert_register(self,register):
        """Converts returned register value to dict of bools
        """
        results = {}
        #get the status and convert to binary, and take off the '0b' header:
        status = bin(register)[2:]
        # if the status is less than 8 bits long, pad the start with zeros!
        while len(status)<8:
            status = '0'+status
        # reverse the status string so bit 0 is first indexed
        status = status[::-1]
        # fill the status byte dictionary
        for i in range(0,8):
            results['bit '+str(i)] = bool(int(status[i]))
        
        return results

    def check_if_PID(self):
        msg = b':SENSe:PID:FUNCtion?'
        out = self.send_msg(msg)
        out.replace(b'\n\r', b'')
        return out.decode('ascii')
    
    def set_PID_setpoint(self, value):
        if value >= 350 and value <= 14_000:
            msg = b':SENSe:PID:SPO %f' % value
            out = self.send_msg_no_read(msg)
            # out.replace(b'\n\r', b'')
            # return out.decode('ascii') 
        else:
            # Requested frequencies need to be within {21428, 857143 }
            raise LabscriptError('Value not within {350 ... 14,000} nm range')

    def convert_register(self,register):
        """Converts returned register value to dict of bools
        
        Args:
            register (int): Status register value returned from 
                            :obj:`check_status`
            
        Returns:
            dict: Status byte dictionary as formatted in :obj:`blacs_tab`
        """
        results = {}
        #get the status and convert to binary, and take off the '0b' header:
        status = bin(register)[2:]
        # if the status is less than 8 bits long, pad the start with zeros!
        while len(status)<8:
            status = '0'+status
        # reverse the status string so bit 0 is first indexed
        status = status[::-1]
        # fill the status byte dictionary
        for i in range(0,8):
            results['bit '+str(i)] = bool(int(status[i]))
        
        return results

    def check_status(self):
        """
        Response is a sum of all the set bit values of the table below:
        Bit | Bit Value |                       Condition
        5   |   32      | A bit is set in the questionable register (see STATus subsystem)
        3   |   8       | The errors in the error queue (see SYSTem subsystem)
        2   |   4       | A bit is set in the event status register
        """
        msg = b'*STB?\r\n'
        stb = self.send_msg(msg)
        stb = stb.decode('ascii')

        return self.convert_register(int(stb))

    def check_questionable(self):
        msg = b':STAT:QUES:COND?\r\n'
        out = self.send_msg(msg)
        return out.decode('ascii')

    def check_errors(self):
        """
        Returns error string from SCPI (30 entry) FIFO Error Queue.
        """

        msg = b':SYST:ERR?\r\n'
        out = self.send_msg(msg)
        return out
    
    ##Skip the opening telnet connection message.
    # @param wait_sec - time taken to read input message x3
    def skipOpeningMessage(self, wait_sec):
        print('{}'.format("testing connection"))
        skip_count = 0
        while(True):
            #out = self.conn.rawq_getchar()
            out = self.conn.read_until(b'\n\n',wait_sec)
            if out == b'':
                skip_count += 1
            if skip_count > 2:
                break

    def close(self):
        self.conn.close()

class BristolWavemeterWorker(Worker):
    # setup_string = '*ESE'
    def init(self):
        Worker.init(self)
        self.intf = BristolWavemeterInterface(self.ip_address)
    
    def check_status(self):
        status = self.intf.check_status()
        return(status)
    
    def check_remote_values(self):
        results = {}
        all_vals = self.intf.get_all_meas()
        self.logger.info(f"check_remote_values: all_vals: {all_vals}")
        # self.logger.info(f"vs front panel: {front_panel_values}")
        all_vals_list = all_vals.split(',')

        try:
            wavelength = all_vals_list[2].strip()
        except:
            raise Exception('Something wrong with measurement response')

        results['wavelength'] = wavelength
        return results
    
    def program_manual(self, front_panel_values):
        '''Performs manual updates from BLACS front panel.'''
        self.logger.info(f'Front panel values: {front_panel_values}')

        results = {}
        wavelength = front_panel_values['wavelength']
        results['wavelength'] = float(wavelength)

        self.intf.set_PID_setpoint(float(wavelength))

        return results

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        self.final_values = initial_values

        self.logger.info('Reading setpoint from instruction .h5 file')

        with h5py.File(h5file, 'r') as hdf5_file:
            group = hdf5_file['devices'][device_name]

            pid_instructions = group['PID_instructions']

            if len(pid_instructions) == 0:
                return {}
            
            setpoint = pid_instructions['setpoint'][0]
            self.logger.info(f'Read setpoint: {setpoint}')

            self.intf.set_PID_setpoint(setpoint)

        self.logger.info('Setpoint successfully set, exiting transition to buffered')
        
        return self.final_values
    
    def clear(self, value):
        self.intf.send_msg_no_read(b'*CLS\r\n')

    def transition_to_manual(self):
        if self.final_values:
            self.program_manual(self.final_values)
        return True
    
    def abort_buffered(self):
        return self.transition_to_manual()

    def abort_transition_to_buffered(self):
        return self.transition_to_manual()
    
    def shutdown(self):
        self.intf.close()
