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
from blacs.tab_base_classes import Tab

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

    def get_Tab(self, notebook):
        name = 'XYZ'
        tab = PluginTab(notebook, settings = {'device_name': name, 'front_panel_settings':{}, 'saved_data':{}})
        return tab, name

    def get_save_data(self):
        return {}

    def close(self):
        pass



class PluginTab(Tab):
    def __init__(self,notebook,settings,restart=False):
        class FakeConnection(object):
            def __init__(self):
                self.BLACS_connection = "Plugin"
        class FakeConnectionTable(object):
            def __init__(self):
                pass

            def find_by_name(self, device_name):
                return FakeConnection()

        settings['connection_table'] = FakeConnectionTable()

        Tab.__init__(self,notebook,settings,restart)

        self.destroy_complete = False

        # Call the initialise GUI function
        self.initialise_GUI()
        self.restore_save_data(self.settings['saved_data'] if 'saved_data' in self.settings else {})

    def initialise_GUI(self):
        # Override this function
        pass

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

    def get_front_panel_values(self):
        return {}

    def destroy(self):
        self.close_tab()
        self.destroy_complete = True
