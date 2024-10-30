from amaranth import *
from amaranth.lib import wiring, stream, io
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
    def __init__(self, width, pll_ice40=True, mclk_sclk_ratio=4, sclk_ws_ratio=64):
        self.width = width
        self.pll = pll_ice40
        self.mclk_sclk_ratio = mclk_sclk_ratio
        self.sclk_ws_ratio = sclk_ws_ratio
        super().__init__({
            # Inputs
            "l_data_tx" : In(stream.Signature(width)),
            "r_data_tx" : In(stream.Signature(width)),
            "en" : In(1),
            "sd_rx" : In(1),
            # Outputs
            "mclk" : Out(1),
            "sclk" : Out(1),
            "ws" : Out(1),
            "sd_tx" : Out(1),
            "l_data_rx" : Out(stream.Signature(width)),
            "r_data_rx" : Out(stream.Signature(width)) 
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
        else:
            m.submodules.clk12 = clk12 = io.Buffer("i", platform.request("clk12", dir="-"))
            m.d.comb += cd_i2s_mclk.clk.eq(clk12.i)

        m.submodules.i2s_clocks = i2s_clocks = I2S_clocks(mclk_sclk_ratio=self.mclk_sclk_ratio, sclk_ws_ratio=self.sclk_ws_ratio)
        m.d.comb += [
            i2s_clocks.en.eq(self.en),
        ] 

        data_tx = Signal(self.width)
        data_rx = Signal(self.width)
        latch_l_tx = Signal()
        latch_r_tx = Signal()

        sclk_reg = Signal()
        sclk_edge_tx = sclk_reg & self.sclk
        m.d.i2s_mclk += sclk_reg.eq(self.sclk)

        with m.If(self.en == 1):
            m.d.comb += [
                    self.sclk.eq(i2s_clocks.sclk),
                    self.ws.eq(i2s_clocks.ws),
                    self.mclk.eq(cd_i2s_mclk.clk)
            ]

        counter_tx = Signal(range(self.width))
        counter_rx = Signal(range(self.width))

        ##################### TX FSM #############################

        with m.FSM(domain='i2s_mclk') as fsm_tx:
            with m.State("TX_WAIT"):
                with m.If(self.en == 1):
                    m.next = "TX_WAIT"
                with m.If(~self.ws & ~latch_l_tx & self.l_data_tx.valid):
                    m.d.comb += self.l_data_tx.ready.eq(1)
                    m.d.i2s_mclk += counter_tx.eq(self.width)
                    m.d.i2s_mclk += data_tx.eq(self.l_data_tx.payload)
                    with m.If(~sclk_edge_tx):
                        m.next = "TX_LEFT"
                with m.If(self.ws & ~latch_r_tx & self.r_data_tx.valid): 
                    m.d.comb += self.r_data_tx.ready.eq(1)
                    m.d.i2s_mclk += counter_tx.eq(self.width)
                    m.d.i2s_mclk += data_tx.eq(self.r_data_tx.payload)
                    with m.If(~sclk_edge_tx):
                        m.next = "TX_RIGHT"


            with m.State("TX_LEFT"):
                m.d.comb += self.l_data_tx.ready.eq(0)
                with m.If(~self.ws & latch_r_tx):
                    m.d.i2s_mclk += latch_r_tx.eq(0)
                with m.If(sclk_edge_tx):
                    m.d.i2s_mclk += data_tx.eq(Cat(0,data_tx))
                    m.d.i2s_mclk += self.sd_tx.eq(data_tx[-1])
                    m.d.i2s_mclk += counter_tx.eq(counter_tx - 1)

                with m.If(counter_tx == 0):
                    m.d.i2s_mclk += latch_l_tx.eq(1)
                    m.d.i2s_mclk += self.sd_tx.eq(0)
                    m.next = "TX_WAIT"


            with m.State("TX_RIGHT"):
                m.d.comb += self.r_data_tx.ready.eq(0)
                with m.If(self.ws & latch_l_tx):
                    m.d.i2s_mclk += latch_l_tx.eq(0)
                with m.If(sclk_edge_tx):
                    m.d.i2s_mclk += data_tx.eq(Cat(0,data_tx))
                    m.d.i2s_mclk += self.sd_tx.eq(data_tx[-1])
                    m.d.i2s_mclk += counter_tx.eq(counter_tx - 1)
                with m.If(counter_tx == 0):
                    m.d.i2s_mclk += latch_r_tx.eq(1)
                    m.d.i2s_mclk += self.sd_tx.eq(0)
                    m.next = "TX_WAIT"

        ##################### RX FSM #############################

        # Detect edges on the `sclk` input:
        sclk_edge = ~sclk_reg & self.sclk
        m.d.i2s_mclk += sclk_reg.eq(self.sclk)

        done_rx = Signal()
        latch_l_rx = Signal()
        latch_r_rx = Signal()

        with m.FSM(domain='i2s_mclk') as fsm_rx:
            with m.State("RX_WAIT"):
                with m.If(self.en):
                    with m.If(~self.ws):
                        with m.If(~latch_l_rx):
                            m.next = "RX_CAPT_LEFT"

                    with m.If(self.ws):
                        with m.If(~latch_r_rx):
                            m.next = "RX_CAPT_RIGHT"

            with m.State("RX_CAPT_LEFT"):
                m.d.i2s_mclk += self.l_data_rx.valid.eq(0)
                m.d.i2s_mclk += latch_r_rx.eq(0)
                with m.If(sclk_edge):
                    m.d.i2s_mclk += [
                        counter_rx.eq(counter_rx + 1),
                        data_rx.eq(Cat(self.sd_rx, data_rx))
                    ]
                    m.d.i2s_mclk += done_rx.eq(counter_rx == self.width-1)
                    with m.If(done_rx):
                        m.d.i2s_mclk += counter_rx.eq(0)
                        m.d.i2s_mclk += done_rx.eq(1)
                        m.next = "PAYLOAD_SEND_LEFT"

            with m.State("RX_CAPT_RIGHT"):
                m.d.i2s_mclk += self.r_data_rx.valid.eq(0)
                m.d.i2s_mclk += latch_l_rx.eq(0)
                with m.If(sclk_edge):
                    m.d.i2s_mclk += [
                        counter_rx.eq(counter_rx + 1),
                        data_rx.eq(Cat(self.sd_rx, data_rx))
                    ]
                    m.d.i2s_mclk += done_rx.eq(counter_rx == self.width-1)
                    with m.If(done_rx):
                        m.d.i2s_mclk += counter_rx.eq(0)
                        m.d.i2s_mclk += done_rx.eq(1)
                        m.next = "PAYLOAD_SEND_RIGHT"

            with m.State("PAYLOAD_SEND_LEFT"):
                m.d.i2s_mclk += latch_l_rx.eq(1)
                with m.If(done_rx & ~self.l_data_rx.valid | self.l_data_rx.ready):
                    m.d.i2s_mclk += [
                        self.l_data_rx.payload.eq(data_rx),
                        self.l_data_rx.valid.eq(1),
                        done_rx.eq(0),
                    ]
                    m.next = "RX_WAIT"
                with m.Elif(self.l_data_rx.ready):
                    m.d.i2s_mclk += self.l_data_rx.valid.eq(0)

            with m.State("PAYLOAD_SEND_RIGHT"):
                m.d.i2s_mclk += latch_r_rx.eq(1)
                with m.If(done_rx & ~self.r_data_rx.valid | self.r_data_rx.ready):
                    m.d.i2s_mclk += [
                        self.r_data_rx.payload.eq(data_rx),
                        self.r_data_rx.valid.eq(1),
                        done_rx.eq(0)
                    ]
                    m.next = "RX_WAIT"
                with m.Elif(self.r_data_rx.ready):
                    m.d.i2s_mclk += self.r_data_rx.valid.eq(0)
            
        return m
