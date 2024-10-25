from amaranth.sim import Simulator
from audio_fpga import I2S_clocks

def test_i2s_clocks():
    i2s_clocks = I2S_clocks(mclk_sclk_ratio=2, sclk_ws_ratio=5)

    async def testbench(ctx):
        # await ctx.tick(domain='mclk')
        ctx.set(i2s_clocks.en, True)
        await ctx.tick(domain='mclk').repeat(500)



    sim = Simulator(i2s_clocks)
    sim.add_clock(1e-6, domain='mclk')
    sim.add_testbench(testbench)
    with sim.write_vcd("test_i2s.vcd"):
        sim.run()
