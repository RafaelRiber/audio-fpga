from amaranth import *
from amaranth.lib import wiring, stream
from amaranth.lib.cdc import FFSynchronizer
from amaranth.lib.wiring import In, Out

class I2S_clocks(wiring.Component):
    en : In(1)
    # clk : In(1)
    mclk : Out(1)
    sclk : Out(1)
    ws : Out(1) 

    # ws is the sample rate of the interface, set mclk_freq = f_s * mclk_sclk_ratio * sclk_ws_ratio
    # For example : f_sample = 44100 Hz --> mclk_freq = 44100 * 64 * 4 = 11.29 MHz
    def ports(self):
        return [self.mclk, self.sclk, self.ws]

    def __init__(self, mclk_sclk_ratio=4, sclk_ws_ratio=64):
        self.mclk_sclk_ratio = mclk_sclk_ratio
        self.sclk_ws_ratio = sclk_ws_ratio
        super().__init__()

    def elaborate(self, platform):
        m = Module()

        sclk_count = Signal(range(self.mclk_sclk_ratio + 1))
        sclk_ovf = Signal()

        ws_count = Signal(range(self.sclk_ws_ratio*self.mclk_sclk_ratio + 1))
        ws_ovf = Signal(init=0)
        
        m.d.comb += sclk_ovf.eq(sclk_count == (2**(sclk_count.shape().width-1)-1)//2)
        m.d.comb += ws_ovf.eq(ws_count == (2**(ws_count.shape().width)-1)//4)

        m.d.i2s_mclk += sclk_count.eq(sclk_count + 1)
        m.d.i2s_mclk += ws_count.eq(ws_count + 1)
        
        with m.If(self.en):
            m.d.i2s_mclk += self.mclk.eq(~self.mclk)
            with m.If(sclk_ovf):
                m.d.i2s_mclk += sclk_count.eq(0)
                m.d.i2s_mclk += self.sclk.eq(~self.sclk)

            with m.If(ws_ovf):
                m.d.i2s_mclk += ws_count.eq(0)
                m.d.i2s_mclk += self.ws.eq(~self.ws)
            return m

class I2S_TX(wiring.Component):
    def __init__(self, width):
        self.width = width
        super().__init__({
            # Inputs
            "l_data_tx" : In(stream.Signature(signed(width))),
            "r_data_tx" : In(stream.Signature(signed(width))),
            "en" : In(1),

            # Outputs
            "mclk" : Out(1),
            "sclk" : Out(1),
            "ws" : Out(1),
            "sd_tx" : Out(1)
    })

    def elaborate(self, platform):
        m = Module()
        
        m.submodules.i2s_clocks = i2s_clocks = I2S_clocks()
        m.d.comb += i2s_clocks.en.eq(self.en),


        with m.If(self.en == 1):
            m.d.comb += [
                    self.mclk.eq(i2s_clocks.mclk),
                    self.sclk.eq(i2s_clocks.sclk),
                    self.ws.eq(i2s_clocks.ws)
                    
            ]

        counter = Signal(signed(self.width))


       
        return m
