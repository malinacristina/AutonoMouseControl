import HelperFunctions.RFID as port
import serial
from PyDAQmx import *
from PyDAQmx.DAQmxCallBack import *
import numpy as np
from ctypes import *
import daqface.DAQ as daq

#ser = serial.Serial('COM8',
                   # baudrate=9600,
                   # parity=serial.PARITY_NONE,
                  #  stopbits=serial.STOPBITS_ONE,
                  #  bytesize=serial.EIGHTBITS,
                   # timeout=3)

# code = ser.read(size=8)

# print(code)

#ser.write(b'RAT\r\n')
#print(ser.read(size=16))
# print(ser.readline())

#ser.close()


dummy_write = np.zeros((1, 60000), dtype=np.uint32)

run = True

while run:

    task = daq.DoAiCallbackTask("Mod2/ai3", 1, "Mod1/port0/line0", 10000, 6, dummy_write, '/cDAQ/ai/SampleClock', 1000, 2, 1.5, 0.1, 0)
    read = task.DoTask()
    print(sum(read[0]))
