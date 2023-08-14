from lxml import etree

class Enumeratable:
    address = None

class EnumerateSoc:
    def __init__(self, vendor, socname, soc):
        self.config = {
            "vendor": vendor,
            "name": socname,
            "addressUnitBits": "8",
            "width": "32",
            "size": "32",
            "resetValue": "0x00000000",
            "resetMask": "0xFFFFFFFF"
        }
        self.registers = {
            "output": "read-write",
            "oenable": "read-write",
            "input": "read-write"
        }
        self.soc = soc

    # TODO: add linker file generator memory.x
    def output(self, filePath):
        peripheraltag = "peripheral"
        registertag = "register"
        fieldtag = "field"
        offset = 0
        device = etree.Element("device")
        for tag, val in self.config.items():
            etree.SubElement(device, tag).text = val

        peripherals = etree.SubElement(device, peripheraltag + 's')
        for name, peripheral in self.soc.peripherals.items():
            peripheralElement = etree.SubElement(peripherals, peripheraltag)
            etree.SubElement(peripheralElement, "name").text = name
            etree.SubElement(peripheralElement,
                             "baseAddress").text = hex(peripheral.address)
            etree.SubElement(peripheralElement, "groupName").text = "PCSR"

            offset = 0

            registers = etree.SubElement(peripheralElement, registertag + 's')
            for _id, (elem, _name, _address) in peripheral._mux._map._resources.items():
            # for csrbank, _addr, _alignment in peripheral._csr_banks:
                # for elem, addr, alignment in csrbank._csr_regs:
                # for register, access in self.registers.items():
                width = elem.width - 1
                access = ""
                if elem.access.readable():
                    access += "read"
                    if elem.access.writable():
                        access += "-write"
                    else:
                        access += "-only"
                elif elem.access.writable():
                    access += "write-only"

                registerElement = etree.SubElement(registers, registertag)
                etree.SubElement(registerElement, "name").text = elem.name
                etree.SubElement(
                    registerElement, "description").text = elem.name + " of csr"
                etree.SubElement(
                    registerElement, "addressOffset").text = hex(offset)
                etree.SubElement(
                    registerElement, "resetValue").text = hex(0)
                etree.SubElement(registerElement, "size").text = str(
                    32)  # str(elem.width)
                etree.SubElement(registerElement, "access").text = access
                # fields = registerElement.append(etree.Element(registerElement))
                fields = etree.SubElement(registerElement, fieldtag + 's')
                fieldElement = etree.SubElement(fields, fieldtag)
                etree.SubElement(fieldElement, "name").text = elem.name
                etree.SubElement(
                    fieldElement, "msb").text = str(elem.width)
                if elem.width > 1:
                    etree.SubElement(
                        fieldElement, "bitRange").text = '[' + str(width) + ':0]'
                etree.SubElement(fieldElement, "lsb").text = str(0)

                offset += 4

        with open(filePath, 'w', encoding="utf-8") as f:
            # etree.indent(device)
            # svd = etree.ElementTree(device)
            # svd.write(f, xml_declaration=True, pretty_print=True, encoding="utf-8")
            f.write(etree.tostring(device, xml_declaration=True,
                    pretty_print=True).decode("utf-8"))
            