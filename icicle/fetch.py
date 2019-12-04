from nmigen import *

from icicle.loadstore import LoadStore, MemWidth
from icicle.pipeline import Stage
from icicle.pipeline_regs import PF_LAYOUT, FD_LAYOUT
from icicle.wishbone import WISHBONE_LAYOUT


class Fetch(Stage):
    def __init__(self):
        super().__init__(rdata_layout=PF_LAYOUT, wdata_layout=FD_LAYOUT)
        self.ibus = Record(WISHBONE_LAYOUT)

    def elaborate_stage(self, m, platform):
        load_store = m.submodules.load_store = LoadStore()
        m.d.comb += [
            load_store.bus.connect(self.ibus),
            load_store.valid.eq(self.valid),
            load_store.load.eq(1),
            load_store.width.eq(MemWidth.WORD),
            load_store.addr.eq(self.rdata.pc_rdata)
        ]
        self.stall_on(load_store.busy)
        self.trap_on((load_store.load | load_store.store) & (load_store.misaligned | load_store.fault))

        with m.If(~self.stall):
            m.d.sync += self.wdata.insn.eq(load_store.rdata)
