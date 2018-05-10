from PyDAQmx import *
from PyDAQmx.DAQmxCallBack import *
from ctypes import *
import daqface.Utils as Util
import numpy
import matplotlib.pyplot as plt
import time
import pandas as pd

class DoAiMultiTaskCallback:
    def __init__(self, ai_device, ai_channels, do_device, samp_rate, secs, write, sync_clock, lick_fraction, windowlength):
        # create tasks
        self.ai_handle = TaskHandle(0)
        self.do_handle = TaskHandle(1)
        self.ai_channels = ai_channels


        # self.analog_input = CallbackTask(ai_device, ai_channels, samp_rate, secs, lick_fraction, windowlength, self)
        # self.digital_output = Task()


        # self.ai_read = int32()
        self.data = numpy.zeros(1000)
        # self.analogData = []
        self.analogData = numpy.zeros((self.ai_channels, self.totalLength), dtype=numpy.float64)

        self.totalLength = numpy.int32(samp_rate * secs)
        self.triallength = secs * samp_rate
        self.windowlength = samp_rate * windowlength
        self.lick_fraction = lick_fraction


        self.sampsPerChanWritten = int32()
        self.read = int32()

        self.write = Util.binary_to_digital_map(write)
        self.sampsPerChan = self.write.shape[1]
        self.write = numpy.sum(self.write, axis=0)

        self.lick_data = []

        # data pointer for callback
        self.data_pointer = create_callbackdata_id(self.analogData)

        # set up tasks
        DAQmxCreateTask('', byref(self.ai_handle))
        DAQmxCreateTask('', byref(self.do_handle))

        # add channels
        DAQmxCreateDOChan(self.do_handle, do_device, "", DAQmx_Val_ChanForAllLines)
        DAQmxCreateAIVoltageChan(self.ai_handle, ai_device, "", DAQmx_Val_Cfg_Default, -10.0, 10.0, DAQmx_Val_Volts,
                                 None)

        # set up sync clock
        DAQmxCfgSampClkTiming(self.ai_handle, "", samp_rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, 1000)
        DAQmxCfgSampClkTiming(self.do_handle, sync_clock, samp_rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, 1000)


        # DAQmxRegisterDoneEvent(self.ai_handle, 0)

        # self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, 1000, 0)
        # self.AutoRegisterDoneEvent(0)

    def StartThisTask(self):

        # define and register callback
        EveryNCallback = DAQmxEveryNSamplesEventCallbackPtr(self.Callback)
        DAQmxRegisterEveryNSamplesEvent(self.ai_handle, DAQmx_Val_Acquired_Into_Buffer, 1000, 0, EveryNCallback,
                                        self.data_pointer)

        # print("Task has been triggered")

        DAQmxWriteDigitalU32(self.do_handle, self.sampsPerChan, 0, -1, DAQmx_Val_GroupByChannel, self.write,
                             byref(self.sampsPerChanWritten), None)

        DAQmxStartTask(self.do_handle)
        DAQmxStartTask(self.ai_handle)

        # print("Task has started")

        DAQmxReadAnalogF64(self.ai_handle, self.totalLength, -1, DAQmx_Val_GroupByChannel, self.data,
                           self.totalLength, byref(self.read), None)

    def Callback(self, handle, every_n_samples_event_type, n_samples, data_pointer):
        self.analogData.extend(self.data.tolist())
        # print("EveryNCallback is triggered")
        print(len(self.analogData))
        print(self.analogData)

        # if len(self.analogData) < 35000:
        #     print("More samples needed")

        # self.window = numpy.asarray(self.analogData)
        # self.response = self.AnalyseLicks(self.window, 2, self.lick_fraction)

        if len(self.analogData) >= 35000:  # shortest time it takes for odour to arrive (1.5s) + window length (2s)
            print(len(self.analogData))
            current_length = len(self.analogData)
            self.window = numpy.asarray(self.analogData[(current_length - self.windowlength):current_length])
            self.response = self.AnalyseLicks(self.window, 2, self.lick_fraction)
            if self.response:
                self.parent.CallbackComplete()
                print(self.response)
                # print(self.window)
            elif len(self.analogData) >= self.triallength:
                self.parent.CallbackComplete()
                print(self.response)
                # print(self.window)

        return 0  # The function should return an integer

    def DoneCallback(self, status):
        print("Status", status.value)
        return 0  # The function should return an integer

    def AnalyseLicks(self, lick_data, threshold, percent_accepted):
        # first binarise the data
        lick_response = numpy.zeros(self.windowlength)
        lick_response[lick_data > threshold] = 1
        # then determine percentage responded
        percent_responded = numpy.sum(lick_response) / len(lick_response)
        # return whether this is accepted as a response or not
        return percent_responded >= percent_accepted

    def CallbackComplete(self):
        self.lick_data = numpy.asarray(self.analogData)
        print(self.lick_data)
        self.StopAll()

    def StopAll(self):
        time.sleep(0.05)
        DAQmxStopTask(self.do_handle)
        DAQmxStopTask(self.ai_handle)
        DAQmxClearTask(self.do_handle)
        DAQmxClearTask(self.ai_handle)

task = DoAiMultiTaskCallback("Mod2/ai3", "", "Mod1/port0/line0", 10000.0, 6.0, numpy.zeros((1, 1000)), "/cDaQ/ai/SampleClock", 0.1, 2.0)
task.StartThisTask()
