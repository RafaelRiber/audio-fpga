from amaranth import *
from amaranth.lib import wiring, stream
from amaranth.lib.wiring import In, Out

class I2S_clocks(wiring.Component):
    # ws is the sample rate of the interface, set mclk_freq = f_s * mclk_sclk_ratio * sclk_ws_ratio
    # For example : f_sample = 44100 Hz --> mclk_freq = 44100 * 64 * 4 = 11.29 MHz
    def __init__(self, mclk_sclk_ratio=4, sclk_ws_ratio=64):
        super().__init__({
            "en" : In(1),
            "mclk" : Out(1),
            "sclk" : Out(1),
            "ws" : Out(1)
        })

        self.mclk_sclk_ratio = mclk_sclk_ratio
        self.sclk_ws_ratio = sclk_ws_ratio
        
    def elaborate(self, platform):
        m = Module()

        sclk_count = Signal(range(self.mclk_sclk_ratio + 1), init=1)
        sclk_ovf = Signal(init=1)

        ws_count = Signal(range(self.sclk_ws_ratio*self.mclk_sclk_ratio + 1), init=1)
        ws_ovf = Signal(init=1)
        
        m.d.i2s_mclk += sclk_count.eq(sclk_count + 1)
        m.d.i2s_mclk += ws_count.eq(ws_count + 1)
        
        with m.If(self.en):

            m.d.comb += sclk_ovf.eq(sclk_count == (2**(sclk_count.shape().width-1)-1)//2)
            m.d.comb += ws_ovf.eq(ws_count == (2**(ws_count.shape().width)-1)//4)
            with m.If(sclk_ovf):
                m.d.i2s_mclk += sclk_count.eq(0)
                m.d.i2s_mclk += self.sclk.eq(~self.sclk)

            with m.If(ws_ovf):
                m.d.i2s_mclk += ws_count.eq(0)
                m.d.i2s_mclk += self.ws.eq(~self.ws)

        with m.Else():
            m.d.i2s_mclk += [
                sclk_count.eq((2**(sclk_count.shape().width-1)-1)//2),
                ws_count.eq(0),
             ]
        return m

class I2S_Transceiver(wiring.Component):
    def __init__(self, width, pll_ice40=True):
        self.width = width
        self.pll = pll_ice40
        super().__init__({
            # Inputs
            "l_data_tx" : In(stream.Signature(signed(width))),
            "r_data_tx" : In(stream.Signature(signed(width))),
            "en" : In(1),
            "sd_rx" : In(1),
            # Outputs
            "mclk" : Out(1),
            "sclk" : Out(1),
            "ws" : Out(1),
            "sd_tx" : Out(1),
            "l_data_rx" : Out(stream.Signature(signed(width))),
            "r_data_rx" : Out(stream.Signature(signed(width))) 
    })

    def elaborate(self, platform):
        m = Module()

        # Clock domain creation
        m.domains.i2s_mclk = cd_i2s_mclk = ClockDomain()
       
        # PLL
        if (self.pll == True):
            cd_por = ClockDomain("por", local=True)
            m.domains += cd_por
            delay = int(5 * 3e-6 * 48e6)
            timer = Signal(range(delay))
            ready = Signal()
            pll_locked = Signal()
            with m.If(timer == delay):
                m.d.por += ready.eq(1)
            with m.Else():
                m.d.por += timer.eq(timer + 1)
            m.d.comb += cd_por.clk.eq(cd_i2s_mclk.clk), cd_por.rst.eq(~pll_locked)
            m.d.comb += cd_i2s_mclk.rst.eq(~ready)
            m.submodules.pll = Instance(
                "SB_PLL40_PAD",
                p_FEEDBACK_PATH="SIMPLE",
                p_DIVR=0,
                p_DIVF=65,
                p_DIVQ=5,
                p_FILTER_RANGE=1,
                i_PACKAGEPIN=platform.request("clk12", dir="-").io,
                i_RESETB=1,
                o_PLLOUTGLOBAL=cd_i2s_mclk.clk,
                o_LOCK=pll_locked,
            )


        m.submodules.i2s_clocks = i2s_clocks = I2S_clocks()
        # m.domains.i2s_mclk = cd_i2s_mclk = ClockDomain()
        m.d.comb += [
            i2s_clocks.en.eq(self.en),
        ] 

        data = Signal(self.width)
        latch_l = Signal()
        latch_r = Signal()

        sclk_reg = Signal()
        sclk_edge = sclk_reg & self.sclk
        m.d.i2s_mclk += sclk_reg.eq(self.sclk)

        with m.If(self.en == 1):
            m.d.comb += [
                    self.sclk.eq(i2s_clocks.sclk),
                    self.ws.eq(i2s_clocks.ws),
                    self.mclk.eq(cd_i2s_mclk.clk)
            ]

        counter = Signal(signed(self.width + 2))

        ##################### TX FSM #############################

        with m.FSM(domain='i2s_mclk'):
            with m.State("WAIT"):
                with m.If(self.en == 1):
                    m.next = "WAIT"
                with m.If(~self.ws & ~latch_l & self.l_data_tx.valid):
                    m.d.comb += self.l_data_tx.ready.eq(1)
                    m.d.i2s_mclk += counter.eq(self.width + 2)
                    m.d.i2s_mclk += data.eq(self.l_data_tx.payload)
                    with m.If(~sclk_edge):
                        m.next = "LEFT"
                with m.If(self.ws & ~latch_r & self.r_data_tx.valid): 
                    m.d.comb += self.r_data_tx.ready.eq(1)
                    m.d.i2s_mclk += counter.eq(self.width + 2)
                    m.d.i2s_mclk += data.eq(self.r_data_tx.payload)
                    with m.If(~sclk_edge):
                        m.next = "RIGHT"


            with m.State("LEFT"):
                m.d.comb += self.l_data_tx.ready.eq(0)
                with m.If(~self.ws & latch_r):
                    m.d.i2s_mclk += latch_r.eq(0)
                with m.If(sclk_edge):
                    m.d.i2s_mclk += data.eq(Cat(0,data))
                    m.d.i2s_mclk += self.sd_tx.eq(data[-1])
                    m.d.i2s_mclk += counter.eq(counter - 1)
                
                with m.If(counter == 0):
                    m.d.i2s_mclk += latch_l.eq(1)
                    m.next = "WAIT"


            with m.State("RIGHT"):
                m.d.comb += self.r_data_tx.ready.eq(0)
                with m.If(self.ws & latch_l):
                    m.d.i2s_mclk += latch_l.eq(0)
                with m.If(sclk_edge):
                    m.d.i2s_mclk += data.eq(Cat(0,data))
                    m.d.i2s_mclk += self.sd_tx.eq(data[-1])
                    m.d.i2s_mclk += counter.eq(counter - 1)
                with m.If(counter == 0):
                    m.d.i2s_mclk += latch_r.eq(1)
                    m.next = "WAIT"
        return m
