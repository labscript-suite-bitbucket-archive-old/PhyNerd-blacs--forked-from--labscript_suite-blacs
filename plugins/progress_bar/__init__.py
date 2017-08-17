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
        self.sequences = {}

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

    def plugin_setup_complete(self, BLACS):
        self.BLACS = BLACS
        self.ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'progressbar.ui'))
        self.BLACS['ui'].queue_status_verticalLayout.addWidget(self.ui)

        # Set the progress bar's maximum to the current amout of loaded shots
        self.initial_value = self.BLACS['experiment_queue']._model.rowCount() - 1
        self.ui.currentProgressBar.setMaximum(self.initial_value)
        self.ui.currentProgressBar.setValue(0)

    def on_shot_complete(self, h5_filepath):
        try:
            with h5py.File(h5_filepath) as h5_file:
                n_runs = int(h5_file.attrs['n_runs'])
                run_number = int(h5_file.attrs['run number'])
                sequence_id = h5_file.attrs['sequence_id']
        except Exception:
            return

        # all shots of this sequence have finished remove sequence from maximum calculation
        if run_number == n_runs - 1:
            try:
                del self.sequences[sequence_id]
            except KeyError:
                pass

        # update progressbar
        current_value = self.ui.currentProgressBar.value()
        if current_value + 1 <= self.ui.currentProgressBar.maximum():
            self.ui.currentProgressBar.setValue(current_value + 1)
        else:
            # reset progressbar to 0 after all shots have run
            self.ui.currentProgressBar.setValue(0)
            self.ui.currentProgressBar.setMaximum(0)
            self.initial_value = 0

    def on_process_request(self, h5_filepath):
        try:
            with h5py.File(h5_filepath) as h5_file:
                n_runs = int(h5_file.attrs['n_runs'])
                sequence_id = h5_file.attrs['sequence_id']
                self.sequences[sequence_id] = n_runs
        except Exception:
            pass

        # calculate new maximum
        self.ui.currentProgressBar.setMaximum(sum(self.sequences.values()) - len(self.sequences.values()) + self.initial_value)

    def get_save_data(self):
        return {}

    def close(self):
        pass
