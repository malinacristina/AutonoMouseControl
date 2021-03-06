import serial


def check_rfid(port, n):
    ser = serial.Serial(port,
                        baudrate=9600,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,
                        timeout=2)

    ser.write(b'RAT\r\n')
    rfid = ser.read(size=n)

    if not rfid:
        rfid = b'default'
    ser.close()
    try:
        out = rfid.decode()
    except:
        rfid = b'default'
        out = rfid.decode()
    return out
