from time import time

from BLACS.tab_base_classes import Worker, define_state
from BLACS.tab_base_classes import MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL, MODE_BUFFERED  
from BLACS.device_base_class import DeviceTab

class ni_pci_6733(DeviceTab):
    def initialise_GUI(self):
        # Capabilities
        self.num_AO = 8
        self.base_units = 'V'
        self.base_min = -10.0
        self.base_max = 10.0
        self.base_step = 0.1
        self.base_decimals = 3
        
        # Create the AO output objects
        ao_prop = {}
        for i in range(self.num_AO):
            ao_prop['ao%d'%i] = {'base_unit':self.base_units,
                                 'min':self.base_min,
                                 'max':self.base_max,
                                 'step':self.base_step,
                                 'decimals':self.base_decimals
                                }
                                
        # Create the output objects    
        self.create_analog_outputs(ao_prop)        
        # Create widgets for output objects
        dds_widgets,ao_widgets,do_widgets = self.auto_create_widgets()
        # and auto place the widgets in the UI
        self.auto_place_widgets(("Analog Outputs",ao_widgets))
        
        # Store the Measurement and Automation Explorer (MAX) name
        self.MAX_name = str(self.settings['connection_table'].find_by_name(self.device_name).BLACS_connection)
        
        # Create and set the primary worker
        self.create_worker("main_worker",NiPCI6733Worker,{'MAX_name':self.MAX_name, 'limits': [self.base_min,self.base_max], 'num_AO':self.num_AO})
        self.primary_worker = "main_worker"

        # Set the capabilities of this device
        self.supports_remote_value_check(False)
        self.supports_smart_programming(False) 
    

class NiPCI6733Worker(Worker):
    def initialise(self):
        exec 'from PyDAQmx import Task' in globals()
        exec 'from PyDAQmx.DAQmxConstants import *' in globals()
        exec 'from PyDAQmx.DAQmxTypes import *' in globals()
        global pylab; import pylab
        global h5py; import labscript_utils.h5_lock, h5py
        global numpy; import numpy
           
        # Create task
        self.ao_task = Task()
        self.ao_read = int32()
        self.ao_data = numpy.zeros((self.num_AO,), dtype=numpy.float64)
        self.setup_static_channels()            
        
        #DAQmx Start Code        
        self.ao_task.StartTask()  
        
    def setup_static_channels(self):
        #setup AO channels
        for i in range(self.num_AO): 
            self.ao_task.CreateAOVoltageChan(self.MAX_name+"/ao%d"%i,"",self.limits[0],self.limits[1],DAQmx_Val_Volts,None)
        
    def shutdown(self):        
        self.ao_task.StopTask()
        self.ao_task.ClearTask()
        
    def program_manual(self,front_panel_values):
        for i in range(self.num_AO):
            self.ao_data[i] = front_panel_values['ao%d'%i]
        self.ao_task.WriteAnalogF64(1,True,1,DAQmx_Val_GroupByChannel,self.ao_data,byref(self.ao_read),None)
          
        # TODO: Return coerced/quantised values
        return {}
        
    def transition_to_buffered(self,device_name,h5file,initial_values,fresh):
        # Store the initial values in case we have to abort and restore them:
        # TODO: Coerce/quantise these correctly before returning them
        self.initial_values = initial_values
            
        with h5py.File(h5file,'r') as hdf5_file:
            group = hdf5_file['devices/'][device_name]
            clock_terminal = group.attrs['clock_terminal']
            h5_data = group.get('ANALOG_OUTS')
            if h5_data:
                ao_channels = group.attrs['analog_out_channels']
                # We use all but the last sample (which is identical to the
                # second last sample) in order to ensure there is one more
                # clock tick than there are samples. The 6733 requires this
                # to determine that the task has completed.
                ao_data = pylab.array(h5_data,dtype=float64)[:-1,:]
                
                self.ao_task.StopTask()
                self.ao_task.ClearTask()
                self.ao_task = Task()
                ao_read = int32()

                self.ao_task.CreateAOVoltageChan(ao_channels,"",-10.0,10.0,DAQmx_Val_Volts,None)
                self.ao_task.CfgSampClkTiming(clock_terminal,1000000,DAQmx_Val_Rising,DAQmx_Val_FiniteSamps, ao_data.shape[0])
                
                self.ao_task.WriteAnalogF64(ao_data.shape[0],False,10.0,DAQmx_Val_GroupByScanNumber, ao_data,ao_read,None)
                self.ao_task.StartTask()   
                
                # Final values here are a dictionary of values, keyed by channel:
                channel_list = [channel.split('/')[1] for channel in ao_channels.split(', ')]
                final_values = {channel: value for channel, value in zip(channel_list, ao_data[-1,:])}
                return final_values
            else:
                return {}
        
    def transition_to_manual(self,abort=False):
        if not abort:
            # if aborting, don't call StopTask since this throws an
            # error if the task hasn't actually finished!
            self.ao_task.StopTask()
        self.ao_task.ClearTask()
        self.ao_task = Task()
        self.setup_static_channels()
        self.ao_task.StartTask()
        if abort:
            # Reprogram the initial states:
            self.program_manual(self.initial_values)
            
        return True
        
    def abort_transition_to_buffered(self):
        # TODO: untested
        return self.transition_to_manual(True)
        
    def abort_buffered(self):
        # TODO: untested
        return self.transition_to_manual(True)    

        
if __name__ == '__main__':
    from PySide.QtCore import *
    from PySide.QtGui import *
    import sys,os
    from labscript_utils.qtwidgets.dragdroptab import DragDropTabWidget
    from BLACS.connections import ConnectionTable
    
    
    class MyWindow(QWidget):
        
        def __init__(self,*args,**kwargs):
            QWidget.__init__(self,*args,**kwargs)
            self.are_we_closed = False
        
        def closeEvent(self,event):
            if not self.are_we_closed:        
                event.ignore()
                self.my_tab.destroy()
                self.are_we_closed = True
                QTimer.singleShot(1000,self.close)
            else:
                if not self.my_tab.destroy_complete: 
                    QTimer.singleShot(1000,self.close)                    
                else:
                    event.accept()
    
        def add_my_tab(self,tab):
            self.my_tab = tab
    
    app = QApplication(sys.argv)
    window = MyWindow()
    layout = QVBoxLayout(window)
    notebook = DragDropTabWidget()
    layout.addWidget(notebook)
    connection_table = ConnectionTable(os.path.join(os.path.dirname(os.path.realpath(__file__)),r'../example_connection_table.h5'))
    tab1 = ni_pci_6733(notebook,settings = {'device_name': 'ni_pci_6733_0', 'connection_table':connection_table})
    window.add_my_tab(tab1)
    window.show()
    def run():
        app.exec_()
        
    sys.exit(run())