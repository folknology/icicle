#!/usr/bin/env python3

from argparse import ArgumentParser

from amaranth.build import Resource, Pins, Attrs
from amaranth_boards.ice40_up5k_b_evn import ICE40UP5KBEVNPlatform

from icicle.soc.enumeratable import EnumerateSoc
from icicle.soc.ice40_spram import ICE40SPRAM
from icicle.soc.flash import Flash
from icicle.soc.soc import SystemOnChip
from icicle.soc.gpio import GPIO
from icicle.soc.uart import UART


def main():
    parser = ArgumentParser()
    # parser.add_argument(
    #     "--flash",
    #     default=False,
    #     action="store_true",
    #     help="flash the bitstream to the board after building"
    # )
    args = parser.parse_args()

    platform = ICE40UP5KBEVNPlatform()
    platform.add_resources([
        Resource("gpio", 0, Pins("39"), Attrs(IO_STANDARD="SB_LVCMOS")),
        Resource("gpio", 1, Pins("40"), Attrs(IO_STANDARD="SB_LVCMOS")),
        Resource("gpio", 2, Pins("41"), Attrs(IO_STANDARD="SB_LVCMOS")),
    ])

    peripherals = {
        "leds": GPIO(numbers=range(3)),
        "uart0": UART()
    }
    memory = {
        "flash": Flash(addr_width=22),
        "ram": ICE40SPRAM(addr_width=17)
    }

    soc = SystemOnChip(peripherals, memory)
    SocSer = EnumerateSoc("vendor", "socname", soc)
    SocSer.svd_out("./soc.svd")
    SocSer.mem_out("./")
    platform.build(soc, nextpnr_opts="--timing-allow-fail", do_program=True)


if __name__ == "__main__":
    main()

        