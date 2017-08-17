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

class Plugin(object):
    def __init__(self, initial_settings):
        self.menu = None
        self.notifications = {}
        self.BLACS = None
        self.ui = None
        self.sequences = {}
        self.initial_max = 0

    def get_menu_class(self):
        return None

    def get_notification_classes(self):
        return []

    def get_setting_classes(self):
        return []

    def get_callbacks(self):
        return {'shot_complete': self.on_shot_complete, 'on_process_request': self.on_process_request}

    def set_menu_instance(self, menu):
        self.menu = menu

    def set_notification_instances(self, notifications):
        self.notifications = notifications

    @inmain_decorator(True)
    def plugin_setup_complete(self, BLACS):
        self.BLACS = BLACS
        self.ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'progressbar.ui'))
        self.BLACS['ui'].queue_status_verticalLayout.addWidget(self.ui)

        # Set the progress bar's maximum to the current amout of loaded shots
        self.initial_max = self.BLACS['experiment_queue']._model.rowCount()
        self.ui.totalProgressBar.setMaximum(self.initial_max)
        self.ui.totalProgressBar.setValue(0)

    @inmain_decorator(True)
    def on_shot_complete(self, h5_filepath):
        try:
            with h5py.File(h5_filepath) as h5_file:
                n_runs = int(h5_file.attrs['n_runs'])
                run_number = int(h5_file.attrs['run number'])
                sequence_id = h5_file.attrs['sequence_id']
        except Exception:
            return

        # update progressbars
        new_value = self.ui.totalProgressBar.value() + 1
        if new_value < self.ui.totalProgressBar.maximum():
            self.ui.totalProgressBar.setValue(new_value)
        else:
            # reset progressbar to 0 after all shots have run
            self.ui.totalProgressBar.setValue(0)
            self.ui.totalProgressBar.setMaximum(0)
            self.initial_max = 0
            self.sequences = {}

        if run_number < n_runs - 1:
            self.ui.currentProgressBar.setValue(run_number + 1)
            self.ui.currentProgressBar.setMaximum(n_runs)
        else:
            self.ui.currentProgressBar.setValue(0)
            self.ui.currentProgressBar.setMaximum(0)

    @inmain_decorator(True)
    def on_process_request(self, h5_filepath):
        try:
            with h5py.File(h5_filepath) as h5_file:
                n_runs = int(h5_file.attrs['n_runs'])
                sequence_id = h5_file.attrs['sequence_id']
                self.sequences[sequence_id] = n_runs
        except Exception:
            pass

        if self.ui.currentProgressBar.maximum() == 0:
            self.ui.currentProgressBar.setMaximum(n_runs-1)

        # calculate new maximum
        self.ui.totalProgressBar.setMaximum(sum(self.sequences.values()) + self.initial_max)

    def get_save_data(self):
        return {}

    def close(self):
        pass
