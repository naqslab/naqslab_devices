#####################################################################
#                                                                   #
# /SR865.py                                                         #
#                                                                   #
#                                                                   #
#####################################################################

import numpy as np
from labscript_devices import labscript_device, BLACS_tab, BLACS_worker
from labscript_devices.VISA import VISA, VISATab, VISAWorker
from labscript import Device, AnalogOut, config, LabscriptError, set_passed_properties
import labscript_utils.properties

sens = {0:1, 1:500e-3, 2:200e-3, 3:100e-3, 4:50e-3, 5:20e-3, 6:10e-3, 7:5e-3, 8:2e-3, 9:1e-3, 
         10:500e-6, 11:200e-6, 12:100e-6, 13:50e-6, 14:20e-6, 15:10e-6, 16:5e-6, 17:2e-6, 18:1e-6, 19:500e-9,
        20:200e-9, 21:100e-9, 22:50e-9, 23:20e-9, 24:10e-9, 25:5e-9, 26:2e-9, 27:1e-9}
revsens = dict((val,key) for key,val in sens.items())
tau = {0:1e-6, 1:3e-6, 2:10e-6, 3:30e-6, 4:100e-6, 5:300e-6, 6: 1e-3, 7:3e-3, 8:10e-3, 9:30e-3,
      10:100e-3, 11:300e-3, 12:1, 13:3, 14:10, 15:30, 16:100, 17:300, 18: 1e3, 19:3e3, 20:10e3, 21:30e3}
revtau = dict((val,key) for key,val in tau.items())
        
@labscript_device              
class SR865(VISA):
    description = 'SR865 Lock-In Amplifier'
    allowed_children = None
    
    # initialize these parameters to None
    tau = None
    sens = None

    @set_passed_properties()
    def __init__(self, name, VISA_name):
        '''VISA_name can be full VISA connection string or NI-MAX alias'''
        # does not have a parent device
        VISA.__init__(self,name,None,VISA_name)
        
    def set_tau(self, tau_constant):
        '''Set the time constant in seconds.
        Uses dictionary to translate to int values.'''
        self.tau = tau_constant
        # check that setting is valid
        try:
            self.tau_i = revtau[tau_constant]
        except KeyError as e:
            raise LabscriptError('{:s}: tau cannot be set to {:f}'.format(self.VISA_name,self.tau))
        
    def set_sens(self, sensitivity):
        '''Set the sensitivity in Volts
        Uses dictionary to translated to int values.'''
        self.sens = sensitivity
        # check that setting is valid
        try:
            self.sens_i = revsens[sensitivity]
        except KeyError as e:
            raise LabscriptError('{:s}: sensitivity cannot be set to {:f}'.format(self.VISA_name,self.sens))
    
    def generate_code(self, hdf5_file):
        # type the static_table
        static_dtypes = [('tau', np.float16), ('tau_i', np.int8)] + \
                        [('sens', np.float16), ('sens_i', np.int8)]
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

        grp = hdf5_file.create_group('/devices/'+self.name)
        grp.create_dataset('STATIC_DATA',compression=config.compression,data=static_table) 
        # add these values to device properties for easy lookup
        self.set_property('tau', self.tau, location='device_properties')
        self.set_property('sensitivity', self.sens, location='device_properties')


from blacs.tab_base_classes import define_state
from blacs.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED
import sys  

# Imports for handling icons in STBstatus.ui
if 'PySide' in sys.modules.copy():
    from PySide import QtCore
    from PySide import QtGui
else:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

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
    
    #status_widget = 'SR865.ui'
    
    # setup for the sens and tau widgets
    #self._tau_comboboxmodel = QtGui.QStandardItemModel()
    #self._sens_comboboxmodel = QtGui.QStandardItemModel()
    
    #for val in tau:
    #    self._tau_comobboxmodel.appendRow(QStandardItem(val))
        
    #for val in sens:
    #    self._sens_comobboxmodel.appendRow(QStandardItem(val))
    
    def __init__(self,*args,**kwargs):
        # set the worker
        self.device_worker_class = SR865Worker
        VISATab.__init__(self,*args,**kwargs)
    
    def initialise_GUI(self):
        
        # use temporary AO widgets to report current settings and allow smart programming
        # these widgets will not allow for manual programming
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
                             'min':-360,
                             'max':360,
                             'step':1,
                             'decimals':6}}
                            
        self.create_analog_outputs(ao_prop)
        ao_widgets = self.create_analog_widgets(ao_prop)
        self.auto_place_widgets(('Settings',ao_widgets))
        
        # call VISATab.initialise to create SR865 widget
        VISATab.initialise_GUI(self)
        
        # populate combo boxes and set signals for them
        #self.status_ui.tau_comboBox.setModel(self._tau_comboboxmodel)
        #self.status_ui.sens_comboBox.setModel(self._sens_comboboxmodel)
        
        #self.status_ui.tau_comboBox.currentIndexChanged(self.tau_changed)
        #self.status_ui.sens_comboBox.currentIndexChanged(self.sens_changed)
        #self.status_ui.phase_SpinBox.

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
    
    def phase_parser(self,phase_string):
        '''Phase Query string parser'''
        phase = float(phase_string)
        return phase
    
    def init(self):
        # import h5py with locks
        global h5py; import labscript_utils.h5_lock, h5py
        # Call the VISA init to initialise the VISA connection
        VISAWorker.init(self)
        # longer timeout for potential future data reads
        #self.connection.timeout = 10000
        
        # initial configure of the instrument
        self.connection.read_termination = u'\n'
        self.connection.write('*CLS;')
        
        # initialize the smart_cache
        self.smart_cache = {'STATIC_DATA': None}
    
    def check_remote_values(self):
        # Get the current set values:

        results = {}
        
        # query instrument
        [tau_i, sens_i, phase] = self.connection.query_ascii_values('OFLT?;SCAL?;PHAS?',separator=';')
        #results['tau_i'] = int(tau_i)
        #results['sens_i'] = int(sens_i)
            
        # convert to proper numbers
        results['tau'] = tau[int(tau_i)]
        results['sens'] = sens[int(sens_i)]
        results['phase'] = self.phase_parser(phase)
        
        if (self.smart_cache['STATIC_DATA'] is not None) and (results != self.smart_cache['STATIC_DATA']):
            # remote values changed, need to reprogram on next run
            print('================RESET=======================')
            self.smart_cache['STATIC_DATA'] = None

        return results
    
    def program_manual(self,front_panel_values):
        #tau_constant = front_panel_values['tau']
        #sensitivity = front_panel_values['sens']
        #phase = front_panel_values['phase']
        
        #self.connection.write('OFLT {:d};SCAL {:d};PHAS {:.6f}'.format(revtau[tau_constant],
        #                                                    revsens[sensitivity],
        #                                                    phase))
        
        return self.check_remote_values()        

    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # call parent method to do basic preamble
        VISAWorker.transition_to_buffered(self,device_name,h5file,initial_values,fresh)
        # Program static values
        
        data = None
        with h5py.File(h5file) as hdf5_file:
            group = hdf5_file['/devices/'+device_name]
            # If there are values to set the unbuffered outputs to, set them now:
            if 'STATIC_DATA' in group:
                data = group['STATIC_DATA'][:][0]
                
        # don't forget to check if it needs to be programmed
        # by smart programming
        # and if setting isn't called for a change either
        
        if data is not None:
            if fresh or data != self.smart_cache['STATIC_DATA']:
                # Save these values into final_values so the GUI can
                # be updated at the end of the run to reflect them:
                # assume initial values in case something isn't programmed
                final_values = self.initial_values
                
                if data['tau_i'] != -1:
                    self.connection.write('OFLT {:d}'.format(data['tau_i']))
                    final_values['tau'] = tau[data['tau_i']]
                if data['sens_i'] != -1:
                    self.connection.write('SCAL {:d}'.format(data['sens_i']))
                    final_values['sens'] = sens[data['sens_i']]
                
        return final_values
        
    def transition_to_manual(self,abort = False):
        '''Save relevant parameters to h5file.'''         
        if abort:
            # If we're aborting the run, reset to original value
            self.program_manual(self.initial_values)
        # If we're not aborting the run, stick with buffered value. Nothing to do really!
        if not abort:
            # phase data to h5file as device attribute
            # first read the phase from the device, without h5lock
            
            phase = self.phase_parser(self.connection.query('PHAS?'))
            
            # add to h5file
            with h5py.File(self.h5_file,'a') as hdf5_file:
                dev_grp = hdf5_file['/devices/'+self.device_name]
                dev_grp.attrs.create('phase',phase)
                
        return True

