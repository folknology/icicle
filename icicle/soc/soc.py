from amaranth import *
from amaranth_soc.csr.bus import Decoder as CSRDecoder
from amaranth_soc.csr.wishbone import WishboneCSRBridge
from amaranth_soc.wishbone import Arbiter as WishboneArbiter, Decoder as WishboneDecoder


from icicle.cpu import CPU
from icicle.soc.flash import Flash
from icicle.soc.gpio import GPIO
from icicle.soc.ice40_spram import ICE40SPRAM
from icicle.soc.uart import UART

class SystemOnChip(Elaboratable):
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
                "flash": Flash(addr_width=22),
                "ram": ICE40SPRAM(addr_width=17)
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
                "leds": GPIO(numbers=range(3)),
                "uart0": UART(),
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
    

