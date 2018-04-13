import HelperFunctions.RFID as port
import serial

ser = serial.Serial('COM8',
                    baudrate=9600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=3)

# code = ser.read(size=8)

# print(code)

ser.write(b'RAT\r\n')
print(ser.read(size=16))
# print(ser.readline())

ser.close()
