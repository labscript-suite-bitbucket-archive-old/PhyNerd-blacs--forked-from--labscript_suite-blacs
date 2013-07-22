import gtk
import threading
from output_classes import AO
from tab_base_classes import Tab, Worker, define_state
import subproc_utils

class adwin(Tab):
    def __init__(self,BLACS,notebook,settings,restart=False):
        Tab.__init__(self,BLACS,ADWinWorker,notebook,settings)
        self.settings = settings
        self.device_name = settings['device_name']
        self.device_number = int(self.settings['connection_table'].find_by_name(self.device_name).BLACS_connection)
        self.static_mode = True
        self.destroy_complete = False
        self.boot_image_path = '/home/bilbo/Desktop/current_work/ADwin/linux/adwin-lib-5.0.5/share/btl/adwin11.btl'
        self.process_1_image_path = '/home/bilbo/Desktop/current_work/ADwin/V5-Rydberg/main.TB1'
        self.process_2_image_path = '/home/bilbo/Desktop/current_work/ADwin/V5-Rydberg/copy_local.TB2'
        
        
        self.static_update_request = subproc_utils.Event('ADWin_static_update_request', type='wait')
        self.static_update_complete = subproc_utils.Event('ADWin_static_update_complete', type='post')
        
        # start the thread that will handle requests for output updates from the other tabs:
        request_handler_thread = threading.Thread(target=self.request_handler_loop)
        request_handler_thread.daemon = True
        request_handler_thread.start()
        
        self.initialise_device()
        
    def request_handler_loop(self):
        """Simply collects static_update requests from other calling
        processes/threads and translates them into static update calls
        here"""
        while True:
            data = self.static_update_request.wait(id=self.device_number)
            self.static_update(data)
            
    @define_state
    def static_update(self, data):
        if data['type'] == 'analog':
            self.queue_work('analog_static_update', data['card'], data['values'])
        elif data['type'] == 'digital':
            self.queue_work('digital_static_update', data['card'], data['values'])
        self.do_after('post_update_done', data['card'])
        
    def post_update_done(self, card, _results):
        """Tells the caller that their static update has been processed"""
        if _results is not None:
            response = True
        else:
            # The update did not complete properly:
            response = Exception('Setting the device output did not complete correctly.' +
                                 'Please see the corresponding ADWin tab for more info.')
        self.static_update_complete.post(id=[self.device_number, card],data=response)
        
            
    @define_state
    def initialise_device(self):
        self.queue_work('initialise', self.device_name, self.device_number, 
                        self.boot_image_path, self.process_1_image_path, self.process_2_image_path)

    @define_state
    def transition_to_buffered(self,h5file,notify_queue):
        self.static_mode = False
        self.queue_work('program_buffered', h5file)
        self.do_after('leave_transition_to_buffered', notify_queue)

    @define_state
    def abort_buffered(self):      
        self.static_mode = True
        # We don't have to do anything
        pass
           
    @define_state
    def leave_transition_to_buffered(self, notify_queue, _results):
        self.static_mode = True
        notify_queue.put(self.device_name)

    @define_state
    def start_run(self, notify_queue):
        self.queue_work('start_run')
        self.statemachine_timeout_add(1,self.status_monitor, notify_queue)
    
    @define_state
    def status_monitor(self, notify_queue):
        self.queue_work('status_monitor')
        self.do_after('leave_status_monitor', notify_queue)
        raise Exception('fuck you, have an exception!')
        
    def leave_status_monitor(self, notify_queue, _results):
        if _results:
            # experiment is over:
            self.timeouts.remove(self.status_monitor)
            notify_queue.put(self.device_name)
                                    
    @define_state
    def destroy(self):
        self.do_after('leave_destroy')
        
    def leave_destroy(self,_results):
        self.destroy_complete = True
        self.close_tab()
        
    
class ADWinWorker(Worker):
#class ADWinWorker(object):
    ADWIN_TOTAL_CYCLE_TIME = 2
    ADWIN_CYCLE_DELAY = 4
    ADWIN_NEW_DATA = 5

    ANALOG_TIMEPOINT = 1
    ANALOG_DURATION = 2
    ANALOG_CARD_NUM = 3
    ANALOG_CHAN_NUM = 4
    ANALOG_RAMP_TYPE = 5
    ANALOG_PAR_A = 6
    ANALOG_PAR_B = 7
    ANALOG_PAR_C = 8
    
    DIGITAL_TIMEPOINT = 10
    DIGITAL_CARD_NUM = 11
    DIGITAL_VALUES = 12
    

    def init(self):
        global ADwin; import ADwin
        
    def initialise(self, device_name, device_number, boot_image_path, process_1_image_path, process_2_image_path):
        self.device_name = device_name
        self.aw = ADwin.ADwin(device_number)

    
        self.aw.Boot(boot_image_path)
        self.aw.Load_Process(process_1_image_path)
        self.aw.Load_Process(process_2_image_path)
        self.aw.Start_Process(1)
        self.aw.Start_Process(2)



    def analog_static_update(self, card, voltages):
        output_values = []
        # Convert the output values to integers as required by the API:
        for voltage in voltages:
            if not -10 <= voltage <= 10:
                raise ValueError('voltage not in range [-10,10]:' + str(voltage))
            output_value = int((voltage+10)/20.*(2**16-1))
            output_values.append(output_value)
        for i, output_value in enumerate(output_values):
            chan = array_index = i+1 # ADWin uses indexing that starts from one
            
            # Set the timepoint:
            self.aw.SetData_Long([0], self.ANALOG_TIMEPOINT, Startindex=array_index, Count=1)
            # The duration, minimum possible; 1 cycle:
            self.aw.SetData_Long([1], self.ANALOG_DURATION, Startindex=array_index, Count=1)
            # The card_number and channel:
            self.aw.SetData_Long([card], self.ANALOG_CARD_NUM, Startindex=array_index, Count=1)
            self.aw.SetData_Long([chan], self.ANALOG_CHAN_NUM, Startindex=array_index, Count=1)
            # The ramp type and parameters such as to create just a constant
            # value through use of a trivial linear ramp:
            self.aw.SetData_Long([0], self.ANALOG_RAMP_TYPE, Startindex=array_index, Count=1)
            self.aw.SetData_Long([output_value], self.ANALOG_PAR_A, Startindex=array_index, Count=1)
            self.aw.SetData_Long([0], self.ANALOG_PAR_B, Startindex=array_index, Count=1)
            self.aw.SetData_Long([output_value], self.ANALOG_PAR_C, Startindex=array_index, Count=1)
        # And now the stop instruction:
        array_index += 1
        self.aw.SetData_Long([2147483647], self.ANALOG_TIMEPOINT, Startindex=array_index, Count=1)
        # Set the total cycle time, a small number:
        self.aw.Set_Par(self.ADWIN_TOTAL_CYCLE_TIME, 2)
        # Set the delay, large enough for all the channels to be programmed:
        self.aw.Set_Par(self.ADWIN_CYCLE_DELAY, 30000) # 100us
        # Tell the program that there is new data:
        self.aw.Set_Par(self.ADWIN_NEW_DATA, 1)
        return True # indicates success


    def digital_static_update(self, card, values):
        output_values = 0
        # Convert the digital values to an integer bitfield as required by the API:
        for i, value in enumerate(values):
            if value:
                output_values += 2**i
        # Set the timepoint:
        self.aw.SetData_Long([0], self.DIGITAL_TIMEPOINT, Startindex=1, Count=1)
        # The card_number:
        self.aw.SetData_Long([card], self.DIGITAL_CARD_NUM, Startindex=1, Count=1)
        # The output values:
        self.aw.SetData_Long([output_values], self.DIGITAL_VALUES, Startindex=1, Count=1)
        # And now the stop instruction:
        self.aw.SetData_Long([2147483647], self.DIGITAL_TIMEPOINT, Startindex=2, Count=1)
        # Set the total cycle time, a small number:
        self.aw.Set_Par(self.ADWIN_TOTAL_CYCLE_TIME, 2)
        # Set the delay, some small value:
        self.aw.Set_Par(self.ADWIN_CYCLE_DELAY, 3000) # 10us
        # Tell the program that there is new data:
        self.aw.Set_Par(self.ADWIN_NEW_DATA, 1)
        return True # indicates success
        
        
    def program_buffered(self, h5file):
        print 'fake program buffered!', h5file
    
    def start_run(self):
        print 'fake start_run!'
            
    def status_monitor(self):
        print 'status_monitor in subproc!'
        import time
        time.sleep(1)
        return False
        
#worker = ADWinWorker()
#worker.init()
#worker.initialise(1, '/home/bilbo/Desktop/current_work/ADwin/linux/adwin-lib-5.0.5/share/btl/adwin11.btl',
#                     '/home/bilbo/Desktop/current_work/ADwin/V5-Rydberg/main.TB1',
#                     '/home/bilbo/Desktop/current_work/ADwin/V5-Rydberg/copy_local.TB2')
##worker.analog_static_update(9,[10]*8)
#worker.digital_static_update(1,[True]*32)


