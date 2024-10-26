from amaranth import *
from amaranth.build import *
from amaranth.lib import io
from amaranth_boards.icebreaker import ICEBreakerPlatform

#from .blinky import Blinky
from .i2s import I2S_clocks
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
        m.submodules.clk12 = clk12 = io.Buffer("i", platform.request("clk12", dir="-"))

        m.domains.i2s_mclk = cd_i2s_mclk = ClockDomain()
        m.d.comb += cd_i2s_mclk.clk.eq(clk12.i)

        m.submodules.i2s_clocks = i2s_clocks = I2S_clocks()
        m.d.comb += [
            i2s2_pins.da_MCLK.o.eq(cd_i2s_mclk.clk),
            i2s2_pins.da_LRCK.o.eq(i2s_clocks.ws),
            i2s2_pins.da_SCLK.o.eq(i2s_clocks.sclk),

            i2s2_pins.ad_MCLK.o.eq(cd_i2s_mclk.clk),
            i2s2_pins.ad_LRCK.o.eq(i2s_clocks.ws),
            i2s2_pins.ad_SCLK.o.eq(i2s_clocks.sclk)
        ]

        return m


def build_icebreaker():
    plat = ICEBreakerPlatform()
    load_dotenv()
    plat.add_resources(pmod_i2s2)
    plat.build(Toplevel())

def run_dev():
    from amaranth.cli import main
    m=Module()
    m.submodules.i2s_clocks = i2s_dev = I2S_clocks()
    main(m, ports=i2s_dev.ports())
