#####################################################################
#                                                                   #
# enumcontrol.py                                                    #
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
from labscript_utils import PY2
if PY2:
    str = unicode

import sys

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *


class EnumControl(QWidget):
    def __init__(self, hardware_name, connection_name='-', display_name=None, horizontal_alignment=False, parent=None):
        QWidget.__init__(self,parent)
        
        self._connection_name = connection_name
        self._hardware_name = hardware_name
        
        label_text = (self._hardware_name + '\n' + self._connection_name) if display_name is None else display_name
        self._label = QLabel(label_text)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Minimum)
        self._combobox = QComboBox()
        self._combobox.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum)
        self._combobox.currentIndexChanged.connect(self._on_combobox_change)
        
        self._value_changed_function = None
        
        self.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)

        # Handle spinbox context menu
        # Lock/Unlock action        
        self._lock_action = QAction("Lock",self._combobox)
        self._lock_action.triggered.connect(lambda:self._menu_triggered(self._lock_action))
            
        self.menu = None
                
        def deletemenu(menu):
            menu.deleteLater()
            if menu == self.menu:
                self.menu = None
                        
        def context_menu(pos):
            self.menu = menu = self._combobox.view().createStandardContextMenu()
            # Add Divider
            menu.addSeparator()

            # Add lock action
            menu.addAction(self._lock_action)
            
            # connect signal for when menu is destroyed
            menu.aboutToHide.connect(lambda menu=menu: deletemenu(menu))
            
            # Show the menu
            menu.popup(self.mapToGlobal(pos))
            
        self._combobox.view().setContextMenuPolicy(Qt.CustomContextMenu)
        self._combobox.view().customContextMenuRequested.connect(context_menu)
        
        # Create widgets and layouts        
        if horizontal_alignment:
            self._layout = QHBoxLayout(self)
            self._layout.addWidget(self._label)
            self._layout.addWidget(self._combobox)
            self._layout.setContentsMargins(0,0,0,0)
        else:
            self._layout = QGridLayout(self)
            self._layout.setVerticalSpacing(3)
            self._layout.setHorizontalSpacing(0)
            self._layout.setContentsMargins(3,3,3,3)
            
            self._label.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Minimum)
            
            #self._layout.addWidget(self._label)            
            #self._layout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum),0,1)
            
            h_widget = QWidget()            
            h_layout = QHBoxLayout(h_widget)
            h_layout.setContentsMargins(0,0,0,0)
            h_layout.addWidget(self._combobox)
            
            self._layout.addWidget(self._label,0,0)
            self._layout.addWidget(h_widget,1,0)            
            #self._layout.addItem(QSpacerItem(0,0,QSizePolicy.MinimumExpanding,QSizePolicy.Minimum),1,1)
            self._layout.addItem(QSpacerItem(0,0,QSizePolicy.Minimum,QSizePolicy.MinimumExpanding),2,0)
        
        # Install the event filter that will allow us to catch right click mouse release events so we can popup a menu even when the button is disabled
        self.installEventFilter(self)
        
        # The Analog Out object that is in charge of this button
        self._AO = None
    
    # Setting and getting methods for the Digitl Out object in charge of this button
    def set_AO(self,AO,notify_old_AO=True,notify_new_AO=True):
        # If we are setting a new AO, remove this widget from the old one (if it isn't None) and add it to the new one (if it isn't None)
        if AO != self._AO:
            if self._AO is not None and notify_old_AO:
                self._AO.remove_widget(self,False)
            if AO is not None and notify_new_AO:
                AO.add_widget(self)
        # Store a reference to the digital out object
        self._AO = AO
        
    def get_AO(self):
        return self._AO
    
    def set_combobox_model(self,model):
        self._combobox.setModel(model)
    
    def _on_combobox_change(self):
        selected_text = self.selected_option
        if self._AO is not None:
            self._AO.change_unit(selected_text)
    
    @property
    def selected_option(self):
        return str(self._combobox.currentText())

    def block_combobox_signals(self):
        return self._combobox.blockSignals(True)
        
    def unblock_combobox_signals(self):
        return self._combobox.blockSignals(False)
    
    def set_selected_option(self,option):
        if option != self.selected_option:
            item = self._combobox.model().findItems(option)
            if item:
                model_index = self._combobox.model().indexFromItem(item[0])
                self._combobox.setCurrentIndex(model_index.row())
    
    # The event filter that pops up a context menu on a right click, even when the button is disabled
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.addAction("Lock" if self._combobox.isEnabled() else "Unlock")
            menu.triggered.connect(self._menu_triggered)
            menu.popup(self.mapToGlobal(event.pos()))
        
        return QWidget.eventFilter(self, obj, event)
     
    # This method is called whenever an entry in the context menu is clicked
    def _menu_triggered(self,action):
        if action.text() == "Lock":
            self.lock()
        elif action.text() == "Unlock":
            self.unlock()
    
    # This method locks (disables) the widget, and if the widget has a parent AO object, notifies it of the lock
    def lock(self,notify_ao=True):        
        self._combobox.setEnabled(False)
        self._lock_action.setText("Unlock")
        if self._AO is not None and notify_ao:
            self._AO.lock()
    
    # This method unlocks (enables) the widget, and if the widget has a parent AO object, notifies it of the unlock    
    def unlock(self,notify_ao=True):        
        self._combobox.setEnabled(True)        
        self._lock_action.setText("Lock")
        if self._AO is not None and notify_ao:
            self._AO.unlock()
        
    
# A simple test!
if __name__ == '__main__':
    
    qapplication = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    button = EnumControl('Control')
        
    layout.addWidget(button)
    
    window.show()
    
    
    sys.exit(qapplication.exec_())
    