import numpy as np
from PyDAQmx import *
import pandas as pd


class CallbackTask(Task):
    def __init__(self):
        Task.__init__(self)
        self.data = np.zeros(1000)
        self.a = []
        self.CreateAIVoltageChan("Mod2/ai3", "", DAQmx_Val_Diff, -10.0, 10.0, DAQmx_Val_Volts, None)
        self.CfgSampClkTiming("", 10000.0, DAQmx_Val_Rising, DAQmx_Val_ContSamps, 1000)

        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, 1000, 0)
        self.AutoRegisterDoneEvent(0)

        self.windowlength = 20000
        self.triallength = 60000

    def EveryNCallback(self):
        read = int32()
        self.ReadAnalogF64(1000, 10.0, DAQmx_Val_GroupByChannel, self.data, 1000, byref(read), None)

        self.a.extend(self.data.tolist())

        if len(self.a) >= 35000:        # shortest time it takes for odour to arrive (1.5s) + window length (2s)
            print('a getting big', len(self.a))
            current_length = len(self.a)
            self.window = pd.Series(self.a[(current_length-self.windowlength):current_length])
            self.response = self.AnalyseLicks(self.window, 2, 0.1)
            if self.response:
                self.Complete()
                print(self.response)
                print(self.window)
            elif len(self.a) >= self.triallength:
                self.Complete()
                print(self.response)

        return 0 # The function should return an integer

    def DoneCallback(self, status):
        print("Status", status.value)
        return 0 # The function should return an integer

    def Complete(self):
        self.StopTask()
        self.ClearTask()

    def AnalyseLicks(self, lick_data, threshold, percent_accepted):
        # first binarise the data
        lick_response = pd.Series(np.zeros(self.windowlength))
        lick_response[lick_data > threshold] = 1
        # then determine percentage responded
        percent_responded = np.sum(lick_response) / len(lick_response)
        # return whether this is accepted as a response or not
        return percent_responded >= percent_accepted


task = CallbackTask()
task.StartTask()

input('Acquiring samples continuously. Press Enter to interrupt\n')

#task.StopTask()
#task.ClearTask()