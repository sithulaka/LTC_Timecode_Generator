"""
Performance benchmarks for LTC generation.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ltc_generator import FrameRate, LTCConfig, LTCGenerator


class TestPerformance:
    def test_1min_generation_under_2s(self):
        config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                          bit_depth=16, start_time=(0, 0, 0, 0), duration_seconds=60.0)
        gen = LTCGenerator(config)
        start = time.time()
        gen.generate_ltc()
        elapsed = time.time() - start
        assert elapsed < 2.0, f"1-min generation took {elapsed:.2f}s (limit: 2s)"

    def test_24bit_vectorized_fast(self):
        """24-bit export should not be dramatically slower than 16-bit"""
        config16 = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                            bit_depth=16, start_time=(0, 0, 0, 0), duration_seconds=60.0)
        config24 = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                            bit_depth=24, start_time=(0, 0, 0, 0), duration_seconds=60.0)
        gen16 = LTCGenerator(config16)
        gen24 = LTCGenerator(config24)
        t16_start = time.time()
        gen16.export_wav('/tmp/bench16.wav')
        t16 = time.time() - t16_start
        t24_start = time.time()
        gen24.export_wav('/tmp/bench24.wav')
        t24 = time.time() - t24_start
        ratio = t24 / max(t16, 0.001)
        assert ratio < 2.0, f"24-bit is {ratio:.1f}x slower than 16-bit (limit: 2x)"
