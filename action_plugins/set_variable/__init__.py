# -*- coding: utf-8; -*-

# Copyright (C) 2015 - 2019 Lionel Ott
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
from PyQt5 import QtCore, QtGui, QtWidgets
from xml.etree import ElementTree

from gremlin.base_classes import AbstractAction, AbstractFunctor
from gremlin.common import InputType
import gremlin.ui.input_item

class RowMajorTableModel(QtGui.QStandardItemModel):
    def __init__(self, num_columns=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setColumnCount(num_columns)
        cc = self.columnCount()
        rc = self.rowCount()
        pass

    def __len__(self):
        return self.rowCount()
    def __getitem__(self, key):
        if key >= self.__len__():
            raise IndexError("Index {key} out of range (0 to {max_key}".format(key=key, max_key=self.__len__()-1))
        return [self.item(key, column) for column in range(self.columnCount())]
    def __setitem__(self, key, value):
        if 0 >= key > self.__len__():
            raise IndexError("Index {key} out of range (0 to {max_key}".format(max_key=self.__len__()))
        cc = self.columnCount()
        if self.columnCount() >= 0:
            #if len(value) != self.columnCount():
            #    raise ValueError("Trying to set wrong number of elements. Trying to set {} elements, but {} required".format(len(value), self.columnCount()))
            if key == self.__len__():
                self.appendRow([QtGui.QStandardItem(val) for val in value])
            else:
                for col, val in enumerate(value):
                    self.setItem(key, col, QtGui.QStandardItem(val))
    def append(self, value):
        self[len(self)] = [val for val in value]
    def extend(self, values):
        for val in values:
            self.append(val)
    def set_all(self, values):
        self.clear()
        self.extend(values)

    def __delitem__(self, key):
        pass
    #def __iter__(self):
    #    return range(self.__len__())


class SetVariablesWidget(gremlin.ui.input_item.AbstractActionWidget):

    """Widget allowing a list of variables to set."""

    def __init__(self, action_data, parent=None):
        super().__init__(action_data, parent=parent)
        assert(isinstance(action_data, SetVariables))

    def _create_ui(self):
        self.model = RowMajorTableModel(num_columns = 2)
        #self.model[0] = ["hello", "world"]
        #self.model[1] = ["goodbye", "world"]
        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # Add widgets which allow modifying the mode list
        self.mode_list = QtWidgets.QComboBox()
        self.variable_name = QtWidgets.QLineEdit()
        self.variable_value = QtWidgets.QLineEdit()
        for entry in gremlin.profile.mode_list(self.action_data):
            self.mode_list.addItem(entry)
        self.add = QtWidgets.QPushButton(
            QtGui.QIcon("gfx/list_add.svg"), "Add"
        )
        self.add.clicked.connect(self._add_cb)
        self.delete = QtWidgets.QPushButton(
            QtGui.QIcon("gfx/list_delete.svg"), "Delete"
        )
        self.delete.clicked.connect(self._remove_cb)
        
        self.actions_layout = QtWidgets.QGridLayout()
        self.actions_layout.addWidget(self.variable_name, 0, 0)
        self.actions_layout.addWidget(self.variable_value, 0, 1)
        self.actions_layout.addWidget(self.add, 1, 1)
        self.actions_layout.addWidget(self.delete, 1, 2)
        self.main_layout.addWidget(self.view)
        self.main_layout.addLayout(self.actions_layout)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

    def _populate_ui(self):
        self.model.set_all(self.action_data.variables)

    def save_changes(self):
        """Saves UI state to the profile."""
        self.action_data.variables = [(k.data(), v.data()) for k,v in self.model]
        self.action_data.variables_dict = dict(self.action_data.variables)
        self.action_modified.emit()

    def _add_cb(self):
        """Adds the currently selected mode to the list of modes."""
        #current_vars = self.model.stringList()
        #current_vars.append([self.variable_name, self.variable_value])
        self.model.append([self.variable_name.text(), self.variable_value.text()])
        self.save_changes()

    def _remove_cb(self):
        """Removes the currently selected mode from the list of modes."""
        variables = list(self.model)
        index = self.view.currentIndex().row()
        if 0 <= index < len(mode_list):
            del variables[index]
            self.model.set_all(variables)
            self.view.setCurrentIndex(self.model.index(0, 0))
            self.save_changes()


class SetVariablesFunctor(AbstractFunctor):

    def __init__(self, action):
        super().__init__(action)
        self.variables = action.variables

    def process_event(self, event, value):
        for variable, value in self.variables:
            gremlin.event_handler.EventHandler().set_variable(variable, value)
        return True


class SetVariables(AbstractAction):

    """Action allowing the switching through a list of modes."""

    name = "Set Variables"
    tag = "set-variables"

    default_button_activation = (True, False)
    input_types = [
        InputType.JoystickAxis,
        InputType.JoystickButton,
        InputType.JoystickHat,
        InputType.Keyboard
    ]

    functor = SetVariablesFunctor
    widget = SetVariablesWidget

    def __init__(self, parent):
        super().__init__(parent)
        self.variables = []
        self.variables_dict = []

    def icon(self):
        return "{}/icon.png".format(os.path.dirname(os.path.realpath(__file__)))

    def requires_virtual_button(self):
        return self.get_input_type() in [
            InputType.JoystickAxis,
            InputType.JoystickHat
        ]

    def _parse_xml(self, node):
        for child in node:
            self.variables.append(child.get("name"), child.get("value"))

    def _is_valid(self):
        return len(self.variables) > 0

    def _generate_xml(self):
        node = ElementTree.Element("set-variables")
        for variable, value in self.variables:
            child = ElementTree.Element("variable")
            child.set("name", variable)
            child.set("value", value)
            node.append(child)
        return node


version = 1
name = "set-variables"
create = SetVariables
