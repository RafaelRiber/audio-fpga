from amaranth import *
from amaranth.lib import wiring, stream
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import Out
import math

def sine_gen(frequency, sample_rate, bit_width):
    period_duration = 1 / frequency                 # Duration of one period in seconds
    num_samples = int(sample_rate * period_duration)  # Number of samples for one period
    
    # Constants for two's complement range
    max_amplitude = 2**(bit_width - 1) - 1  # Max positive value for given bit width
    min_amplitude = -2**(bit_width - 1)     # Min (most negative) value for given bit width
    
    # Generate sine wave in integer form for one period
    sine_wave_integers = []
    for i in range(num_samples):
        # Calculate the time for this sample
        t = i / sample_rate
        
        # Generate the sine wave sample and scale to the specified bit width
        sample = math.sin(2 * math.pi * frequency * t)
        sample_scaled = int(sample * max_amplitude)
        
        # Clip to two's complement range
        if sample_scaled > max_amplitude:
            sample_scaled = max_amplitude
        elif sample_scaled < min_amplitude:
            sample_scaled = min_amplitude
        
        # Convert to two's complement binary as an integer
        if sample_scaled < 0:
            # Convert to two's complement by adding 2^bit_width
            sample_twos_complement = (1 << bit_width) + sample_scaled
        else:
            sample_twos_complement = sample_scaled
        
        # Append the integer representation to the list
        sine_wave_integers.append(sample_twos_complement)
    
    return sine_wave_integers

class Sine(wiring.Component):

    def __init__(self, width = 24, frequency = 440, sample_rate = 96000):
        self.width = width
        self.frequency = frequency
        super().__init__({
            "data_out" : Out(stream.Signature(signed(width)))
        })

    def elaborate(self, platform):
        m = Module()

        sine = sine_gen(frequency = 400, sample_rate=96000, bit_width=self.width)
        # sine = b"Hello world\n"

        m.submodules.memory = memory = Memory(shape=signed(self.width), depth = len(sine), init=sine)

        rd_port = memory.read_port(domain="comb")

        with m.If(rd_port.addr == memory.depth - 1):
            m.d.sync += rd_port.addr.eq(0)
        with m.Else():
            m.d.sync += rd_port.addr.eq(rd_port.addr + 1)

        word = Signal(self.width)

        m.d.comb += word.eq(rd_port.data)


        return m


