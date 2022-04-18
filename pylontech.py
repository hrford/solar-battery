import serial
import construct


class HexToByte(construct.Adapter):
    def _decode(self, obj, context, path) -> bytes:
        hexstr = ''.join([chr(x) for x in obj])
        return bytes.fromhex(hexstr)


class JoinBytes(construct.Adapter):
    def _decode(self, obj, context, path) -> bytes:
        return ''.join([chr(x) for x in obj]).encode()


class DivideBy1000(construct.Adapter):
    def _decode(self, obj, context, path) -> float:
        return obj / 1000


class DivideBy100(construct.Adapter):
    def _decode(self, obj, context, path) -> float:
        return obj / 100


class ToVolt(construct.Adapter):
    def _decode(self, obj, context, path) -> float:
        return obj / 1000

class ToAmp(construct.Adapter):
    def _decode(self, obj, context, path) -> float:
        return obj / 10

class ToCelsius(construct.Adapter):
    def _decode(self, obj, context, path) -> float:
        return (obj / 10) - 273.1



class Pylontech:
    manufacturer_info_fmt = construct.Struct(
        "DeviceName" / JoinBytes(construct.Array(10, construct.Byte)),
        "SoftwareVersion" / construct.Array(2, construct.Byte),
        "ManufacturerName" / JoinBytes(construct.GreedyRange(construct.Byte)),
    )

    system_parameters_fmt = construct.Struct(
        "CellHighVoltageLimit" / ToVolt(construct.Int16ub),
        "CellLowVoltageLimit" / ToVolt(construct.Int16ub),
        "CellUnderVoltageLimit" / ToVolt(construct.Int16sb),
        "ChargeHighTemperatureLimit" / ToCelsius(construct.Int16sb),
        "ChargeLowTemperatureLimit" / ToCelsius(construct.Int16sb),
        "ChargeCurrentLimit" / DivideBy100(construct.Int16sb),
        "ModuleHighVoltageLimit" / ToVolt(construct.Int16ub),
        "ModuleLowVoltageLimit" / ToVolt(construct.Int16ub),
        "ModuleUnderVoltageLimit" / ToVolt(construct.Int16ub),
        "DischargeHighTemperatureLimit" / ToCelsius(construct.Int16sb),
        "DischargeLowTemperatureLimit" / ToCelsius(construct.Int16sb),
        "DischargeCurrentLimit" / DivideBy100(construct.Int16sb),
    )

    management_info_fmt = construct.Struct(
        "CommandValue" / construct.Byte,
        "ChargeVoltageLimit" / construct.Array(2, construct.Byte),
        "DischargeVoltageLimit" / construct.Array(2, construct.Byte),
        "ChargeCurrentLimit" / construct.Array(2, construct.Byte),
        "DishargeCurrentLimit" / construct.Array(2, construct.Byte),
        "Status" / construct.Byte,
    )

    module_serial_number_fmt = construct.Struct(
        "CommandValue" / construct.Byte,
        "ModuleSerialNumber" / JoinBytes(construct.Array(16, construct.Byte)),
    )


    get_values_fmt = construct.Struct(
        "NumberOfModules" / construct.Byte,
        "Module" / construct.Array(construct.this.NumberOfModules, construct.Struct(
            "NumberOfCells" / construct.Int8ub,
            "CellVoltages" / construct.Array(construct.this.NumberOfCells, ToVolt(construct.Int16sb)),
            "NumberOfTemperatures" / construct.Int8ub,
            "AverageBMSTemperature" / ToCelsius(construct.Int16sb),
            "GroupedCellsTemperatures" / construct.Array(construct.this.NumberOfTemperatures - 1, ToCelsius(construct.Int16sb)),
            "Current" / ToAmp(construct.Int16sb),
            "Voltage" / ToVolt(construct.Int16ub),
            "Power" / construct.Computed(construct.this.Current * construct.this.Voltage),
            "RemainingCapacity" / DivideBy1000(construct.Int16ub),
            "UserDefinedItems" / construct.Int8ub,
            "TotalCapacity" / DivideBy1000(construct.Int16ub),
            "CycleNumber" / construct.Int16ub,
            "US3000" / construct.If(construct.this.UserDefinedItems > 2,
                "Capacity" / construct.Struct(
                    "Remaining" / DivideBy1000(construct.Int24ub),
                    "Total" / DivideBy1000(construct.Int24ub),
                )
            ),
        )),
        "TotalPower" / construct.Computed(lambda this: sum([x.Power for x in this.Module])),
        "StateOfCharge" / construct.Computed(
            lambda this: sum([x.RemainingCapacity for x in this.Module]) / sum([x.TotalCapacity for x in this.Module])
        ),
        #"US3000Debug" / construct.Computed(lambda this: [x.US3000 for x in this.Module]),
        "StateOfChargeUS3000" / construct.Computed(
            lambda this: sum([x.US3000.Remaining for x in this.Module]) / sum([x.US3000.Total for x in this.Module])
        ),
    )

    def __init__(self, serial_port='/dev/ttyUSB0', baudrate=115200):
        #self.s = serial.Serial(serial_port, baudrate, bytesize=8, parity=serial.PARITY_NONE, stopbits=1, timeout=2)
        return


    @staticmethod
    def get_frame_checksum(frame: bytes):
        assert isinstance(frame, bytes)

        sum = 0
        for byte in frame:
            sum += byte
        sum = ~sum
        sum %= 0x10000
        sum += 1
        return sum

    @staticmethod
    def get_info_length(info: bytes) -> int:
        lenid = len(info)
        if lenid == 0:
            return 0

        lenid_sum = (lenid & 0xf) + ((lenid >> 4) & 0xf) + ((lenid >> 8) & 0xf)
        lenid_modulo = lenid_sum % 16
        lenid_invert_plus_one = 0b1111 - lenid_modulo + 1

        return (lenid_invert_plus_one << 12) + lenid


    def send_cmd(self, address: int, cmd, info: bytes = b''):
        raw_frame = self._encode_cmd(address, cmd, info)
        self.s.write(raw_frame)


    def _encode_cmd(self, address: int, cid2: int, info: bytes = b''):
        cid1 = 0x46

        info_length = Pylontech.get_info_length(info)

        frame = "{:02X}{:02X}{:02X}{:02X}{:04X}".format(0x20, address, cid1, cid2, info_length).encode()
        frame += info

        frame_chksum = Pylontech.get_frame_checksum(frame)
        whole_frame = (b"~" + frame + "{:04X}".format(frame_chksum).encode() + b"\r")
        return whole_frame


    def _decode_hw_frame(self, raw_frame: bytes) -> bytes:
        # XXX construct
        frame_data = raw_frame[1:len(raw_frame) - 5]
        frame_chksum = raw_frame[len(raw_frame) - 5:-1]

        got_frame_checksum = Pylontech.get_frame_checksum(frame_data)
        assert got_frame_checksum == int(frame_chksum, 16)

        return frame_data

    def _decode_frame(self, frame):
        format = construct.Struct(
            "ver" / HexToByte(construct.Array(2, construct.Byte)),
            "adr" / HexToByte(construct.Array(2, construct.Byte)),
            "cid1" / HexToByte(construct.Array(2, construct.Byte)),
            "cid2" / HexToByte(construct.Array(2, construct.Byte)),
            "infolength" / HexToByte(construct.Array(4, construct.Byte)),
            "info" / HexToByte(construct.GreedyRange(construct.Byte)),
        )

        return format.parse(frame)


    def read_frame(self):
        raw_frame = self.s.readline()
        print("raw_frame:", raw_frame)
        f = self._decode_hw_frame(raw_frame=raw_frame)
        parsed = self._decode_frame(f)
        return parsed

    def get_debug_frame(self, raw_frame):
        f = self._decode_hw_frame(raw_frame=raw_frame)
        parsed = self._decode_frame(f)
        return parsed

    def get_protocol_version(self):
        self.send_cmd(0, 0x4f)
        return self.read_frame()


    def get_manufacturer_info(self):
        self.send_cmd(0, 0x51)
        f = self.read_frame()
        return self.manufacturer_info_fmt.parse(f.info)


    def get_system_parameters(self):
        #self.send_cmd(2, 0x47)
        #f = self.read_frame()
        f = self.get_debug_frame(b'~20024600B032110E420BEA0B540D0D0A3D03FCD2F0B3B0ADD40D0D0A3DFC18F23D\r')
        return self.system_parameters_fmt.parse(f.info[1:])

    def get_management_info(self):
        raise Exception('Dont touch this for now')
        self.send_cmd(2, 0x92)
        f = self.read_frame()

        print(f.info)
        print(len(f.info))
        ff = self.management_info_fmt.parse(f.info)
        print(ff)
        return ff

    def get_module_serial_number(self):
        self.send_cmd(2, 0x93)
        f = self.read_frame()
        # infoflag = f.info[0]
        return self.module_serial_number_fmt.parse(f.info[0:])

    def get_values(self):
        #self.send_cmd(2, 0x42, b'FF')
        #f = self.read_frame()
        #f = self.get_debug_frame(b'~20024600F07A11010F0DC00DCF0DD10DD00DD00DCF0DD00DD00DD90DD80DD70DD80DD70DD70DD6050B730B4B0B4B0B4B0B4B0002CF53FFFF04FFFF009A012110012110E209\r')
        f = self.get_debug_frame(b'~2002460061DC11040F0CFD0CFC0CFC0CFB0CFC0CFB0CFD0CFC0CFC0CFB0CFA0CFD0CFB0CFE0CFA050BE10BCD0BCD0BCD0BCD0000C2C1FFFF04FFFF002F00EFEC0121100F0CEB0CEB0CEB0CEA0CEA0CEC0CEB0CEB0CE90CE80CE60CE90CE90CEA0CE8050BE10BCD0BCD0BCD0BCDFFBCC1B2FFFF04FFFF002800F2D00121100F0CE80CE90CEA0CEA0CEA0CE90CEA0CEA0CEB0CEC0CEB0CEB0CEB0CEA0CEA050BE10BC30BC30BC30BC3FFB7C1B8FFFF04FFFF007100E7400121100F0CE90CEC0CEB0CEA0CEA0CEB0CE90CE80CEA0CEA0CEA0CEB0CEC0CEA0CEA050BD70BC30BC30BC30BB9FFBBC1B9FFFF04FFFF006B00ED080121108D63\r')

        # infoflag = f.info[0]
        d = self.get_values_fmt.parse(f.info[1:])
        return d


if __name__ == '__main__':
    p = Pylontech()
    # print(p.get_protocol_version())
    # print(p.get_manufacturer_info())
    # print(p.get_system_parameters())
    # print(p.get_management_info())
    # print(p.get_module_serial_number())
    print(p.get_values())

