import numpy as np
from PyDAQmx import *
from ctypes import *
import daqface.Utils as Util
from daqface import *
import pandas as pd
from PyDAQmx.DAQmxCallBack import *
import weakref

class DoAiMultiTaskCallback:
    def __init__(self, ai_device, ai_channels, do_device, samp_rate, secs, write, sync_clock):
        self.ai_handle = TaskHandle(0)
        self.do_handle = TaskHandle(1)

        DAQmxCreateTask('', byref(self.ai_handle))
        DAQmxCreateTask('', byref(self.do_handle))

        DAQmxCreateAIVoltageChan(self.ai_handle, ai_device, '', DAQmx_Val_Diff, -10.0, 10.0, DAQmx_Val_Volts, None)
        DAQmxCreateDOChan(self.do_handle, do_device, '', DAQmx_Val_ChanForAllLines)

        self.datasnip = np.zeros(1000)

        self.ai_read = int32()
        self.ai_channels = ai_channels
        self.sampsPerChanWritten = int32()

        self.write = Util.binary_to_digital_map(write)
        self.sampsPerChan = self.write.shape[1]
        self.write = numpy.sum(self.write, axis=0)

        self.totalLength = numpy.uint64(samp_rate * secs)
        self.windowLength = samp_rate * 2.0 #widnow is 2s
        self.analogData = []

        DAQmxCfgSampClkTiming(self.ai_handle, '', samp_rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, 1000)
        DAQmxCfgSampClkTiming(self.do_handle, sync_clock, samp_rate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, 1000)

        # AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, 1000, 0)
        # AutoRegisterDoneEvent(0)

        DAQmxRegisterEveryNSamplesEvent(self.ai_handle, DAQmx_Val_Acquired_Into_Buffer,1000, 0, self.EveryNCallback, self.analogData)
        DAQmxRegisterDoneEvent(self.ai_handle, 0)

    # def AutoRegisterEveryNSamplesEvent(self, everyNsamplesEventType, nSamples, options, name='EveryNCallback'):
    #     """Register the method named name as the callback function for EveryNSamplesEvent
    #
    #
    #     With this method you can register a method of the class Task as a callback function.
    #     The parameters everyNsamplesEventType, nSamples and options are the same
    #     as the DAQmxRegisterEveryNSamplesEvent parameters
    #
    #     No parameters are passed to the method
    #
    #     If an event was already registered, the UnregisterEveryNSamplesEvent is automatically called
    #     """
    #     if self._EveryNSamplesEvent_already_register:
    #         self.UnregisterEveryNSamplesEvent()
    #     self_id = create_callbackdata_id(self)
    #
    #     # Define the python function
    #     def EveryNCallback_py(taskHandle, everyNsamplesEventType, nSamples, self_id):
    #         self = get_callbackdata_from_id(self_id)
    #         getattr(self, name)()
    #         return 0
    #
    #     # Transform the python function to a CFunction
    #     self.EveryNCallback_C = DAQmxEveryNSamplesEventCallbackPtr(EveryNCallback_py)
    #     # Register the function
    #     self.RegisterEveryNSamplesEvent(everyNsamplesEventType, nSamples, options, self.EveryNCallback_C, self_id)
    #     self._EveryNSamplesEvent_already_register = True
    #
    # def UnregisterEveryNSamplesEvent(self):
    #     self.RegisterEveryNSamplesEvent(1, 0, 0, ctypes.cast(None, DAQmxEveryNSamplesEventCallbackPtr), 0)
    #     self._EveryNSamplesEvent_already_register = False
    #
    # def AutoRegisterDoneEvent(self, options, name='DoneCallback'):
    #     """Register the method named name as the callback function for DoneEvent
    #
    #     With this method you can register a method of the class Task as a callback function.
    #     The parameter options is the same as the DAQmxRegisterDoneEvent parameters
    #
    #     The method registered has one parameter : status
    #     """
    #     self_id = create_callbackdata_id(self)
    #
    #     # Define the python function
    #     def DoneCallback_py(taskHandle, status, self_id):
    #         getattr(get_callbackdata_from_id(self_id), name)(status)
    #         return 0
    #
    #     # Transform the python function to a CFunction
    #     self.DoneCallback_C = DAQmxDoneEventCallbackPtr(DoneCallback_py)
    #     # Register the function
    #     self.RegisterDoneEvent(options, self.DoneCallback_C, self_id)

    def DoTask(self):
        DAQmxWriteDigitalU32(self.do_handle, self.sampsPerChan, 0, -1, DAQmx_Val_GroupByChannel, self.write,
                             byref(self.sampsPerChanWritten), None)

        DAQmxStartTask(self.do_handle)
        DAQmxStartTask(self.ai_handle)

       # DAQmxReadAnalogF64(self.ai_handle, self.totalLength, -1, DAQmx_Val_GroupByChannel, self.analogData,
        #                   numpy.uint32(self.ai_channels*self.totalLength), byref(self.ai_read), None)

        self.ClearTasks()
        return self.analogData


    def EveryNCallback(self):
        read = int32()
        DAQmxReadAnalogF64(self.ai_handle, 1000, 10.0, DAQmx_Val_GroupByChannel, self.datasnip, 1000, byref(read), None)

        self.analogData.extend(self.datasnip.tolist())

        if len(self.analogData) >= 1500 + self.windowLength:  # shortest time it takes for odour to arrive (1.5s) + window length (2s)
            print('a getting big', len(self.analogData))
            current_length = len(self.analogData)
            self.window = pd.Series(self.analogData[(current_length - self.windowLength):current_length])
            self.response = self.AnalyseLicks(self.window, 2, 0.1)
            if self.response:
                print(self.response)
                print(self.window)
                self.ClearTasks()
            elif len(self.analogData) >= self.totalLength:
                print(self.response)
                self.ClearTasks()

        return 0  # The function should return an integer


    def DoneCallback(self, status):
        print("Status", status.value)
        return 0  # The function should return an integer


    def AnalyseLicks(self, lick_data, threshold, percent_accepted):
        # first binarise the data
        lick_response = pd.Series(np.zeros(self.windowLength))
        lick_response[lick_data > threshold] = 1
        # then determine percentage responded
        percent_responded = np.sum(lick_response) / len(lick_response)
        # return whether this is accepted as a response or not
        return percent_responded >= percent_accepted

    def ClearTasks(self):
        time.sleep(0.05)
        DAQmxStopTask(self.do_handle)
        DAQmxStopTask(self.ai_handle)

        DAQmxClearTask(self.do_handle)
        DAQmxClearTask(self.ai_handle)

task = DoAiMultiTaskCallback("Mod2/ai3", "", "Mod1/port0/line0", 10000.0, 6.0, numpy.zeros((2, 1000)), "/cDaQ/ai/SampleClock")

task.DoTask()

input('Acquiring samples continuously. Press Enter to interrupt\n')
