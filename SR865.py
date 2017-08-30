#####################################################################
#                                                                   #
# /SR865.py                                                         #
#                                                                   #
#                                                                   #
#####################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from labscript_devices.VISA import VISA, VISATab, VISAWorker
from labscript import Device, AnalogOut, config, LabscriptError, set_passed_properties
import labscript_utils.properties

sens = np.array([1,500e-3,200e-3,100e-3,50e-3,20e-3,10e-3,5e-3,2e-3,1e-3,
                    500e-6,200e-6,100e-6,50e-6,20e-6,10e-6,5e-6,2e-6,1e-6,
                    500e-9,200e-9,100e-9,50e-9,20e-9,10e-9,5e-9,2e-9,1e-9])
                    
tau = np.array([1e-6,3e-6,10e-6,30e-6,100e-6,300e-6,
                1e-3,3e-3,10e-3,30e-3,100e-3,300e-3,
                1,3,10,30,100,300,1e3,3e3,10e3,30e3])
        
@labscript_device              
class SR865(VISA):
    description = 'SR865 Lock-In Amplifier'
    allowed_children = None
    
    # initialize these parameters to None
    tau = None
    sens = None
    phase = None

    @set_passed_properties()
    def __init__(self, name, VISA_name):
        '''VISA_name can be full VISA connection string or NI-MAX alias'''
        # does not have a parent device
        VISA.__init__(self,name,None,VISA_name)
        
    def set_tau(self, tau_constant):
        '''Set the time constant in seconds.
        Uses numpy digitize to translate to int values.'''
        self.tau = tau_constant
        # check that setting is valid
        if tau_constant in tau:
            self.tau_i = np.digitize(tau_constant,tau,right=True)
        else:
            raise LabscriptError('{:s}: tau cannot be set to {:f}'.format(self.VISA_name,self.tau))
        
    def set_sens(self, sensitivity):
        '''Set the sensitivity in Volts
        Uses numpy digitize to translate to int values.'''
        self.sens = sensitivity
        # check that setting is valid
        if sensitivity in sens:
            self.sens_i = np.digitize(sensitivity,sens)
        else:
            raise LabscriptError('{:s}: sensitivity cannot be set to {:f}'.format(self.VISA_name,self.sens))
            
    def set_phase(self, phase):
        '''Set the phase reference in degrees
        Device auto-converts to -180,180 range'''
        self.phase = phase
        
    
    def generate_code(self, hdf5_file):
        # type the static_table
        static_dtypes = np.dtype({'names':['tau','tau_i','sens','sens_i','phase'],
                            'formats':[np.float16,np.int8,np.float16,np.int8,np.float32]})
        static_table = np.zeros(1,dtype=static_dtypes)
        
        # if tau is set, add tau value to table, else add NaN
        if self.tau:
            static_table['tau'] = self.tau
            static_table['tau_i'] = self.tau_i
        else:
            static_table['tau'] = np.NaN
            static_table['tau_i'] = -1
        # if sensitivity is set, add sens to table, else add NaN
        if self.sens:
            static_table['sens'] = self.sens
            static_table['sens_i'] = self.sens_i
        else:
            static_table['sens'] = np.NaN
            static_table['sens_i'] = -1
        # if phase set, add to table, else NaN
        if self.phase:
            static_table['phase'] = self.phase
        else:
            static_table['phase'] = np.NaN

        grp = hdf5_file.create_group('/devices/'+self.name)
        grp.create_dataset('STATIC_DATA',compression=config.compression,data=static_table) 
        # add these values to device properties for easy lookup
        if self.tau: self.set_property('tau', self.tau, location='device_properties')
        if self.sens: self.set_property('sensitivity', self.sens, location='device_properties')
        if self.phase: self.set_property('phase',self.phase,location='device_properties')


from blacs.tab_base_classes import define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED 

@BLACS_tab
class SR865Tab(VISATab):
    # Capabilities

    status_byte_labels = {'bit 7':'unused', 
                          'bit 6':'SRQ',
                          'bit 5':'ESB',
                          'bit 4':'MAV',
                          'bit 3':'LIA',
                          'bit 2':'ERR',
                          'bit 1':'unused',
                          'bit 0':'unused'}
    
    def __init__(self,*args,**kwargs):
        # set the worker
        self.device_worker_class = SR865Worker
        VISATab.__init__(self,*args,**kwargs)
    
    def initialise_GUI(self):
        
        # use AO widgets to mimick functionality
        ao_prop = {'tau':{'base_unit':'s',
                          'min':1e-6,
                          'max':30e3,
                          'step':1,
                          'decimals':6},
                    'sens':{'base_unit':'V',
                            'min':1e-9,
                            'max':1,
                            'step':1e-3,
                            'decimals':9},
                    'phase':{'base_unit':'deg',
                             'min':-180,
                             'max':180,
                             'step':1,
                             'decimals':6}}
                            
        self.create_analog_outputs(ao_prop)
        ao_widgets = self.create_analog_widgets(ao_prop)
        self.auto_place_widgets(('Settings',ao_widgets))
        
        # call VISATab.initialise to create SR865 widget
        VISATab.initialise_GUI(self)

        # Set the capabilities of this device
        self.supports_remote_value_check(True)
        self.supports_smart_programming(True) 
        self.statemachine_timeout_add(5000, self.status_monitor)   
        
    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True,True)
    def tau_changed(self,widget=None):
        value = self.status_ui.tau_comboBox.currentIndex()
        new_value = yield(self.queue_work(self._primary_worker,'set_tau',value))
        
        # only update if value is different
        if new_value != value:
            # block signals for update
            self.status_ui.tau_comboBox.blockSignals(True)
            self.status_ui.tau_comboBox.setCurrentIndex(new_value)
            self.status_ui.tau_comboBox.blockSignals(False)
        
    @define_state(MODE_MANUAL|MODE_BUFFERED|MODE_TRANSITION_TO_BUFFERED|MODE_TRANSITION_TO_MANUAL,True,True)
    def sens_changed(self,widget=None):
        value = self.status_ui.sens_comboBox.currentIndex()
        new_value = yield(self.queue_work(self._primary_worker,'set_sens',value))
        
        # only update if value is different
        if new_value != value:
            # block signals for update
            self.status_ui.tau_comboBox.blockSignals(True)
            self.status_ui.tau_comboBox.setCurrentIndex(new_value)
            self.status_ui.tau_comboBox.blockSignals(False)

@BLACS_worker
class SR865Worker(VISAWorker):
    program_string = 'OFLT {:d};SCAL {:d};PHAS {:.6f}'
    read_string = 'OFLT?;SCAL?;PHAS?'   
    
    def phase_parser(self,phase_string):
        '''Phase Query string parser'''
        phase = float(phase_string)
        return phase
        
    def coerce_tau(self,tau_constant):
        '''Returns coerced, valid integer setting. 
        Tau value rounds up.
        Returns max or min valid setting if out of bound.'''
        coerced_i = int(np.digitize(tau_constant,tau,right=True))
        if coerced_i >= len(tau):
            coerced_i -= 1
        return coerced_i
        
    def coerce_sens(self,sensitivity):
        '''Returns coerced, valid integer setting. 
        Sens value rounds down.
        Returns max or min valid setting if out of bound.'''
        coerced_i = int(np.digitize(sensitivity,sens))
        if coerced_i >= len(sens):
            coerced_i -= 1
        return coerced_i
    
    def init(self):
        # import h5py with locks
        global h5py; import labscript_utils.h5_lock, h5py
        # Call the VISA init to initialise the VISA connection
        VISAWorker.init(self)
        
        # initial configure of the instrument
        self.connection.read_termination = u'\n'
        self.connection.write('*CLS;')
        
        # initialize the smart_cache
        self.smart_cache = {'STATIC_DATA': None}
    
    def check_remote_values(self):
        # Get the current set values:
        results = {}

        [tau_i, sens_i, phase] = self.connection.query_ascii_values(self.read_string,separator=';')
            
        # convert to proper numbers
        results['tau'] = tau[int(tau_i)]
        results['sens'] = sens[int(sens_i)]
        results['phase'] = self.phase_parser(phase)
        
        if (self.smart_cache['STATIC_DATA'] is not None) and (results != self.smart_cache['STATIC_DATA']):
            # remote values changed, need to reprogram on next run
            self.smart_cache['STATIC_DATA'] = None

        return results
    
    def program_manual(self,front_panel_values):
        # coerce the front_panel tau & sens to a valid setting
        tau_i = self.coerce_tau(front_panel_values['tau'])
        sens_i = self.coerce_sens(front_panel_values['sens'])
        phase = front_panel_values['phase']
        
        self.connection.write(self.program_string.format(tau_i,sens_i,phase))
                
        return self.check_remote_values()        

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # call parent method to do basic preamble
        VISAWorker.transition_to_buffered(self,device_name,h5file,initial_values,fresh)
        
        data = None
        with h5py.File(h5file) as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            # If there are values to set the unbuffered outputs to, set them now:
            if 'STATIC_DATA' in group:
                data = group['STATIC_DATA'][:][0]
                
        # Save these values into final_values so the GUI can
        # be updated at the end of the run to reflect them:
        # assume initial values in case something isn't programmed
        self.final_values = self.initial_values
        
        if data is not None:
            if fresh or data != self.smart_cache['STATIC_DATA']:                
                if data['tau_i'] != -1:
                    self.connection.write('OFLT {:d}'.format(data['tau_i']))
                    self.final_values['tau'] = tau[data['tau_i']]
                else:
                    self.final_values['tau'] = tau[initial_values['tau_i']]
                if data['sens_i'] != -1:
                    self.connection.write('SCAL {:d}'.format(data['sens_i']))
                    self.final_values['sens'] = sens[data['sens_i']]
                else:
                    self.final_values['sens'] = sens[initial_values['sens_i']]
                if not np.isnan(data['phase']):
                    self.connection.write('PHAS {:.6f}'.format(data['phase']))
                    self.final_values['phase'] = data['phase']
                else:
                    self.final_values['phase'] = initial_values['phase']
                    
        # write the final_values to h5file for later lookup
        with h5py.File(h5file) as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            group.attrs.create('sensitivity',self.final_values['sens'])
            group.attrs.create('tau',self.final_values['tau'])
            group.attrs.create('phase',round(self.final_values['phase'],6))
                
        return self.final_values

