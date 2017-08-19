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
        self.tab = None

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
        pass

    def get_BLACS_tab(self, notebook, settings, restart=False):
        self.tab = TestTab(notebook, settings, restart)
        self.tab.create_worker('My worker',PluginWorker,{'x':7})
        return self.tab

    def get_save_data(self):
        return {}

    def close(self):
        pass


class PluginWorker(Worker):
    def init(self):
        return

    def foo(self,*args,**kwargs):
        raise Exception('error!')


class TestTab(PluginTab):
    def initialise_GUI(self):
        self.layout = self.get_tab_layout()

        foobutton = QPushButton('test')
        foobutton.clicked.connect(self.test_abc)

        self.layout.addWidget(foobutton)

    @define_state(1, True)
    def test_abc(self, *args, **kwargs):
        yield(self.queue_work('My worker', 'foo', 5, 6, 7))
