from amaranth.sim import Simulator
from audio_fpga import I2S_clocks, I2S_Transceiver

async def stream_get(ctx, stream, domain):
    ctx.set(stream.ready, 1)
    payload, = await ctx.tick(domain).sample(stream.payload).until(stream.valid)
    ctx.set(stream.ready, 0)
    return payload

async def stream_put(ctx, stream, payload):
    ctx.set(stream.valid, 1)
    ctx.set(stream.payload, payload)
    await ctx.tick('i2s_mclk').until(stream.ready)
    ctx.set(stream.valid, 0)


def test_i2s_clocks():
    m_s_ratio = 4
    s_w_ratio = 64 

    i2s_clocks = I2S_clocks(mclk_sclk_ratio=m_s_ratio, sclk_ws_ratio=s_w_ratio)

    async def testbench(ctx):
        ctx.set(i2s_clocks.en, True)
        # Test mclk/sclk ratio
        for _ in range(m_s_ratio - 1):
            await ctx.tick(domain='i2s_mclk').repeat(m_s_ratio)
            # assert ctx.get(i2s_clocks.sclk) == 1
            await ctx.tick(domain='i2s_mclk').repeat(m_s_ratio)
            # assert ctx.get(i2s_clocks.sclk) == 0

        # # Test sclk/ws ratio
        #
        # for _ in range(s_w_ratio-1):
        #     await ctx.tick(domain='i2s_mclk').repeat(m_s_ratio*s_w_ratio)
        #     #assert ctx.get(i2s_clocks.ws) == 1
        #     await ctx.tick(domain='i2s_mclk').repeat(m_s_ratio*s_w_ratio)
        # await ctx.tick(domain='i2s_mclk').repeat(m_s_ratio*10)


    sim = Simulator(i2s_clocks)
    sim.add_clock(88.573959255979e-9, domain='i2s_mclk')
    sim.add_testbench(testbench)
    with sim.write_vcd("test_i2s_clocks.vcd"):
        sim.run()

def test_i2s_tx():
    width = 24
    i2s_tx = I2S_Transceiver(width = width, pll=False)

    async def testbench_input_left(ctx):
        await stream_put(ctx, i2s_tx.l_data_tx, 0b101010101010101010101010)
    async def testbench_input_right(ctx):
        await stream_put(ctx, i2s_tx.r_data_tx, 0b010101010101010101010101)

    async def testbench_output(ctx):
        ctx.set(i2s_tx.en, 1)

    sim = Simulator(i2s_tx)
    sim.add_clock(88.573959255979e-9, domain='i2s_mclk')
    sim.add_testbench(testbench_input_left)
    sim.add_testbench(testbench_input_right)
    sim.add_testbench(testbench_output)
    with sim.write_vcd("test_i2s_tx.vcd"):
        sim.run_until(88.5e-9 * 1100)

