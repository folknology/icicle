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
        self.soc = soc

    # TODO: add linker file generator memory.x
    def svd_out(self, filePath):
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
                             "baseAddress").text = hex(self.soc.memmap[2] + peripheral.address )
            etree.SubElement(peripheralElement, "groupName").text = "PCSR"

            offset = 0

            registers = etree.SubElement(peripheralElement, registertag + 's')
            # TODO: resources may have a collection/iterator which might be preferable here, thi feels a little dirty
            for _id, (elem, _name, _address) in peripheral._mux._map._resources.items():
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
                    peripheral._mux._map.data_width)  # str(elem.width)
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

                offset += peripheral._mux._map.data_width // 8

        with open(filePath, 'w', encoding="utf-8") as f:
            # etree.indent(device)
            # svd = etree.ElementTree(device)
            # svd.write(f, xml_declaration=True, pretty_print=True, encoding="utf-8")
            f.write(etree.tostring(device, xml_declaration=True,
                    pretty_print=True).decode("utf-8"))
    

    def mem_out(self, memdir):
        with open(memdir + "link.x", "r") as lx:
            with open(memdir + "memory.x", "w") as mx:
                links = lx.read() # read everything in the file
                mx.seek(0) # rewind
                mx.write(" MEMORY {\n")
                mx.write(f'    FLASH (rx)      : ORIGIN = {hex(self.soc.flash_offset)}, LENGTH = {hex(self.soc.flash_size)}\n', )
                mx.write(f'    RAM (xrw)       : ORIGIN = {hex(self.soc.memmap[1])}, LENGTH = {hex(self.soc.ram_size)}\n', )
                mx.write("}\n\n" + links)

            