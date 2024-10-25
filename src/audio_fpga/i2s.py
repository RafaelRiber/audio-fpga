from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.cdc import FFSynchronizer
from amaranth.lib.wiring import In, Out

class I2S_clocks(wiring.Component):
    en : In(1)
    mclk : Out(1)
    sclk : Out(1)
    ws : Out(1)
    def __init__(self, f_sample=44100, mclk_sclk_ratio=4, sclk_ws_ratio=64):
        self.f_sample = f_sample
        self.mclk_sclk_ratio = mclk_sclk_ratio
        self.sclk_ws_ratio = sclk_ws_ratio
        super().__init__()

    def elaborate(self, platform):
        m = Module()

        m.domains.mclk = cd_mclk = ClockDomain(local=True)

        sclk_count = Signal(range(self.mclk_sclk_ratio+1))
        sclk_ovf = Signal()

        ws_count = Signal(range((2*self.mclk_sclk_ratio * self.sclk_ws_ratio) + self.mclk_sclk_ratio))

        ws_ovf = Signal()
        
        # TODO: Fix the overflows so that everything is aligned
        m.d.comb += self.mclk.eq(cd_mclk.clk)
        m.d.comb += sclk_ovf.eq(sclk_count == 2*sclk_count.shape().width-1) 
        m.d.comb += ws_ovf.eq(ws_count == (2*self.mclk_sclk_ratio * self.sclk_ws_ratio) + self.mclk_sclk_ratio)


        with m.If(self.en):
            m.d.mclk += sclk_count.eq(sclk_count + 1)
            m.d.mclk += ws_count.eq(ws_count + 1)
            with m.If(sclk_ovf):
                m.d.mclk += sclk_count.eq(0)
                m.d.mclk += self.sclk.eq(~self.sclk)
            with m.If(ws_ovf):
                m.d.mclk += ws_count.eq(0)
                m.d.mclk += self.ws.eq(~self.ws)




        return m


