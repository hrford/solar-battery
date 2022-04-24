import time

BANNER="Fake Pylontech serial:"
PARITY_NONE="PARITY_NONE"

class Serial(object):

    def __init__(self, serial_port, baudrate, bytesize=8, parity=PARITY_NONE, stopbits=1, timeout=5):
        print(BANNER, "init(serial_port={}, baudrate={}, bytesize={}, parity={}, stopbits={}, timeout={})".format(serial_port, baudrate, bytesize, parity, stopbits, timeout))

        self.out_buff = b''

        return

    def write(self, data):
        print(BANNER, "write(data={})".format(data))

        if data == b'~200246470000FDA7\r':
            self.out_buff += b'~20024600B032110E420BEA0B540D0D0A3D03FCD2F0B3B0ADD40D0D0A3DFC18F23D\r'
        elif data == b'~20024642E002FFFD09\r':
            #self.out_buff += b'~20024600F07A11010F0DC00DCF0DD10DD00DD00DCF0DD00DD00DD90DD80DD70DD80DD70DD70DD6050B730B4B0B4B0B4B0B4B0002CF53FFFF04FFFF009A012110012110E209\r'
            self.out_buff += b'~20024600F07A11010F0CEB0CEC0CEC0CEC0CEC0CEB0CED0CEC0CED0CEE0CEF0CEF0CED0CEF0CED050B7D0B550B550B550B55FFD7C1E1FFFF04FFFF009A011B48012110E103\r'
            #self.out_buff += b'~2002460061DC11040F0CFD0CFC0CFC0CFB0CFC0CFB0CFD0CFC0CFC0CFB0CFA0CFD0CFB0CFE0CFA050BE10BCD0BCD0BCD0BCD0000C2C1FFFF04FFFF002F00EFEC0121100F0CEB0CEB0CEB0CEA0CEA0CEC0CEB0CEB0CE90CE80CE60CE90CE90CEA0CE8050BE10BCD0BCD0BCD0BCDFFBCC1B2FFFF04FFFF002800F2D00121100F0CE80CE90CEA0CEA0CEA0CE90CEA0CEA0CEB0CEC0CEB0CEB0CEB0CEA0CEA050BE10BC30BC30BC30BC3FFB7C1B8FFFF04FFFF007100E7400121100F0CE90CEC0CEB0CEA0CEA0CEB0CE90CE80CEA0CEA0CEA0CEB0CEC0CEA0CEA050BD70BC30BC30BC30BB9FFBBC1B9FFFF04FFFF006B00ED080121108D63\r'

        # Vards0-2021-12-06 messages
        if data == b'~200146470000FDA8\r':
            self.out_buff += b'~20024600B032110E420BEA0B540D0D0A3D03FCD2F0B3B0ADD40D0D0A3DFC18F23D\r'


        return

    def read(self, num_bytes=1):
        write_data = self.out_buff[0:num_bytes]
        #print(BANNER, "read(num_bytes={}) return {}".format(num_bytes, write_data))
        #time.sleep(0.1)

        self.out_buff = self.out_buff[num_bytes:]
        return write_data

    def readline(self):
        write_data = self.out_buff
        print(BANNER, "readline() return {}".format(write_data))
        time.sleep(0.5)

        self.out_buff = b''
        return write_data
