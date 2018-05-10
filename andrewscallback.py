from PyDAQmx import *
from PyDAQmx.DAQmxCallBack import *
import numpy as np
from ctypes import *
import daqface.Utils as Util
import matplotlib.pyplot as plt


class TypeList(list):
    pass


class DoAiCallbackTask:
    def __init__(self, ai_device, ai_channels, do_device, samp_rate, secs, write, sync_clock, samps_per_callback, response_length_secs, response_start_secs, lick_fraction):
        self.ai_handle = TaskHandle(0)
        self.do_handle = TaskHandle(1)
        self.ai_channels = ai_channels
        self.total_length = np.uint64(samp_rate * secs)
        self.samps_per_callback = samps_per_callback
        self.callback_counter = 0
        self.response_length = response_length_secs * samp_rate
        self.response_start = response_start_secs * samp_rate
        self.lick_fraction = lick_fraction

        # set up data buffers (analog)
        self.analog_data = np.zeros((self.ai_channels, self.total_length), dtype=np.float64)
        self.ai_read = int32()
        self.samps_per_chan_written = int32()

        # set up data buffers (digital)
        self.write = Util.binary_to_digital_map(write)
        self.samps_per_chan = self.write.shape[1]
        self.write = np.sum(self.write, axis=0)

        # data pointer to make callback happy
        self.data_pointer = create_callbackdata_id(self.analog_data)

        # set up tasks
        DAQmxCreateTask('', byref(self.ai_handle))
        DAQmxCreateTask('', byref(self.do_handle))

        DAQmxCreateAIVoltageChan(self.ai_handle, ai_device, '', DAQmx_Val_Diff, -10.0, 10.0, DAQmx_Val_Volts, None)
        DAQmxCreateDOChan(self.do_handle, do_device, '', DAQmx_Val_ChanForAllLines)

        DAQmxCfgSampClkTiming(self.ai_handle, '', samp_rate, DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, self.total_length)
        DAQmxCfgSampClkTiming(self.do_handle, sync_clock, samp_rate, DAQmx_Val_Rising, DAQmx_Val_FiniteSamps,
                              self.total_length)

    def Callback(self, handle, every_n_samples_event_type, n_samples, data_pointer):
        self.callback_counter += 1
        data_of_interest = self.analog_data[0][0:(self.samps_per_callback * self.callback_counter)]
        print(data_of_interest.shape)
        print(np.sum(data_of_interest))

        current_pos = self.samps_per_callback * self.callback_counter
        response_window = data_of_interest[(current_pos - self.response_length):current_pos]
        print(response_window.shape)

        if current_pos >= self.response_start:
            response = self.AnalyseLicks(response_window, 2, self.lick_fraction)
            if response:
                print('animal licked')
                DAQmxTaskControl(self.ai_handle, DAQmx_Val_Task_Abort)
                # self.ClearTasks()
                return 0

        # if self.callback_counter > 5:
        #     print('stopping')
        #     DAQmxTaskControl(self.ai_handle, DAQmx_Val_Task_Abort)
        #     # self.ClearTasks()
        #     return 0


        return 0

    def DoTask(self):
        # Define and register callback function
        EveryNCallback = DAQmxEveryNSamplesEventCallbackPtr(self.Callback)
        DAQmxRegisterEveryNSamplesEvent(self.ai_handle, DAQmx_Val_Acquired_Into_Buffer, self.samps_per_callback,
                                       0, EveryNCallback, self.data_pointer)

        # Start tasks
        DAQmxWriteDigitalU32(self.do_handle, self.samps_per_chan, 0, -1, DAQmx_Val_GroupByChannel, self.write,
                             byref(self.samps_per_chan_written), None)

        DAQmxStartTask(self.do_handle)
        DAQmxStartTask(self.ai_handle)
        try:
            DAQmxReadAnalogF64(self.ai_handle, self.total_length, -1, DAQmx_Val_GroupByChannel, self.analog_data,
                               np.uint32(self.ai_channels * self.total_length), byref(self.ai_read), None)
        except:
            pass


        # self.ClearTasks()
        return self.analog_data

    def AnalyseLicks(self, lick_data, threshold, percent_accepted):
        # first binarise the data
        lick_response = np.zeros(self.response_length)
        lick_response[lick_data > threshold] = 1
        # then determine percentage responded
        percent_responded = np.sum(lick_response) / len(lick_response)
        # return whether this is accepted as a response or not
        return percent_responded >= percent_accepted

    def ClearTasks(self):
        print('clearing tasks')
        DAQmxStopTask(self.ai_handle)
        DAQmxStopTask(self.do_handle)

        DAQmxClearTask(self.ai_handle)
        DAQmxClearTask(self.do_handle)


dummy_write = np.zeros((1, 10000), dtype=np.uint32)

task = DoAiCallbackTask("Mod2/ai3", 1, "Mod1/port0/line0", 10000, 10, dummy_write, '/cDAQ/ai/SampleClock', 10000, 2, 2, 0.1)
read = task.DoTask()

plt.plot(read[0])
plt.show()