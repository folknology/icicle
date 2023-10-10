from lxml import etree

from amaranth import *
from amaranth_soc.csr.bus import Decoder as CSRDecoder
from amaranth_soc.csr.wishbone import WishboneCSRBridge
from amaranth_soc.wishbone import Arbiter as WishboneArbiter, Decoder as WishboneDecoder


from icicle.cpu import CPU
from icicle.soc.flash import Flash
from icicle.soc.ice40_spram import ICE40SPRAM
from icicle.soc.gpio import GPIO
from icicle.soc.uart import UART

# TODO:change filename and class of this
class Mappable:
    address = None
    size = None

class FlashMapped(Flash, Mappable):
    def __init__(self, addr_width, number=0, address=0x00000000, offset=0x00100000):
        super().__init__(addr_width, number)
        self.address = address
        self.size = 2**addr_width

class SpramMapped(ICE40SPRAM, Mappable):
    def __init__(self, addr_width, address=0x40000000):
        super().__init__()
        self.address = address
        self.size = 2**addr_width

class GpioMapped(GPIO, Mappable):
    def __init__(self, numbers, addr_width=None):
        super().__init__(numbers, addr_width)
        
class UartMapped(UART, Mappable):
    def __init__(self, number=0, fifo_depth=513, default_baud=9600):
        super().__init__(number, fifo_depth, default_baud)
 

class GenSoc(Elaboratable):
    def __init__(self, peripherals=None, memory=None,
                 addr_width=30, data_width=32, granularity=8, features=["err"], 
                 peripheral_address=0x80000000, reset_vector=0x00100000, trap_vector=0x00100000
                 ):

        self.peripheral_address = peripheral_address
        self.reset_vector = reset_vector
        self.cpu = CPU(reset_vector, trap_vector)
        self.peripherals = peripherals
        self.memory = memory
        
        self.csr_decoder = CSRDecoder(addr_width=16, data_width=8)
        self._configure_peripherals()
        
        self.bridge = WishboneCSRBridge(self.csr_decoder.bus, data_width=data_width)
        self.decoder = WishboneDecoder(addr_width=addr_width, data_width=data_width, granularity=granularity, features=features)
        self._configure_memory()
        self.decoder.add(self.bridge.wb_bus, addr=self.peripheral_address)
        self.arbiter = WishboneArbiter(addr_width=addr_width, data_width=data_width, granularity=granularity, features=features)
        self.arbiter.add(self.cpu.ibus)
        self.arbiter.add(self.cpu.dbus)

    def _configure_memory(self):
        # TODO: remove this for external memory paramaterisation
        if self.memory is None:
            self.memory = {
                "flash": FlashMapped(addr_width=22),
                "ram": SpramMapped(addr_width=17)
            }

        for _name, memory in self.memory.items(): 
            self.decoder.add(memory.bus, addr=memory.address)

        print("Memory:")   
        for name, memory in self.memory.items(): 
            print(f'{name}: {hex(memory.address)}, {hex(memory.size)}')

    
    
    def _configure_peripherals(self):
        # TODO: remove this for external peripherap paramaterisation
        if self.peripherals is None:
            self.peripherals = {
                "leds": GpioMapped(numbers=range(3)),
                "uart0": UartMapped(),
            }

        last_peripheral = None
        for _name, peripheral in self.peripherals.items(): 
            address = self.csr_decoder._map._next_addr
            if peripheral.address is None:
                peripheral.address = self.peripheral_address + address
            if peripheral.size is None and last_peripheral is not None:
                last_peripheral.size = peripheral.address - 1 - last_peripheral.address
            
            last_peripheral = peripheral
            self.csr_decoder.add(peripheral.bus, addr=address)
        last_peripheral.size = self.peripheral_address + self.csr_decoder._map._next_addr - 1 - last_peripheral.address
        
        print("Peripherals:")
        for name, peripheral in self.peripherals.items(): 
            print(f'{name}: {hex(peripheral.address)}, {hex(peripheral.size)}')

        
    def elaborate(self, platform):
        m = Module()

        m.submodules.cpu = self.cpu

        # m.submodules.flash = self.flash
        # m.submodules.ram = self.ram
        for _name, memory in self.memory.items():
            m.submodules +=  memory

        for _name, peripheral in self.peripherals.items():
            m.submodules += peripheral 

        m.submodules.csr_decoder = self.csr_decoder
        m.submodules.csr_bridge = self.bridge

        m.submodules.decoder = self.decoder

        m.submodules.arbiter = self.arbiter
        m.d.comb += self.arbiter.bus.connect(self.decoder.bus)

        return m
    



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
                             "baseAddress").text = hex(peripheral.address)
            etree.SubElement(peripheralElement, "groupName").text = "PCSR"

            offset = 0

            registers = etree.SubElement(peripheralElement, registertag + 's')
            # TODO: resources may have a collection/iterator which might be preferable here, thi feels a little dirty
            for _id, (elem, _name, _address) in peripheral._mux._map._resources.items():
                width = elem.width - 1
                word_bits = peripheral._mux._map.data_width
                words = (elem.width + word_bits -
                         1) // word_bits

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
                    words * word_bits)  # str(elem.width)
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

                offset += words  # TODO: assumption word_bits = 8 ??

        with open(filePath, 'w', encoding="utf-8") as f:
            # etree.indent(device)
            # svd = etree.ElementTree(device)
            # svd.write(f, xml_declaration=True, pretty_print=True, encoding="utf-8")
            f.write(etree.tostring(device, xml_declaration=True,
                    pretty_print=True).decode("utf-8"))

    def mem_out(self, memdir):
        with open(memdir + "link.x", "r") as lx:
            with open(memdir + "memory.x", "w") as mx:
                links = lx.read()  # read everything in the file
                mx.seek(0)  # rewind
                mx.write(" MEMORY {\n")
                mx.write(
                    f'    FLASH (rx)      : ORIGIN = {hex(self.soc.reset_vector)}, LENGTH = {hex(self.soc.memory["flash"].size)}\n', )
                mx.write(
                    f'    RAM (xrw)       : ORIGIN = {hex(self.soc.memory["ram"].address)}, LENGTH = {hex(self.soc.memory["ram"].size)}\n', )
                mx.write("}\n\n" + links)
