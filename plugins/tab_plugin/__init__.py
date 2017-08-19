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
from blacs.tab_base_classes import Tab, Worker, define_state
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
        pass

    def get_BLACS_tab(self):
        return PluginTab

    def get_save_data(self):
        return {}

    def close(self):
        pass


class PluginWorker(Worker):
    def init(self):
        return

    def foo(self,*args,**kwargs):
        raise Exception('error!')



class PluginTab(Tab):
    ICON_OK = ':/qtutils/fugue/block'
    ICON_BUSY = ':/qtutils/fugue/clock-frame'
    ICON_ERROR = ':/qtutils/fugue/bug'
    ICON_FATAL_ERROR = ':/qtutils/fugue/bug--exclamation'

    def __init__(self,notebook,settings,restart=False):
        Tab.__init__(self,notebook,settings,restart)

        self.create_worker('My worker',PluginWorker,{'x':7})

        self.destroy_complete = False

        # Call the initialise GUI function
        self.initialise_GUI()
        self.restore_save_data(self.settings['saved_data'] if 'saved_data' in self.settings else {})

    def initialise_GUI(self):
        self.layout = self.get_tab_layout()

        foobutton = QPushButton('test')
        foobutton.clicked.connect(self.test_abc)

        self.layout.addWidget(foobutton)

    @define_state(1, True)
    def test_abc(self, *args, **kwargs):
        yield(self.queue_work('My worker', 'foo', 5, 6, 7))

    # This method should be overridden in your device class if you want to save any data not
    # stored in an AO, DO or DDS object
    # This method should return a dictionary, and this dictionary will be passed to the restore_save_data()
    # method when the tab is initialised
    def get_save_data(self):
        return {}

    # This method should be overridden in your device class if you want to restore data
    # (saved by get_save_data()) when teh tab is initialised.
    # You will be passed a dictionary of the form specified by your get_save_data() method
    #
    # Note: You must handle the case where the data dictionary is empty (or one or more keys are missing)
    #       This case will occur the first time BLACS is started on a PC, or if the BLACS datastore is destroyed
    def restore_save_data(self,data):
        return

    def update_from_settings(self,settings):
        self.restore_save_data(settings['saved_data'])

    def destroy(self):
        self.close_tab()
        self.destroy_complete = True
