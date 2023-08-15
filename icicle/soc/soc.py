from amaranth import *
from amaranth_soc.csr.bus import Decoder as CSRDecoder
from amaranth_soc.csr.wishbone import WishboneCSRBridge
from amaranth_soc.wishbone import Arbiter as WishboneArbiter, Decoder as WishboneDecoder


from icicle.cpu import CPU
from icicle.soc.flash import Flash
from icicle.soc.gpio import GPIO
from icicle.soc.ice40_spram import ICE40SPRAM
from icicle.soc.uart import UART
from icicle.soc.enumeratable import EnumerateSoc

class SystemOnChip(Elaboratable):
    def __init__(self, peripherals=None, addr_width=30, data_width=32, granularity=8, features=["err"], flash_addr_width=22, ram_addr_width=17, reset_vector=0x00100000, trap_vector=0x00100000):
        self.flash_size = 2**flash_addr_width
        self.ram_size = 2**ram_addr_width
        self.flash_offset = 0x00100000
        self.memmap = (0x00000000, 0x40000000, 0x80000000)
        self.cpu = CPU(reset_vector, trap_vector)
        self.flash = Flash(addr_width=flash_addr_width)
        self.peripherals = peripherals
        self.ram = ICE40SPRAM()

        # TODO: remove this for external peripherap paramaterisation
        if peripherals is None:
            self.peripherals = {
                "leds": GPIO(numbers=range(3)),
                "uart1": UART()
            }
        
        self.csr_decoder = CSRDecoder(addr_width=16, data_width=8)
        for _name, peripheral in self.peripherals.items(): 
            if peripheral.address is None:
                peripheral.address = self.csr_decoder._map._next_addr
            self.csr_decoder.add(peripheral.bus, addr=peripheral.address)

        self.bridge = WishboneCSRBridge(self.csr_decoder.bus, data_width=data_width)
        self.decoder = WishboneDecoder(addr_width=addr_width, data_width=data_width, granularity=granularity, features=features)
        self.decoder.add(self.flash.bus,     addr=self.memmap[0])
        self.decoder.add(self.ram.bus,       addr=self.memmap[1])
        self.decoder.add(self.bridge.wb_bus, addr=self.memmap[2])
        self.arbiter = WishboneArbiter(addr_width=addr_width, data_width=data_width, granularity=granularity, features=features)
        self.arbiter.add(self.cpu.ibus)
        self.arbiter.add(self.cpu.dbus)

        SocSer = EnumerateSoc("vendor", "socname", self)
        SocSer.svd_out("./soc.svd")
        SocSer.mem_out("./")

        
    def elaborate(self, platform):
        m = Module()

        m.submodules.cpu = self.cpu

        m.submodules.flash = self.flash
        m.submodules.ram = self.ram

        for _name, peripheral in self.peripherals.items():
            m.submodules += peripheral 

        m.submodules.csr_decoder = self.csr_decoder
        m.submodules.csr_bridge = self.bridge

        m.submodules.decoder = self.decoder

        m.submodules.arbiter = self.arbiter
        m.d.comb += self.arbiter.bus.connect(self.decoder.bus)

        return m
    

