#!/usr/bin/env python3

from argparse import ArgumentParser

from amaranth.build import Resource, Pins, Attrs
from amaranth_boards.ice40_up5k_b_evn import ICE40UP5KBEVNPlatform

from icicle.soc.soc import SystemOnChip


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
    platform.build(SystemOnChip(), nextpnr_opts="--timing-allow-fail", do_program=True)


if __name__ == "__main__":
    main()
