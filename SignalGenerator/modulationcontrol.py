#####################################################################
#                                                                   #
# ddsoutput.py                                                      #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from __future__ import division, unicode_literals, print_function, absolute_import

import sys

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *

from labscript_utils.qtwidgets.analogoutput import AnalogOutput
from labscript_utils.qtwidgets.digitaloutput import DigitalOutput
from labscript_utils.qtwidgets.enumcontrol import EnumControl

class ModulationControl(QWidget):
    def __init__(self, hardware_name, connection_name='-', parent=None):
        QWidget.__init__(self,parent)
        
        self._connection_name = connection_name
        self._hardware_name = hardware_name
        
        label_text = (self._hardware_name + '\n' + self._connection_name) 
        self._label = QLabel(label_text)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
        
        
        self.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
        
        # Create widgets
        self._widgets = {}
        self._widgets['enable'] = DigitalOutput('Enable')
        self._widgets['type'] = EnumControl('',display_name='Type',horizontal_alignment=True)
        self._widgets['function'] = EnumControl('',display_name='Function',horizontal_alignment=True)
        self._widgets['rate'] = AnalogOutput('',display_name='Rate', horizontal_alignment=True)
        self._widgets['depth'] = AnalogOutput('',display_name='Depth', horizontal_alignment=True)
        self._widgets['ext'] = EnumControl('',display_name='External Coupling', horizontal_alignment=True)
        
        # Extra layout at the top level with horizontal stretches so that our
        # widgets do not grow to take up all available horizontal space:
        self._outer_layout = QHBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        # self._layout.setHorizontalSpacing(3)
        self._frame = QFrame(self)
        self._outer_layout.addStretch()
        self._outer_layout.addWidget(self._frame)
        self._outer_layout.addStretch()

        # Create grid layout that keeps widgets from expanding and keeps label centred above the widgets
        self._layout = QGridLayout(self._frame)
        self._layout.setVerticalSpacing(6)
        self._layout.setHorizontalSpacing(0)
        self._layout.setContentsMargins(0,0,0,0)
        
        v_widget = QFrame()
        v_widget.setFrameStyle(QFrame.StyledPanel)            
        v_layout = QVBoxLayout(v_widget)
        v_layout.setContentsMargins(6,6,6,6)

        # Extra widget with stretches around the enabled button so it doesn't
        # stretch out to fill all horizontal space:
        self.enable_container = QWidget()
        gate_layout = QHBoxLayout(self.enable_container)
        gate_layout.setContentsMargins(0,0,0,0)
        gate_layout.setSpacing(0)
        gate_layout.addStretch()
        gate_layout.addWidget(self._widgets['enable'])
        gate_layout.addStretch()

        self._widgets['enable'].setToolTip("Enable")
        self._widgets['type'].setToolTip("Modulation Type")
        self._widgets['function'].setToolTip("Modulation Function")
        self._widgets['rate'].setToolTip("Modulation Rate")
        self._widgets['depth'].setToolTip("Modulation Depth")
        self._widgets['ext'].setToolTip("External Input Coupling")

        v_layout.addWidget(self.enable_container)
        v_layout.addWidget(self._widgets['type'])
        v_layout.addWidget(self._widgets['function'])
        v_layout.addWidget(self._widgets['rate'])
        v_layout.addWidget(self._widgets['depth'])
        v_layout.addWidget(self._widgets['ext'])
        
        self._layout.addWidget(self._label,0,0)
        #self._layout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum),0,1)
        self._layout.addWidget(v_widget,1,0)            
        #self._layout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum),1,1)
        self._layout.addItem(QSpacerItem(0,0,QSizePolicy.Minimum,QSizePolicy.MinimumExpanding),2,0)
        
        
    def get_sub_widget(self,subchnl):
        if subchnl in self._widgets:
            return self._widgets[subchnl]
        
        raise RuntimeError('The sub-channel %s must be either gate, freq, amp or phase'%subchnl)
        
    def hide_sub_widget(self,subchnl):
        if subchnl in self._widgets:
            if subchnl == 'enable':
                self.enable_container.hide()
            else:
                self._widgets[subchnl].hide()
            return
        
        raise RuntimeError('The sub-channel %s must be either gate, freq, amp or phase'%subchnl)  
    
    def show_sub_widget(self,subchnl):
        if subchnl in self._widgets:
            if subchnl == 'enable':
                self.enable_container.show()
            else:
                self._widgets[subchnl].show()
            return
        
        raise RuntimeError('The sub-channel %s must be either gate, freq, amp or phase'%subchnl)
        
# A simple test!
if __name__ == '__main__':
    
    qapplication = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    button = ModulationControl('Modulation Control')
        
    layout.addWidget(button)
    
    window.show()
    
    
    sys.exit(qapplication.exec_())
    