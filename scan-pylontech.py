import pylontech

p = pylontech.Pylontech(serial_port="/dev/ttyUSB0")

def main():
    #print("prot_ver:", p.get_protocol_version())
    #print("manf_info:", p.get_manufacturer_info())
    print("sys_params:", p.get_system_parameters())
    #print("serial:", p.get_module_serial_number())
    print("values:", p.get_values())

if __name__ == "__main__":
    print("Mendip Pylontech US3000 scanner")
    main()

