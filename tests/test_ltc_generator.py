import pytest
import os
import sys
import wave
import struct
import tempfile
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ltc_generator import FrameRate, LTCConfig, LTCGenerator


class TestLTCWordStructure:
    """Test correct 80-bit LTC word structure"""

    def _make_generator(self, frame_rate=FrameRate.FR_30_NDF, sample_rate=48000):
        config = LTCConfig(frame_rate=frame_rate, sample_rate=sample_rate,
                          bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0)
        return LTCGenerator(config)

    def test_sync_word_at_bits_64_79(self):
        """Sync word 0xBFFC must be at bits 64-79"""
        gen = self._make_generator()
        word = gen._generate_ltc_word([1, 0, 0, 0])
        sync = sum(word[64 + i] * (1 << i) for i in range(16))
        assert sync == 0xBFFC

    def test_word_length_is_80_bits(self):
        gen = self._make_generator()
        word = gen._generate_ltc_word([0, 0, 0, 0])
        assert len(word) == 80

    def test_frame_units_at_bits_0_3(self):
        gen = self._make_generator()
        word = gen._generate_ltc_word([0, 0, 0, 7])  # frame 7
        val = sum(word[i] * (1 << i) for i in range(4))
        assert val == 7

    def test_frame_tens_at_bits_8_9(self):
        gen = self._make_generator()
        word = gen._generate_ltc_word([0, 0, 0, 25])  # frame 25 -> tens=2
        val = sum(word[8 + i] * (1 << i) for i in range(2))
        assert val == 2

    def test_drop_frame_flag_at_bit_10(self):
        gen_df = self._make_generator(FrameRate.FR_29_97_DF)
        # Use timecode that won't trigger drop frame adjustment (10th minute)
        word = gen_df._generate_ltc_word([0, 10, 0, 0])
        assert word[10] == 1

        gen_ndf = self._make_generator(FrameRate.FR_30_NDF)
        word = gen_ndf._generate_ltc_word([0, 0, 0, 0])
        assert word[10] == 0

    def test_seconds_units_at_bits_16_19(self):
        gen = self._make_generator()
        word = gen._generate_ltc_word([0, 0, 37, 0])  # seconds 37, units=7
        val = sum(word[16 + i] * (1 << i) for i in range(4))
        assert val == 7

    def test_seconds_tens_at_bits_24_26(self):
        gen = self._make_generator()
        word = gen._generate_ltc_word([0, 0, 37, 0])  # seconds 37, tens=3
        val = sum(word[24 + i] * (1 << i) for i in range(3))
        assert val == 3

    def test_minutes_units_at_bits_32_35(self):
        gen = self._make_generator()
        word = gen._generate_ltc_word([0, 45, 0, 0])  # minutes 45, units=5
        val = sum(word[32 + i] * (1 << i) for i in range(4))
        assert val == 5

    def test_minutes_tens_at_bits_40_42(self):
        gen = self._make_generator()
        word = gen._generate_ltc_word([0, 45, 0, 0])  # minutes 45, tens=4
        val = sum(word[40 + i] * (1 << i) for i in range(3))
        assert val == 4

    def test_hours_units_at_bits_48_51(self):
        gen = self._make_generator()
        word = gen._generate_ltc_word([13, 0, 0, 0])  # hours 13, units=3
        val = sum(word[48 + i] * (1 << i) for i in range(4))
        assert val == 3

    def test_hours_tens_at_bits_56_57(self):
        gen = self._make_generator()
        word = gen._generate_ltc_word([13, 0, 0, 0])  # hours 13, tens=1
        val = sum(word[56 + i] * (1 << i) for i in range(2))
        assert val == 1


class TestPolarityCorrection:
    """Test polarity correction bit makes total 1-count even"""

    def _make_generator(self, frame_rate=FrameRate.FR_30_NDF):
        config = LTCConfig(frame_rate=frame_rate, sample_rate=48000,
                          bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0)
        return LTCGenerator(config)

    def test_parity_even_for_various_timecodes(self):
        gen = self._make_generator()
        timecodes = [
            [0, 0, 0, 0], [1, 0, 0, 0], [23, 59, 59, 29],
            [12, 30, 15, 10], [0, 0, 0, 1], [5, 5, 5, 5],
        ]
        for tc in timecodes:
            word = gen._generate_ltc_word(tc)
            ones = sum(word[0:64])
            assert ones % 2 == 0, f"Parity not even for timecode {tc}: {ones} ones"


class TestDropFrame:
    """Test drop frame logic"""

    def test_2997_skips_frames_0_1(self):
        config = LTCConfig(frame_rate=FrameRate.FR_29_97_DF, sample_rate=48000,
                          bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0)
        gen = LTCGenerator(config)
        # At second 0, minute 1 (non-tenth), frame 0 -> should become 2
        result = gen._apply_drop_frame(0, 1, 0, 0)
        assert result == 2
        result = gen._apply_drop_frame(0, 1, 0, 1)
        assert result == 3

    def test_2997_no_skip_at_tenth_minutes(self):
        config = LTCConfig(frame_rate=FrameRate.FR_29_97_DF, sample_rate=48000,
                          bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0)
        gen = LTCGenerator(config)
        for m in [0, 10, 20, 30, 40, 50]:
            result = gen._apply_drop_frame(0, m, 0, 0)
            assert result == 0, f"Should not skip at minute {m}"

    def test_5994_skips_frames_0_3(self):
        config = LTCConfig(frame_rate=FrameRate.FR_59_94_DF, sample_rate=48000,
                          bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0)
        gen = LTCGenerator(config)
        for f in range(4):
            result = gen._apply_drop_frame(0, 1, 0, f)
            assert result == f + 4, f"59.94 DF frame {f} should become {f+4}"

    def test_5994_no_skip_at_tenth_minutes(self):
        config = LTCConfig(frame_rate=FrameRate.FR_59_94_DF, sample_rate=48000,
                          bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0)
        gen = LTCGenerator(config)
        for m in [0, 10, 20, 30, 40, 50]:
            result = gen._apply_drop_frame(0, m, 0, 0)
            assert result == 0


class TestTimecodeIncrement:
    """Test timecode increment and wrapping"""

    def _make_generator(self, frame_rate=FrameRate.FR_30_NDF):
        config = LTCConfig(frame_rate=frame_rate, sample_rate=48000,
                          bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0)
        return LTCGenerator(config)

    def test_basic_increment(self):
        gen = self._make_generator()
        tc = [0, 0, 0, 0]
        gen._increment_timecode(tc)
        assert tc == [0, 0, 0, 1]

    def test_frame_rollover(self):
        gen = self._make_generator(FrameRate.FR_30_NDF)
        tc = [0, 0, 0, 29]
        gen._increment_timecode(tc)
        assert tc == [0, 0, 1, 0]

    def test_second_rollover(self):
        gen = self._make_generator()
        tc = [0, 0, 59, 29]
        gen._increment_timecode(tc)
        assert tc == [0, 1, 0, 0]

    def test_minute_rollover(self):
        gen = self._make_generator()
        tc = [0, 59, 59, 29]
        gen._increment_timecode(tc)
        assert tc == [1, 0, 0, 0]

    def test_midnight_wrap(self):
        gen = self._make_generator()
        tc = [23, 59, 59, 29]
        gen._increment_timecode(tc)
        assert tc == [0, 0, 0, 0]

    def test_drop_frame_increment_skips_correctly(self):
        """29.97 DF: incrementing past second boundary at non-tenth minute skips frames 0,1"""
        gen = self._make_generator(FrameRate.FR_29_97_DF)
        tc = [0, 0, 59, 29]  # Last frame before 00:01:00
        gen._increment_timecode(tc)
        assert tc == [0, 1, 0, 2], f"Expected [0,1,0,2] got {tc}"

    def test_drop_frame_no_skip_at_tenth_minute(self):
        gen = self._make_generator(FrameRate.FR_29_97_DF)
        tc = [0, 9, 59, 29]  # Last frame before 00:10:00
        gen._increment_timecode(tc)
        assert tc == [0, 10, 0, 0]

    def test_5994_drop_frame_increment_skips_4(self):
        """59.94 DF: incrementing past second boundary at non-tenth minute skips frames 0-3"""
        gen = self._make_generator(FrameRate.FR_59_94_DF)
        tc = [0, 0, 59, 59]  # Last frame before 00:01:00
        gen._increment_timecode(tc)
        assert tc == [0, 1, 0, 4], f"Expected [0,1,0,4] got {tc}"


class TestWAVExport:
    """Test WAV file export"""

    def test_16bit_wav_export(self):
        config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                          bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0)
        gen = LTCGenerator(config)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name
        try:
            gen.export_wav(path)
            with wave.open(path, 'rb') as wf:
                assert wf.getnchannels() == 1
                assert wf.getsampwidth() == 2
                assert wf.getframerate() == 48000
                assert wf.getnframes() == 48000  # 1 second
        finally:
            os.unlink(path)

    def test_24bit_wav_export(self):
        config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                          bit_depth=24, start_time=(0,0,0,0), duration_seconds=1.0)
        gen = LTCGenerator(config)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name
        try:
            gen.export_wav(path)
            with wave.open(path, 'rb') as wf:
                assert wf.getnchannels() == 1
                assert wf.getsampwidth() == 3
                assert wf.getframerate() == 48000
                assert wf.getnframes() == 48000
        finally:
            os.unlink(path)

    def test_sample_count_matches_duration(self):
        for sr in [44100, 48000]:
            config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=sr,
                              bit_depth=16, start_time=(0,0,0,0), duration_seconds=2.0)
            gen = LTCGenerator(config)
            audio, rate = gen.generate_ltc()
            assert len(audio) == sr * 2
            assert rate == sr


class TestLTCConfig:
    """Test config validation"""

    def test_invalid_sample_rate(self):
        with pytest.raises(ValueError):
            LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=22050,
                     bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0)

    def test_invalid_bit_depth(self):
        with pytest.raises(ValueError):
            LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                     bit_depth=8, start_time=(0,0,0,0), duration_seconds=1.0)

    def test_invalid_hours(self):
        with pytest.raises(ValueError):
            LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                     bit_depth=16, start_time=(24,0,0,0), duration_seconds=1.0)

    def test_invalid_frames(self):
        with pytest.raises(ValueError):
            LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                     bit_depth=16, start_time=(0,0,0,30), duration_seconds=1.0)

    def test_negative_duration(self):
        with pytest.raises(ValueError):
            LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                     bit_depth=16, start_time=(0,0,0,0), duration_seconds=-1.0)

    def test_valid_config(self):
        config = LTCConfig(frame_rate=FrameRate.FR_29_97_DF, sample_rate=48000,
                          bit_depth=16, start_time=(1,30,0,0), duration_seconds=60.0)
        assert config.frame_rate == FrameRate.FR_29_97_DF


class TestAllFrameRates:
    """Test all frame rates produce valid BCD-encoded timecode"""

    def test_all_frame_rates_produce_valid_ltc(self):
        for fr in FrameRate:
            config = LTCConfig(frame_rate=fr, sample_rate=48000,
                              bit_depth=16, start_time=(1,30,15,0), duration_seconds=0.5)
            gen = LTCGenerator(config)
            word = gen._generate_ltc_word([1, 30, 15, 0])
            # Check sync word
            sync = sum(word[64 + i] * (1 << i) for i in range(16))
            assert sync == 0xBFFC, f"Sync word wrong for {fr.name}"
            # Check parity
            ones = sum(word[0:64])
            assert ones % 2 == 0, f"Parity not even for {fr.name}"


class TestEdgeCases:
    """Edge case tests for unusual configurations and boundary conditions."""

    def test_start_at_drop_frame_boundary(self):
        """Start at 00:01:00:02 for 29.97 DF — first valid frame after skip"""
        config = LTCConfig(frame_rate=FrameRate.FR_29_97_DF, sample_rate=48000,
                          bit_depth=16, start_time=(0, 1, 0, 2), duration_seconds=1.0)
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()
        assert len(audio) == 48000

    def test_max_timecode_start(self):
        """Start at 23:59:59:29 — should wrap to 00:00:00:00"""
        config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                          bit_depth=16, start_time=(23, 59, 59, 29), duration_seconds=1.0)
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()
        assert len(audio) == 48000

    def test_very_short_duration(self):
        """Duration shorter than one frame"""
        config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                          bit_depth=16, start_time=(0, 0, 0, 0), duration_seconds=0.01)
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()
        assert len(audio) == 480

    def test_44100_with_23976(self):
        """Sample rate that doesn't divide evenly by frame rate"""
        config = LTCConfig(frame_rate=FrameRate.FR_23_976_NDF, sample_rate=44100,
                          bit_depth=16, start_time=(0, 0, 0, 0), duration_seconds=2.0)
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()
        assert len(audio) == 88200

    def test_user_bits_preserved(self):
        """User bits 0xDEADBEEF should be encoded in UB1-UB8"""
        config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                          bit_depth=16, start_time=(0, 0, 0, 0), duration_seconds=1.0,
                          user_bits=0xDEADBEEF)
        gen = LTCGenerator(config)
        word = gen._generate_ltc_word([0, 0, 0, 0])
        ub_positions = [4, 12, 20, 28, 36, 44, 52, 60]
        ub_val = 0
        for idx, pos in enumerate(ub_positions):
            nibble = sum(word[pos + i] << i for i in range(4))
            ub_val |= nibble << (idx * 4)
        assert ub_val == 0xDEADBEEF

    def test_32bit_export(self):
        """32-bit WAV export"""
        config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                          bit_depth=32, start_time=(0, 0, 0, 0), duration_seconds=1.0)
        gen = LTCGenerator(config)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name
        try:
            gen.export_wav(path)
            with wave.open(path, 'rb') as wf:
                assert wf.getsampwidth() == 4
                assert wf.getnframes() == 48000
        finally:
            os.unlink(path)

    def test_stereo_export(self):
        """Stereo WAV export has 2 channels"""
        config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                          bit_depth=16, start_time=(0, 0, 0, 0), duration_seconds=1.0,
                          channels=2)
        gen = LTCGenerator(config)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name
        try:
            gen.export_wav(path)
            with wave.open(path, 'rb') as wf:
                assert wf.getnchannels() == 2
                assert wf.getnframes() == 48000
        finally:
            os.unlink(path)

    def test_streaming_export_matches_regular(self):
        """Streaming export produces same audio as regular export"""
        config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                          bit_depth=16, start_time=(1, 0, 0, 0), duration_seconds=2.0)
        gen = LTCGenerator(config)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f1, \
             tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f2:
            p1, p2 = f1.name, f2.name
        try:
            gen.export_wav(p1)
            gen.export_wav_streaming(p2)
            with wave.open(p1, 'rb') as w1, wave.open(p2, 'rb') as w2:
                assert w1.getnframes() == w2.getnframes()
                d1 = w1.readframes(w1.getnframes())
                d2 = w2.readframes(w2.getnframes())
                assert d1 == d2
        finally:
            os.unlink(p1)
            os.unlink(p2)
