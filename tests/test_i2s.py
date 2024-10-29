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
    i2s_tx = I2S_Transceiver(width = width, pll_ice40=False)

    async def testbench_input_left(ctx):
        await stream_put(ctx, i2s_tx.l_data_tx, 0b001010101010101010101010)
        
    async def testbench_input_right(ctx):
        await stream_put(ctx, i2s_tx.r_data_tx, 0b110101010101010101010101)

    async def testbench_output_left(ctx):
        ctx.set(i2s_tx.en, 1)
        await ctx.tick('i2s_mclk').repeat(2)
        for index, expected_bit in enumerate([0,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0]):
            _, sdat = await ctx.posedge(i2s_tx.sclk).sample(i2s_tx.sd_tx)
            assert sdat == expected_bit, \
                f"bit {index}: {sdat} != {expected_bit} (expected)"

        await ctx.posedge(i2s_tx.ws)
        await ctx.tick('i2s_mclk').repeat(2)
        for index, expected_bit in enumerate([1,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1]):
            _, sdat = await ctx.posedge(i2s_tx.sclk).sample(i2s_tx.sd_tx)
            assert sdat == expected_bit, \
                f"bit {index}: {sdat} != {expected_bit} (expected)"

    sim = Simulator(i2s_tx)
    sim.add_clock(88.573959255979e-9, domain='i2s_mclk')
    sim.add_testbench(testbench_input_left)
    sim.add_testbench(testbench_input_right)
    sim.add_testbench(testbench_output_left)
    with sim.write_vcd("test_i2s_tx.vcd"):
        sim.run()


def test_i2s_rx():
    width = 24

    i2s = I2S_Transceiver(width = width, pll_ice40=False)

    async def testbench(ctx):
        ctx.set(i2s.en, 1)
        for bit in [1,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1]:
            await ctx.posedge(i2s.sclk)
            ctx.set(i2s.sd_rx, bit)
            await ctx.tick('i2s_mclk').repeat(2)
        await ctx.posedge(i2s.ws)
        for bit in [1,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,0]:
            await ctx.posedge(i2s.sclk)
            ctx.set(i2s.sd_rx, bit)
            await ctx.tick('i2s_mclk').repeat(2)
        await ctx.negedge(i2s.ws)
        for bit in [1,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,0]:
            await ctx.posedge(i2s.sclk)
            ctx.set(i2s.sd_rx, bit)
            await ctx.tick('i2s_mclk').repeat(2)

        await ctx.tick('i2s_mclk').repeat(199)
    
    sim = Simulator(i2s)
    sim.add_clock(88.5e-9, domain='i2s_mclk')
    sim.add_testbench(testbench)
    with sim.write_vcd("test_i2s_rx.vcd"):
        sim.run()
