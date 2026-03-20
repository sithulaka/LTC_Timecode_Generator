"""
Real LTC decode test using libltc (the industry-standard C library).
Generates LTC audio with our Python encoder, then decodes it with libltc
to verify a real decoder can read every frame correctly.
"""
import ctypes
import ctypes.util
import os
import sys
import struct
import tempfile
import wave

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ltc_generator import FrameRate, LTCConfig, LTCGenerator

# ---------------------------------------------------------------------------
# libltc ctypes bindings
# ---------------------------------------------------------------------------
LIBLTC_PATH = "/tmp/libltc/libltc.so"

if not os.path.exists(LIBLTC_PATH):
    pytest.skip("libltc not built — run: cd /tmp/libltc && gcc -shared -fPIC -o libltc.so -I src src/ltc.c src/decoder.c src/encoder.c src/timecode.c -lm",
                allow_module_level=True)

_lib = ctypes.CDLL(LIBLTC_PATH)


class LTCFrame(ctypes.Structure):
    """Mirrors struct LTCFrame (little-endian version) from ltc.h"""
    _fields_ = [
        # byte 0
        ("frame_units", ctypes.c_uint, 4),
        ("user1", ctypes.c_uint, 4),
        # byte 1
        ("frame_tens", ctypes.c_uint, 2),
        ("dfbit", ctypes.c_uint, 1),
        ("col_frame", ctypes.c_uint, 1),
        ("user2", ctypes.c_uint, 4),
        # byte 2
        ("secs_units", ctypes.c_uint, 4),
        ("user3", ctypes.c_uint, 4),
        # byte 3
        ("secs_tens", ctypes.c_uint, 3),
        ("biphase_mark_phase_correction", ctypes.c_uint, 1),
        ("user4", ctypes.c_uint, 4),
        # byte 4
        ("mins_units", ctypes.c_uint, 4),
        ("user5", ctypes.c_uint, 4),
        # byte 5
        ("mins_tens", ctypes.c_uint, 3),
        ("binary_group_flag_bit0", ctypes.c_uint, 1),
        ("user6", ctypes.c_uint, 4),
        # byte 6
        ("hours_units", ctypes.c_uint, 4),
        ("user7", ctypes.c_uint, 4),
        # byte 7
        ("hours_tens", ctypes.c_uint, 2),
        ("binary_group_flag_bit1", ctypes.c_uint, 1),
        ("binary_group_flag_bit2", ctypes.c_uint, 1),
        ("user8", ctypes.c_uint, 4),
        # bytes 8-9
        ("sync_word", ctypes.c_uint, 16),
    ]


class LTCFrameExt(ctypes.Structure):
    _fields_ = [
        ("ltc", LTCFrame),
        ("off_start", ctypes.c_longlong),
        ("off_end", ctypes.c_longlong),
        ("reverse", ctypes.c_int),
        ("biphase_tics", ctypes.c_float * 80),
        ("sample_min", ctypes.c_ubyte),
        ("sample_max", ctypes.c_ubyte),
        ("volume", ctypes.c_double),
    ]


class SMPTETimecode(ctypes.Structure):
    _fields_ = [
        ("timezone", ctypes.c_char * 6),
        ("years", ctypes.c_ubyte),
        ("months", ctypes.c_ubyte),
        ("days", ctypes.c_ubyte),
        ("hours", ctypes.c_ubyte),
        ("mins", ctypes.c_ubyte),
        ("secs", ctypes.c_ubyte),
        ("frame", ctypes.c_ubyte),
    ]


# Function prototypes
_lib.ltc_decoder_create.restype = ctypes.c_void_p
_lib.ltc_decoder_create.argtypes = [ctypes.c_int, ctypes.c_int]

_lib.ltc_decoder_free.restype = ctypes.c_int
_lib.ltc_decoder_free.argtypes = [ctypes.c_void_p]

_lib.ltc_decoder_write_float.restype = None
_lib.ltc_decoder_write_float.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_size_t,
    ctypes.c_longlong,
]

_lib.ltc_decoder_read.restype = ctypes.c_int
_lib.ltc_decoder_read.argtypes = [ctypes.c_void_p, ctypes.POINTER(LTCFrameExt)]

_lib.ltc_frame_to_time.restype = None
_lib.ltc_frame_to_time.argtypes = [
    ctypes.POINTER(SMPTETimecode),
    ctypes.POINTER(LTCFrame),
    ctypes.c_int,
]


def decode_ltc_audio(audio_float32: np.ndarray, sample_rate: int, fps=30):
    """Decode float32 audio using libltc. Returns list of (h, m, s, f) tuples."""
    apv = int(sample_rate / fps)
    decoder = _lib.ltc_decoder_create(apv, 32)
    assert decoder, "Failed to create LTC decoder"

    try:
        buf = audio_float32.astype(np.float32)
        frames = []
        frame_ext = LTCFrameExt()

        # Feed in chunks to avoid queue overflow
        chunk_size = sample_rate  # 1 second at a time
        offset = 0
        while offset < len(buf):
            end = min(offset + chunk_size, len(buf))
            chunk = buf[offset:end]
            ptr = chunk.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            _lib.ltc_decoder_write_float(decoder, ptr, len(chunk), offset)

            # Read all decoded frames from queue
            while _lib.ltc_decoder_read(decoder, ctypes.byref(frame_ext)):
                tc = SMPTETimecode()
                _lib.ltc_frame_to_time(ctypes.byref(tc), ctypes.byref(frame_ext.ltc), 0)
                frames.append((tc.hours, tc.mins, tc.secs, tc.frame))

            offset = end

        return frames
    finally:
        _lib.ltc_decoder_free(decoder)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRealDecode:
    """Generate LTC with our encoder, decode with libltc, compare."""

    def test_30fps_ndf_basic(self):
        """30 NDF starting at 01:00:00:00 for 2 seconds — expect 60 frames."""
        config = LTCConfig(
            frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
            bit_depth=16, start_time=(1, 0, 0, 0), duration_seconds=2.0,
        )
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()

        decoded = decode_ltc_audio(audio, sr)
        assert len(decoded) >= 58, f"Expected ~60 frames, got {len(decoded)}"

        # First decoded frame should be 01:00:00:00
        assert decoded[0] == (1, 0, 0, 0), f"First frame: {decoded[0]}"
        # Last should be around 01:00:01:29
        assert decoded[-1] == (1, 0, 1, 29) or decoded[-1] == (1, 0, 1, 28), \
            f"Last frame: {decoded[-1]}"

        # Verify sequential increment
        for i in range(1, len(decoded)):
            prev = decoded[i - 1]
            curr = decoded[i]
            assert _next_tc(prev, 30) == curr, \
                f"Frame {i}: expected {_next_tc(prev, 30)} after {prev}, got {curr}"

    def test_25fps_ndf(self):
        """25 NDF (PAL) starting at 10:30:00:00 for 2 seconds."""
        config = LTCConfig(
            frame_rate=FrameRate.FR_25_NDF, sample_rate=48000,
            bit_depth=16, start_time=(10, 30, 0, 0), duration_seconds=2.0,
        )
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()

        decoded = decode_ltc_audio(audio, sr)
        assert len(decoded) >= 48, f"Expected ~50 frames, got {len(decoded)}"
        assert decoded[0] == (10, 30, 0, 0), f"First frame: {decoded[0]}"

        for i in range(1, len(decoded)):
            prev = decoded[i - 1]
            curr = decoded[i]
            assert _next_tc(prev, 25) == curr, \
                f"Frame {i}: expected {_next_tc(prev, 25)} after {prev}, got {curr}"

    def test_24fps_ndf(self):
        """24 NDF starting at 00:00:00:00 for 2 seconds."""
        config = LTCConfig(
            frame_rate=FrameRate.FR_24_NDF, sample_rate=48000,
            bit_depth=16, start_time=(0, 0, 0, 0), duration_seconds=2.0,
        )
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()

        decoded = decode_ltc_audio(audio, sr)
        assert len(decoded) >= 46, f"Expected ~48 frames, got {len(decoded)}"
        assert decoded[0] == (0, 0, 0, 0), f"First frame: {decoded[0]}"

    def test_2997_drop_frame(self):
        """29.97 DF — verify drop frame skip is decoded correctly."""
        # Start at 00:59:50:00, run 12 seconds to cross 01:00:00
        config = LTCConfig(
            frame_rate=FrameRate.FR_29_97_DF, sample_rate=48000,
            bit_depth=16, start_time=(0, 59, 50, 0), duration_seconds=12.0,
        )
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()

        decoded = decode_ltc_audio(audio, sr)
        assert len(decoded) > 300, f"Expected ~360 frames, got {len(decoded)}"

        # Check first frame
        assert decoded[0] == (0, 59, 50, 0), f"First frame: {decoded[0]}"

        # Verify the drop frame flag is set (check that frames skip correctly)
        # At minute boundaries (non-10th), frames 0 and 1 should be skipped
        for i in range(1, len(decoded)):
            prev = decoded[i - 1]
            curr = decoded[i]
            expected = _next_tc_df29(prev)
            assert curr == expected, \
                f"Frame {i}: after {prev} expected {expected}, got {curr}"

    def test_2997_df_minute_boundary_skip(self):
        """29.97 DF — specifically test that 00:00:59:29 -> 00:01:00:02."""
        config = LTCConfig(
            frame_rate=FrameRate.FR_29_97_DF, sample_rate=48000,
            bit_depth=16, start_time=(0, 0, 58, 0), duration_seconds=4.0,
        )
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()

        decoded = decode_ltc_audio(audio, sr)
        # Find the transition
        for i in range(1, len(decoded)):
            if decoded[i - 1] == (0, 0, 59, 29):
                assert decoded[i] == (0, 1, 0, 2), \
                    f"After 00:00:59:29 expected 00:01:00:02, got {_fmt(decoded[i])}"
                return
        pytest.fail("Never saw timecode 00:00:59:29 in decoded output")

    def test_midnight_wrap(self):
        """Test timecode wraps from 23:59:59:xx to 00:00:00:00."""
        config = LTCConfig(
            frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
            bit_depth=16, start_time=(23, 59, 58, 0), duration_seconds=4.0,
        )
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()

        decoded = decode_ltc_audio(audio, sr)
        found_wrap = False
        for i in range(1, len(decoded)):
            if decoded[i - 1] == (23, 59, 59, 29) and decoded[i] == (0, 0, 0, 0):
                found_wrap = True
                break
        assert found_wrap, "Midnight wrap not found in decoded output"

    def test_wav_file_decodable(self):
        """Generate a WAV file, read it back, decode it — full round-trip."""
        config = LTCConfig(
            frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
            bit_depth=16, start_time=(12, 0, 0, 0), duration_seconds=2.0,
        )
        gen = LTCGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            gen.export_wav(path)

            # Read WAV back
            with wave.open(path, "rb") as wf:
                assert wf.getnchannels() == 1
                n = wf.getnframes()
                raw = wf.readframes(n)
                sr = wf.getframerate()
                sw = wf.getsampwidth()

            if sw == 2:
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
            else:
                pytest.skip("24-bit WAV read not implemented in test")

            decoded = decode_ltc_audio(samples, sr)
            assert len(decoded) >= 58
            assert decoded[0] == (12, 0, 0, 0), f"First frame: {decoded[0]}"
        finally:
            os.unlink(path)

    def test_24bit_wav_decodable(self):
        """24-bit WAV round-trip decode test."""
        config = LTCConfig(
            frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
            bit_depth=24, start_time=(5, 30, 0, 0), duration_seconds=2.0,
        )
        gen = LTCGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            gen.export_wav(path)

            with wave.open(path, "rb") as wf:
                n = wf.getnframes()
                raw = wf.readframes(n)
                sr = wf.getframerate()

            # Decode 24-bit samples
            samples = np.zeros(n, dtype=np.float32)
            for i in range(n):
                b = raw[i * 3 : i * 3 + 3]
                val = struct.unpack("<i", b + (b"\xff" if b[2] & 0x80 else b"\x00"))[0]
                samples[i] = val / 8388607.0

            decoded = decode_ltc_audio(samples, sr)
            assert len(decoded) >= 58
            assert decoded[0] == (5, 30, 0, 0), f"First frame: {decoded[0]}"
        finally:
            os.unlink(path)

    def test_all_sample_rates(self):
        """Test decode works at 44100, 48000, 96000 Hz."""
        for sr in [44100, 48000, 96000]:
            config = LTCConfig(
                frame_rate=FrameRate.FR_30_NDF, sample_rate=sr,
                bit_depth=16, start_time=(1, 0, 0, 0), duration_seconds=1.0,
            )
            gen = LTCGenerator(config)
            audio, rate = gen.generate_ltc()
            decoded = decode_ltc_audio(audio, rate)
            assert len(decoded) >= 28, \
                f"At {sr}Hz: expected ~30 frames, got {len(decoded)}"
            assert decoded[0] == (1, 0, 0, 0), \
                f"At {sr}Hz: first frame {decoded[0]}"

    def test_long_duration_no_drift(self):
        """5 minutes of 30fps — verify no timing drift (last frame correct)."""
        config = LTCConfig(
            frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
            bit_depth=16, start_time=(0, 0, 0, 0), duration_seconds=300.0,
        )
        gen = LTCGenerator(config)
        audio, sr = gen.generate_ltc()
        decoded = decode_ltc_audio(audio, sr)

        # Should have ~9000 frames (300s * 30fps)
        assert len(decoded) >= 8998, f"Expected ~9000 frames, got {len(decoded)}"

        # Verify first and last
        assert decoded[0] == (0, 0, 0, 0)
        # Last frame should be around 00:04:59:29
        assert decoded[-1][0] == 0 and decoded[-1][1] == 4, \
            f"Last frame: {_fmt(decoded[-1])}"

        # Spot-check sequential correctness every 1000 frames
        for i in range(1000, len(decoded), 1000):
            prev = decoded[i - 1]
            curr = decoded[i]
            assert _next_tc(prev, 30) == curr, \
                f"Frame {i}: after {_fmt(prev)} expected {_fmt(_next_tc(prev, 30))}, got {_fmt(curr)}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(tc):
    return f"{tc[0]:02d}:{tc[1]:02d}:{tc[2]:02d}:{tc[3]:02d}"

def _next_tc(tc, fps):
    """Compute next timecode (NDF)."""
    h, m, s, f = tc
    f += 1
    if f >= fps:
        f = 0
        s += 1
        if s >= 60:
            s = 0
            m += 1
            if m >= 60:
                m = 0
                h += 1
                if h >= 24:
                    h = 0
    return (h, m, s, f)

def _next_tc_df29(tc):
    """Compute next timecode for 29.97 DF."""
    h, m, s, f = tc
    f += 1
    if f >= 30:
        f = 0
        s += 1
        if s >= 60:
            s = 0
            m += 1
            if m >= 60:
                m = 0
                h += 1
                if h >= 24:
                    h = 0
            # Drop frame: skip 0,1 at non-tenth minutes
            if m % 10 != 0:
                f = 2
    return (h, m, s, f)
