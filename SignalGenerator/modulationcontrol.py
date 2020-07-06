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
import sys

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *

from labscript_utils.qtwidgets.analogoutput import AnalogOutput
from labscript_utils.qtwidgets.digitaloutput import DigitalOutput
from labscript_utils.qtwidgets.enumoutput import EnumOutput


class ModulationControl(QWidget):
    def __init__(self, hardware_name, parent=None):
        QWidget.__init__(self,parent)
        
        self._hardware_name = hardware_name
        
        label_text = (self._hardware_name) 
        self._label = QLabel(label_text)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
        
        
        self.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
        
        # Create widgets
        self._widgets = {}
        self._widgets['MODL'] = DigitalOutput('Enable')
        self._widgets['FNC'] = EnumOutput('',display_name='Function',horizontal_alignment=True)
        self._widgets['RATE'] = AnalogOutput('',display_name='Rate', horizontal_alignment=True)
        self._widgets['DEV'] = AnalogOutput('',display_name='Depth', horizontal_alignment=True)
        self._widgets['COUP'] = EnumOutput('',display_name='External Coupling', horizontal_alignment=True)
        
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
        gate_layout.addWidget(self._widgets['MODL'])
        gate_layout.addStretch()

        self._widgets['MODL'].setToolTip("Enable")
        self._widgets['FNC'].setToolTip("Modulation Function")
        self._widgets['RATE'].setToolTip("Modulation Rate")
        self._widgets['DEV'].setToolTip("Modulation Depth")
        self._widgets['COUP'].setToolTip("External Input Coupling")

        v_layout.addWidget(self.enable_container)
        v_layout.addWidget(self._widgets['FNC'])
        v_layout.addWidget(self._widgets['RATE'])
        v_layout.addWidget(self._widgets['DEV'])
        v_layout.addWidget(self._widgets['COUP'])
        
        self._layout.addWidget(self._label,0,0)
        #self._layout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum),0,1)
        self._layout.addWidget(v_widget,1,0)            
        #self._layout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum),1,1)
        self._layout.addItem(QSpacerItem(0,0,QSizePolicy.Minimum,QSizePolicy.MinimumExpanding),2,0)
        
        
    def get_sub_widget(self,subchnl):
        if subchnl in self._widgets:
            return self._widgets[subchnl]
        
        raise RuntimeError('The sub-channel %s must be one of [MODL,FNC,RATE,DEV,COUP]'%subchnl)
        
    def hide_sub_widget(self,subchnl):
        if subchnl in self._widgets:
            if subchnl == 'enable':
                self.enable_container.hide()
            else:
                self._widgets[subchnl].hide()
            return
        
        raise RuntimeError('The sub-channel %s must be one of [MODL,FNC,RATE,DEV,COUP]'%subchnl)  
    
    def show_sub_widget(self,subchnl):
        if subchnl in self._widgets:
            if subchnl == 'enable':
                self.enable_container.show()
            else:
                self._widgets[subchnl].show()
            return
        
        raise RuntimeError('The sub-channel %s must be one of [MODL,FNC,RATE,DEV,COUP]'%subchnl)
        
# A simple test!
if __name__ == '__main__':
    
    qapplication = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    button = ModulationControl('Modulation Control')
        
    layout.addWidget(button)
    
    window.show()
    
    
    sys.exit(qapplication.exec_())
    
