from amaranth.sim import Simulator
from audio_fpga import I2S_clocks



def test_i2s_clocks():
    m_s_ratio = 4 
    s_w_ratio = 264

    i2s_clocks = I2S_clocks(mclk_sclk_ratio=m_s_ratio, sclk_ws_ratio=s_w_ratio)

    async def testbench(ctx):
        # Wait a few cycles
        await ctx.tick(domain='mclk').repeat(3)
        ctx.set(i2s_clocks.en, True)
        for _ in range(100):
            # await ctx.tick(domain='mclk').repeat(m_s_ratio-1)
            # assert ctx.get(i2s_clocks.sclk) == 0
            await ctx.tick(domain='mclk').repeat(m_s_ratio)
            assert ctx.get(i2s_clocks.sclk) == 1
            await ctx.tick(domain='mclk').repeat(m_s_ratio)
            assert ctx.get(i2s_clocks.sclk) == 0



    sim = Simulator(i2s_clocks)
    sim.add_clock(1e-6, domain='mclk')
    sim.add_testbench(testbench)
    with sim.write_vcd("test_i2s.vcd"):
        sim.run()
