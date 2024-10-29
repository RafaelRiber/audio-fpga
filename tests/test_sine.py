from amaranth.sim import Simulator
from audio_fpga import Sine

def test_sine():

    sine = Sine(width=24, frequency=440, sample_rate=96000)

    async def testbench(ctx):
        await ctx.tick().repeat(500)

    sim = Simulator(sine)
    sim.add_clock(10.41666e-6)
    sim.add_testbench(testbench)
    with sim.write_vcd("test_sine.vcd"):
        sim.run()

