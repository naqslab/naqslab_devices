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
            self.skipOpeningMessage(0.5) # is this not necessary?

        except Exception as e:
            raise e
        
        identity = self.get_identity()
        print(f'IDN Response: {identity}')
        all_meas = self.get_all_meas()
        print(f'ALL Response: {all_meas}')
        # current_status = self.check_status()
        # print(f'Current status is: {current_status}')

        # current_wavelength = self.get_wavelength()
        # print(f'Current wavelength is: {current_wavelength}')

        # PID_capable = self.check_if_PID()
        # print(f'PID: {PID_capable}')

    def send_msg(self, msg):
        read_msg = msg + b'\r\n'
        self.conn.write(read_msg)
        skip_count = 0
        out = b''
        while(True):
            out = self.conn.read_some()
            if out != b'' and out != b'1':
                # print(out)
                return out

    def get_identity(self):
        msg = b'*IDN?\r\n'
        out = self.send_msg(msg)
        out.replace(b'\n\r',b'')
        return(out.decode('ascii'))
            
    def get_wavelength(self):
        msg = b':READ:WAV?\r\n'
        out = self.send_msg(msg)
        out.replace(b'\n\r',b'')
        return float(out.decode('ascii'))
    
    def get_all_meas(self):
        msg = b':READ:ALL?\r\n'
        out = self.send_msg(msg)
        out.replace(b'\n\r',b'')
        # return(out.decode('ascii'))
        return(out.decode('ascii'))
        
    # def readWN(self):
    #     msg = b':READ:WNUM?\r\n'
    #     out = self.send_msg(msg)
    #     out.replace(b'\n\r',b'')
    #     return float(out.decode('ascii'))

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
        msg = b':SENSe:PID:SPO %d', value
        out = self.send_msg(msg)
        out.replace(b'\n\r', b'')
        return out.decode('ascii') 

    def check_status(self):
        msg = b'*STB?\r\n'
        out = self.send_msg(msg)
        out.replace(b'\n\r',b'')
        out = out.decode('ascii')
        mask = 122
        error_code = out & mask
        return error_code
        
    #     if error_code:
    #         # error exists, but nothing to report beyond register value
    #         print('{:s} has ESR = {:d}'.format(self.name, error_code))
        
    #     return self.convert_register(esr)

    ##Skip the opening telnet connection message.
    #@param wait_sec - time taken to read input message x3
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
        print(f"check_remote_values: all_vals: {all_vals}")
        all_vals_list = all_vals.split(',')

        wavelength = all_vals_list[2].strip()
        try:
            frequency = 3e8 / float(wavelength)
            results['frequency'] = frequency
        except ZeroDivisionError:
            results['frequency'] = 0.0

        return results
    
    # def remote_update_front_panel(self, front_panel_values):
    #     current_remote = self.check_remote_values()
    #     try:
    #         self.program_manual(current_remote['wavelength'])
    #     except Exception as e:
    #         raise e
    
    def program_manual(self,front_panel_values):
        '''Performs manual updates from BLACS front panel.'''
        print(f'Front panel values: {front_panel_values}')

        results = {}
        frequency = front_panel_values['frequency']
        results['frequency'] = float(frequency)
                
        # return self.check_remote_values() # this works but overrides front panel with remote
        return results # not sure about this

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # call parent method to do basic preamble
        Worker.transition_to_buffered(self,device_name,h5file,initial_values,fresh)
        pass


