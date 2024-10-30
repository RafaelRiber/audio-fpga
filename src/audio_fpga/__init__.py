from amaranth import *
from amaranth.build import *
from amaranth.lib import wiring
from amaranth.lib.fifo import AsyncFIFO
from amaranth_boards.icebreaker import ICEBreakerPlatform

from .i2s import I2S_clocks, I2S_Transceiver
# Temporary fix until uv supports env files
from dotenv import load_dotenv

pmod_i2s2 = [
    Resource("pmod_i2s2", 0,
             Subsignal("da_MCLK", Pins("1", dir="o", conn=("pmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS33")),
             Subsignal("da_LRCK", Pins("2", dir="o", conn=("pmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS33")),
             Subsignal("da_SCLK", Pins("3", dir="o", conn=("pmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS33")),
             Subsignal("da_SDIN", Pins("4", dir="o", conn=("pmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS33")),
             Subsignal("ad_MCLK", Pins("7", dir="o", conn=("pmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS33")),
             Subsignal("ad_LRCK", Pins("8", dir="o", conn=("pmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS33")),
             Subsignal("ad_SCLK", Pins("9", dir="o", conn=("pmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS33")),
             Subsignal("ad_SDOUT", Pins("10", dir="i", conn=("pmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS33")))
]

class Toplevel(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        i2s2_pins = platform.request("pmod_i2s2")

        # I2S instantiation and connection
        m.submodules.i2s_transceiver = i2s = I2S_Transceiver(width = 24, mclk_sclk_ratio=4, sclk_ws_ratio=64, pll_ice40=True)
        m.submodules.queue_l = queue_l = AsyncFIFO(width=24, depth=16, r_domain='i2s_mclk', w_domain='i2s_mclk')
        m.submodules.queue_r = queue_r = AsyncFIFO(width=24, depth=16, r_domain='i2s_mclk', w_domain='i2s_mclk')

        wiring.connect(m, i2s.l_data_rx, queue_l.w_stream)
        wiring.connect(m, queue_l.r_stream, i2s.l_data_tx)
        wiring.connect(m, i2s.r_data_rx, queue_r.w_stream)
        wiring.connect(m, queue_r.r_stream, i2s.r_data_tx)

        m.d.comb += [
            i2s.en.eq(True),

            i2s2_pins.da_MCLK.o.eq(i2s.mclk),
            i2s2_pins.da_LRCK.o.eq(i2s.ws),
            i2s2_pins.da_SCLK.o.eq(i2s.sclk),

            i2s2_pins.ad_MCLK.o.eq(i2s.mclk),
            i2s2_pins.ad_LRCK.o.eq(i2s.ws),
            i2s2_pins.ad_SCLK.o.eq(i2s.sclk),
            # i2s2_pins.da_SDIN.o.eq(i2s2_pins.ad_SDOUT.i) # LEAVE HERE FOR TESTING DIRECT LOOPBACK

            i2s2_pins.da_SDIN.o.eq(i2s.sd_tx),
            i2s.sd_rx.eq(i2s2_pins.ad_SDOUT.i)
        ]


        return m


def build_icebreaker():
    plat = ICEBreakerPlatform()
    print("Loading Env")
    load_dotenv()
    print("Adding Ressources")
    plat.add_resources(pmod_i2s2)
    print("Building ICEBreaker bitfile...")
    plat.build(Toplevel())
    print("Done !")

def run_dev():
    from amaranth.cli import main
    m=Module()
    # m.submodules.i2s_clocks = i2s_dev = I2S_clocks()
    m.submodules.i2s_transceiver = i2s_tx = I2S_Transceiver(width = 24, pll_ice40=False)
    main(m)
