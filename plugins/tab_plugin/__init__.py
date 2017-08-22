#####################################################################
#                                                                   #
# /plugins/general/__init__.py                                      #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the program BLACS, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import os
import labscript_utils.h5_lock
import h5py
from qtutils import UiLoader
from qtutils import inmain_decorator
from blacs.tab_base_classes import PluginTab, Worker, define_state
import qtutils.icons
from qtutils.qt.QtWidgets import *

class Plugin(object):
    def __init__(self, initial_settings):
        self.menu = None
        self.notifications = {}
        self.BLACS = None

    def get_menu_class(self):
        return None

    def get_notification_classes(self):
        return []

    def get_setting_classes(self):
        return []

    def get_callbacks(self):
        return {}

    def set_menu_instance(self, menu):
        self.menu = menu

    def set_notification_instances(self, notifications):
        self.notifications = notifications

    def plugin_setup_complete(self, BLACS):
        self.BLACS = BLACS

    def get_tab_classes(self):
        return {'hallo': TestTab}

    def get_save_data(self):
        return {}

    def close(self):
        pass


class TestTab(PluginTab):
    def initialise_GUI(self):
        self.layout = self.get_tab_layout()

        self.foobutton = QPushButton('Error')
        self.foobutton.clicked.connect(self.test_abc)

        self.layout.addWidget(self.foobutton)

    def test_abc(self, *args):
        raise Exception('test')

    def get_save_data(self):
        return {}

    def restore_save_data(self,data):
        return
