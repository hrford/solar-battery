#! /usr/bin/python3

import sys
import pylonpacket
import logging
import serial
import time

import json
#import paho.mqtt.client as mqtt


class PylonCom:

    PORT = "/dev/ttyUSB1"
    BAUD = 115200

    def __init__(self):
        self.sp = serial.Serial(PylonCom.PORT,PylonCom.BAUD,timeout=0.5)

    def GetReply(self, request, reply_type):
        self.sp.write(request.GetAsciiBytes())
        line = bytearray()
        while True:
            c = self.sp.read(1)
            if c:
                line.extend(c)
                if c[0] == 0x0D:
                    break
            else:
                break
        logging.debug("Received sentence %s",line)
        preply = pylonpacket.PylonPacket.Parse(line, reply_type)
        return preply

    def close(self):
        self.sp.close()

def connect():
    global client
    # Needs to be adjusted to set where your MQTT server is found:
    #client = mqtt.Client(client_id="pylonbatteries")
    #client.username_pw_set('emonpi', 'emonpimqtt2016')
    #client.connect('10.1.1.32')
    
def send_data(data, topic):
    try:
        client.publish(topic, data)
    except Exception as e:
        print("error sending to emoncms...:" + str(e))
        return 0
    return 1

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    connect();
    pc = PylonCom()


    #for adr in range(0,255):
    #    ppIn = pylonpacket.PPGetVersionInfo()
    #    ppIn.ADR=adr
    #    ppOut=pc.GetReply(ppIn, pylonpacket.PPVersionInfo)
    #    if ppOut: print("Get protocol version reply:",ppOut)
    #return
    


    #ppIn=pylonpacket.PPGetManufacturerInfo()
    #print("Get manufacturer info:",ppIn)
    #ppOut=pc.GetReply(ppIn, pylonpacket.PPManufacturerInfo)
    #print("Get manufacturer info reply:",ppOut)

    batteries = []
    batteryInfo = {}

    print("*** Scanning for batteries")
    for adr in range(1,9):
#        print("*** Polling adress ", adr)
        ppIn = pylonpacket.PPGetSystemParameter()
        ppIn.Command = adr
        ppIn.ADR = adr
#        print("Get system parameter:",ppIn)
        ppSystemParams = pc.GetReply(ppIn, pylonpacket.PPSystemParameter)
        if not ppSystemParams is None:
            print("Get system parameter reply for address ", adr, ":",ppSystemParams)
            ppIn = pylonpacket.PPGetSeriesNumber()
            ppIn.Command = adr
            ppIn.ADR = adr
#            print("Get serial number:",ppIn)
            ppSerial = pc.GetReply(ppIn, pylonpacket.PPSeriesNumber)
            if not ppSerial is None:
                print("Get serial number reply for address ", adr, ":",ppSerial) #,ppOut.info.hex())
                batteries.append(adr)
                batteryInfo[adr] = { "adr": adr, "systemParams": ppSystemParams, "serialNumber": ppSerial }

    # Get system parameter reply for address  2 : VER: 0x20, ADR: 0x02, CID1: 0x46, CID2: 0x00, LENGTH: 50, len(INFO): 25, CHKSUM: 0xF224
    # >  FLAG: 0b10001, UnitCellVoltage: 3.7, UnitCellLowVoltage 3.05, UnitCellUnderVoltage: 2.9
    # Get serial number reply for address  2 : VER: 0x20, ADR: 0x02, CID1: 0x46, CID2: 0x00, LENGTH: 34, len(INFO): 17, CHKSUM: 0xF6C5
    # > Series Number: PPTBH02198838124

    print("*** We found batteries at:", batteries)
    print("*** BatteryInfo:", batteryInfo)

    if len(batteries) != 4:
        print("Quitting since we didn't find 4 batteries")
        exit(1)

    while True:
        start=time.time()
        for adr in batteries:
            print("Conecting to addr",adr)
            ppSystemParams = batteryInfo[adr]['systemParams']
            ppIn = pylonpacket.PPGetChargeManagementInformation()
            ppIn.Command = adr
            ppIn.ADR = adr
            #print("Get charge info:",ppIn)
            ppChargeInfo = pc.GetReply(ppIn, pylonpacket.PPChargeManagementInformation)
            print("Get charge info reply, addr", adr, ":", ppChargeInfo)

            if ppChargeInfo is None:
                continue

            #return

            ppIn = pylonpacket.PPGetAnalogValue()
            ppIn.Command = adr
            ppIn.ADR = adr
            print("Get analog:",ppIn)
            ppAnalogue = pc.GetReply(ppIn, pylonpacket.PPAnalogValue)
            print("Get analog reply, addr", adr, ":", ppAnalogue)

            if ppAnalogue is None:
                continue

            # Conecting to addr 2
            # Get charge info reply, addr 2 : 02d002b7980032ff06c0
            # VER: 0x20, ADR: 0x02, CID1: 0x46, CID2: 0x00, LENGTH: 20, len(INFO): 10, CHKSUM: 0xF94F
            # >  VoltageUpLimit: 53.25, VoltageDownLimit: 47.0, MaxChargeCurrent: 50.0, MaxDischargeCurrent: -250.0, Status: 0xc0
            # Get analog: VER: 0x20, ADR: 0x02, CID1: 0x46, CID2: 0x42, LENGTH: 2, len(INFO): 1, CHKSUM: 0x0000, Command: 2
            # Get analog reply, addr 2 : VER: 0x20, ADR: 0x02, CID1: 0x46, CID2: 0x00, LENGTH: 110, len(INFO): 55, CHKSUM: 0xE46E
            # >  CellsCount: 15, TemperaturesCount: 5
            # >  TotalCurrent: 0.000A, TotalVoltage: 52.456V, RemainingCapacity: 50.000Ah, P: 0.00
            # >  Quantity: 2, TotalCapacity: 50.0Ah, Cycles: 0
            # >  CellVoltages: [3.499, 3.498, 3.493, 3.494, 3.498, 3.483, 3.497, 3.498, 3.499, 3.5, 3.499, 3.499, 3.499, 3.501, 3.499]
            # >  Temperatures: [27.0, 25.0, 25.0, 25.0, 25.0]

            j = '{ '
            j += '"time":' + str(int(time.time()))
            j += ', "VoltageUpperLimit":' + str(ppChargeInfo.VoltageUpLimit)
            j += ', "VoltageLowerLimit":' + str(ppChargeInfo.VoltageDownLimit)
            j += ', "MaxChargeAmps":' + str(ppChargeInfo.MaxChargeCurrent)
            j += ', "MaxDischargeAmps":' + str(ppChargeInfo.MaxDischargeCurrent)
            j += ', "BatteryCycles":' + str(ppAnalogue.Cycles)
            j += ', "BatteryVoltage":' + str(ppAnalogue.TotalVoltage)
            j += ', "BatteryAmps":' + str(ppAnalogue.TotalCurrent)
            j += ', "BatteryWatts":' + str(ppAnalogue.TotalCurrent*ppAnalogue.TotalVoltage)
            j += ', "BatterySOC":' + str(ppAnalogue.RemainingCapacity*100.0/50.0)
            j += ', "RemainingAh":' + str(ppAnalogue.RemainingCapacity)
            j += ', "RemainingWh":' + str(int(ppAnalogue.RemainingCapacity*ppAnalogue.CellsCount*3.33))
            j += ', "MinutesToRun":' + ( '9999' if ppAnalogue.TotalCurrent >= 0 else str(int(ppAnalogue.RemainingCapacity*60/-ppAnalogue.TotalCurrent)) )
            j += ', "CellMaxVoltage":' + str(ppSystemParams.UnitCellVoltage)
            j += ', "CellLowVoltage":' + str(ppSystemParams.UnitCellLowVoltage)
            j += ', "CellUnderVoltage":' + str(ppSystemParams.UnitCellUnderVoltage)
            lowestCell = 99
            highestCell = 0
            cells = ppAnalogue.CellVoltages
            for cell in range(ppAnalogue.CellsCount):
                j += ', "cellVoltage' + str(cell) + '":' + str(cells[cell])
                if cells[cell] < lowestCell:
                    lowestCell = cells[cell]
                if cells[cell] > highestCell:
                    highestCell = cells[cell]
            j += ', "highestCellVoltage":' + str(highestCell)
            j += ', "lowestCellVoltage":' + str(lowestCell)
            imbalance = int( (highestCell/lowestCell - 1) * 1000) / 10.0
            j += ', "cellImbalancePct":' + str(imbalance)
            temps = ppAnalogue.Temperatures
            lowestTemp = 99
            highestTemp = 0
            for temp in range(ppAnalogue.TemperaturesCount):
                j += ', "temp' + str(temp) + '":' + str(temps[temp])
                if temps[temp] < lowestTemp:
                    lowestTemp = temps[temp]
                if temps[temp] > highestTemp:
                    highestTemp = temps[temp]
            j += ', "highestTemp":' + str(highestTemp)
            j += ', "lowestTemp":' + str(lowestTemp)
            j += ' }'
            print('Send ' + j + ' to emon/pylon' + str(batteryInfo[adr]['serialNumber'].SeriesNumber))
            send = send_data(j, 'emon/pylon' + str(batteryInfo[adr]['serialNumber'].SeriesNumber))
            time.sleep(1)

        print("")
        time.sleep(max(1,10-(time.time()-start)))

    #ppIn=pylonpacket.PPGetChargeManagementInformation()
    #ppIn.Command=0x02
    #print("Get charge info:",ppIn)
    #ppOut=pc.GetReply(ppIn, pylonpacket.PPChargeManagementInformation)
    #print("Get charge info reply:",ppOut)
      

    ppIn = pylonpacket.PPGetAlarmInformation()
    ppIn.Command = 0x02
    print("Get alarm info:",ppIn)
    ppOut = pc.GetReply(ppIn, pylonpacket.PPAlarmInformation)
    print("Get alarm info reply:",ppOut) #,ppOut.info.hex())

    
    ppIn = pylonpacket.PPTurnOff()
    ppIn.Command = 0x02
    print("Turn off:",ppIn)
    ppOut = pc.GetReply(ppIn, pylonpacket.PPTurnOffReply)
    print("Turn off reply:",ppOut)
    

if __name__ == "__main__":
    root = logging.getLogger()
    #root.setLevel(logging.DEBUG)
    main(sys.argv[1:])

