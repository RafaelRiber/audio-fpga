from amaranth import *
from amaranth.build import *
from amaranth.lib import io
from amaranth_boards.icebreaker import ICEBreakerPlatform

#from .blinky import Blinky
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
        # m.submodules.i2s_clocks = i2s_clocks = I2S_clocks()
        m.submodules.i2s_transceiver = i2s_tx = I2S_Transceiver(width = 24)
        m.d.comb += [
            i2s_tx.en.eq(True),

            i2s2_pins.da_MCLK.o.eq(i2s_tx.mclk),
            i2s2_pins.da_LRCK.o.eq(i2s_tx.ws),
            i2s2_pins.da_SCLK.o.eq(i2s_tx.sclk),

            i2s2_pins.ad_MCLK.o.eq(i2s_tx.mclk),
            i2s2_pins.ad_LRCK.o.eq(i2s_tx.ws),
            i2s2_pins.ad_SCLK.o.eq(i2s_tx.sclk),
            i2s2_pins.da_SDIN.o.eq(i2s2_pins.ad_SDOUT.i)
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
    m.submodules.i2s_transceiver = i2s_tx = I2S_Transceiver(width = 24)
    main(m)
