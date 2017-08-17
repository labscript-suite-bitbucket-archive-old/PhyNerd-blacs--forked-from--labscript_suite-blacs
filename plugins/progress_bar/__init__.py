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


class Plugin(object):
    def __init__(self, initial_settings):
        self.menu = None
        self.notifications = {}
        self.BLACS = None
        self.ui = None

    def get_menu_class(self):
        return None

    def get_notification_classes(self):
        return []

    def get_setting_classes(self):
        return []

    def get_callbacks(self):
        return {'shot_complete': self.on_shot_complete}

    def set_menu_instance(self, menu):
        self.menu = menu

    def set_notification_instances(self, notifications):
        self.notifications = notifications

    def plugin_setup_complete(self, BLACS):
        self.BLACS = BLACS
        self.ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'progressbar.ui'))
        BLACS['ui'].queue_status_verticalLayout.addWidget(self.ui)

    def on_shot_complete(self, h5_filepath):
        try:
            with h5py.File(h5_filepath) as h5_file:
                n_runs = int(h5_file.attrs['n_runs'])
                run_number = int(h5_file.attrs['run number'])
                self.ui.currentProgressBar.setMaximum(n_runs)
                self.ui.currentProgressBar.setValue(run_number + 1)
        except Exception:
            pass

    def get_save_data(self):
        return {}

    def close(self):
        pass
