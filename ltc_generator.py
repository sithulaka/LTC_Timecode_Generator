import numpy as np
import wave
import struct
import logging
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Callable

logger = logging.getLogger(__name__)

# [3.5] Module-level constants — extract magic numbers
LTC_BITS_PER_FRAME = 80
LTC_SYNC_WORD = 0xBFFC
MAX_INT16 = 32767
MAX_INT24 = 8388607
MAX_INT32 = 2147483647

# [1.3] BCD lookup table — pre-computed 4-bit lists for digits 0-9
_BCD_TABLE = [
    [0, 0, 0, 0],  # 0
    [1, 0, 0, 0],  # 1
    [0, 1, 0, 0],  # 2
    [1, 1, 0, 0],  # 3
    [0, 0, 1, 0],  # 4
    [1, 0, 1, 0],  # 5
    [0, 1, 1, 0],  # 6
    [1, 1, 1, 0],  # 7
    [0, 0, 0, 1],  # 8
    [1, 0, 0, 1],  # 9
]

class FrameRate(Enum):
    """Standard international frame rates"""
    # Non-Drop Frame (NDF)
    FR_23_976_NDF = (24000, 1001, False, "23.976 fps NDF")  # 23.976 fps
    FR_24_NDF = (24, 1, False, "24 fps NDF")            # 24 fps
    FR_25_NDF = (25, 1, False, "25 fps NDF")            # 25 fps (PAL)
    FR_29_97_NDF = (30000, 1001, False, "29.97 fps NDF")   # 29.97 fps
    FR_30_NDF = (30, 1, False, "30 fps NDF")            # 30 fps
    FR_50_NDF = (50, 1, False, "50 fps NDF")            # 50 fps
    FR_59_94_NDF = (60000, 1001, False, "59.94 fps NDF")   # 59.94 fps
    FR_60_NDF = (60, 1, False, "60 fps NDF")            # 60 fps

    # Drop Frame (DF) - Only applicable to 29.97 and 59.94
    FR_29_97_DF = (30000, 1001, True, "29.97 fps DF")     # 29.97 fps Drop Frame
    FR_59_94_DF = (60000, 1001, True, "59.94 fps DF")     # 59.94 fps Drop Frame

    def get_fps(self) -> float:
        """Get actual frames per second"""
        return self.value[0] / self.value[1]

    def is_drop_frame(self) -> bool:
        """Check if this is drop frame format"""
        return self.value[2]

    def get_display_name(self) -> str:
        """Get display name for UI"""
        return self.value[3]

    @classmethod
    def get_frame_rate_by_name(cls, name: str):
        """Get frame rate enum by name"""
        for fr in cls:
            if fr.name == name:
                return fr
        raise ValueError(f"Frame rate '{name}' not found")

    @classmethod
    def get_all_frame_rates(cls):
        """Get all frame rates as a list of dictionaries for UI"""
        return [{"name": fr.name, "display": fr.get_display_name()} for fr in cls]

@dataclass
class LTCConfig:
    """LTC Generator Configuration"""
    frame_rate: FrameRate
    sample_rate: int  # 44100, 48000, 96000, 192000
    bit_depth: int    # 16, 24, 32
    start_time: Tuple[int, int, int, int]  # (hours, minutes, seconds, frames)
    duration_seconds: float
    user_bits: int = 0        # [2.2] 32-bit unsigned user bits
    channels: int = 1         # [2.4] 1=mono, 2=stereo

    def __post_init__(self):
        """Validate configuration parameters"""
        valid_sample_rates = [44100, 48000, 96000, 192000]
        if self.sample_rate not in valid_sample_rates:
            raise ValueError(f"Sample rate must be one of {valid_sample_rates}")

        if self.bit_depth not in [16, 24, 32]:
            raise ValueError("Bit depth must be 16, 24, or 32")

        if len(self.start_time) != 4:
            raise ValueError("Start time must be (hours, minutes, seconds, frames)")

        # Validate hours, minutes, seconds, frames
        hours, minutes, seconds, frames = self.start_time

        if hours < 0 or hours > 23:
            raise ValueError("Hours must be between 0 and 23")

        if minutes < 0 or minutes > 59:
            raise ValueError("Minutes must be between 0 and 59")

        if seconds < 0 or seconds > 59:
            raise ValueError("Seconds must be between 0 and 59")

        max_frames = round(self.frame_rate.get_fps())
        if frames < 0 or frames >= max_frames:
            raise ValueError(f"Frames must be between 0 and {max_frames-1}")

        if self.duration_seconds <= 0:
            raise ValueError("Duration must be greater than 0")

        # [2.2] Validate user_bits
        if not (0 <= self.user_bits <= 0xFFFFFFFF):
            raise ValueError("user_bits must be between 0 and 0xFFFFFFFF")

        # [2.4] Validate channels
        if self.channels not in [1, 2]:
            raise ValueError("Channels must be 1 (mono) or 2 (stereo)")

class LTCGenerator:
    """Professional LTC Timecode Generator"""

    def __init__(self, config: LTCConfig):
        self.config = config
        self.frame_duration_samples = int(self.config.sample_rate / config.frame_rate.get_fps())

    def generate_ltc(self) -> Tuple[np.ndarray, int]:
        """
        Generate complete LTC audio signal

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        logger.info(
            "LTC generation started: frame_rate=%s, sample_rate=%d, bit_depth=%d, "
            "start_time=%s, duration=%.2fs, user_bits=0x%08X, channels=%d",
            self.config.frame_rate.get_display_name(),
            self.config.sample_rate,
            self.config.bit_depth,
            self.config.start_time,
            self.config.duration_seconds,
            self.config.user_bits,
            self.config.channels,
        )

        total_samples = int(self.config.duration_seconds * self.config.sample_rate)
        audio_data = np.zeros(total_samples, dtype=np.float32)

        current_time = list(self.config.start_time)
        sample_pos = 0

        while sample_pos < total_samples:
            # Generate LTC word for current frame
            ltc_word = self._generate_ltc_word(current_time)

            # Convert to audio samples
            frame_audio = self._ltc_word_to_audio(ltc_word)

            # Add to output buffer
            end_pos = min(sample_pos + len(frame_audio), total_samples)
            audio_data[sample_pos:end_pos] = frame_audio[:end_pos - sample_pos]

            sample_pos += len(frame_audio)

            # Increment timecode
            self._increment_timecode(current_time)

        logger.info("LTC generation complete: %d samples generated", total_samples)

        return audio_data, self.config.sample_rate

    def _generate_ltc_word(self, timecode: List[int]) -> List[int]:
        """
        Generate 80-bit LTC word for given timecode

        SMPTE 12M 80-bit layout:
        Bits 0-3:   frame_units (4 bits BCD)
        Bits 4-7:   UB1 (user bits group 1, 4 bits)
        Bits 8-9:   frame_tens (2 bits BCD)
        Bit 10:     drop frame flag
        Bit 11:     color frame flag
        Bits 12-15: UB2 (user bits group 2, 4 bits)
        Bits 16-19: seconds_units (4 bits BCD)
        Bits 20-23: UB3 (user bits group 3, 4 bits)
        Bits 24-26: seconds_tens (3 bits BCD)
        Bit 27:     BGF0 (polarity correction bit)
        Bits 28-31: UB4 (user bits group 4, 4 bits)
        Bits 32-35: minutes_units (4 bits BCD)
        Bits 36-39: UB5 (user bits group 5, 4 bits)
        Bits 40-42: minutes_tens (3 bits BCD)
        Bit 43:     BGF2 (binary group flag, zero)
        Bits 44-47: UB6 (user bits group 6, 4 bits)
        Bits 48-51: hours_units (4 bits BCD)
        Bits 52-55: UB7 (user bits group 7, 4 bits)
        Bits 56-57: hours_tens (2 bits BCD)
        Bit 58:     BGF1 (binary group flag, zero)
        Bit 59:     reserved (zero)
        Bits 60-63: UB8 (user bits group 8, 4 bits)
        Bits 64-79: sync word (16 bits)
        """

        hours, minutes, seconds, frames = timecode

        # Apply drop frame compensation if needed
        if self.config.frame_rate.is_drop_frame():
            frames = self._apply_drop_frame(hours, minutes, seconds, frames)

        ltc_word = [0] * LTC_BITS_PER_FRAME

        # [1.3] Use BCD lookup table instead of per-frame bit shifting

        # Bits 0-3: Frame units (4 bits BCD)
        frame_units = frames % 10
        ltc_word[0:4] = _BCD_TABLE[frame_units]

        # Bits 8-9: Frame tens (2 bits BCD)
        frame_tens = frames // 10
        ltc_word[8:10] = _BCD_TABLE[frame_tens][:2]

        # Bit 10: Drop frame flag
        ltc_word[10] = 1 if self.config.frame_rate.is_drop_frame() else 0

        # Bit 11: Color frame flag (zero)

        # Bits 16-19: Seconds units (4 bits BCD)
        seconds_units = seconds % 10
        ltc_word[16:20] = _BCD_TABLE[seconds_units]

        # Bits 24-26: Seconds tens (3 bits BCD)
        seconds_tens = seconds // 10
        ltc_word[24:27] = _BCD_TABLE[seconds_tens][:3]

        # Bit 27: BGF0 / polarity correction — set below after counting ones

        # Bits 32-35: Minutes units (4 bits BCD)
        minutes_units = minutes % 10
        ltc_word[32:36] = _BCD_TABLE[minutes_units]

        # Bits 40-42: Minutes tens (3 bits BCD)
        minutes_tens = minutes // 10
        ltc_word[40:43] = _BCD_TABLE[minutes_tens][:3]

        # Bit 43: BGF2 (zero)

        # Bits 48-51: Hours units (4 bits BCD)
        hours_units = hours % 10
        ltc_word[48:52] = _BCD_TABLE[hours_units]

        # Bits 56-57: Hours tens (2 bits BCD)
        hours_tens = hours // 10
        ltc_word[56:58] = _BCD_TABLE[hours_tens][:2]

        # Bit 58: BGF1 (zero)
        # Bit 59: reserved (zero)

        # [2.2] Write user bits (UB1-UB8) from config.user_bits
        ub = self.config.user_bits
        # UB1 (bits 4-7): lowest 4 bits of user_bits
        for i in range(4):
            ltc_word[4 + i] = (ub >> i) & 1
        # UB2 (bits 12-15)
        for i in range(4):
            ltc_word[12 + i] = (ub >> (4 + i)) & 1
        # UB3 (bits 20-23)
        for i in range(4):
            ltc_word[20 + i] = (ub >> (8 + i)) & 1
        # UB4 (bits 28-31)
        for i in range(4):
            ltc_word[28 + i] = (ub >> (12 + i)) & 1
        # UB5 (bits 36-39)
        for i in range(4):
            ltc_word[36 + i] = (ub >> (16 + i)) & 1
        # UB6 (bits 44-47)
        for i in range(4):
            ltc_word[44 + i] = (ub >> (20 + i)) & 1
        # UB7 (bits 52-55)
        for i in range(4):
            ltc_word[52 + i] = (ub >> (24 + i)) & 1
        # UB8 (bits 60-63)
        for i in range(4):
            ltc_word[60 + i] = (ub >> (28 + i)) & 1

        # Polarity correction bit (bit 27) — recalculate AFTER setting user bits
        # Count ones in bits 0-63 (with bit 27 currently 0), set bit 27 to make total even
        ltc_word[27] = 0
        ones_count = sum(ltc_word[0:64])
        if ones_count % 2 != 0:
            ltc_word[27] = 1

        # Bits 64-79: Sync word (SMPTE pattern in transmission order)
        for i in range(16):
            ltc_word[64 + i] = (LTC_SYNC_WORD >> i) & 1

        return ltc_word

    def _ltc_word_to_audio(self, ltc_word: List[int]) -> np.ndarray:
        """
        Convert LTC word to bi-phase mark encoded audio

        Bi-phase mark encoding (per SMPTE 12M):
        - Always transition at the START of each bit period
        - '1' bit: additional transition at bit midpoint
        - '0' bit: no transition at bit midpoint

        Uses fractional accumulator to avoid sample drift (Issue #8).
        """
        fds = self.frame_duration_samples
        audio_samples = np.zeros(fds, dtype=np.float32)

        current_level = -1.0

        for bit_index, bit_value in enumerate(ltc_word):
            start_sample = round(bit_index * fds / LTC_BITS_PER_FRAME)
            end_sample = round((bit_index + 1) * fds / LTC_BITS_PER_FRAME)
            mid_sample = (start_sample + end_sample) // 2

            # Always transition at start of bit period
            current_level = -current_level

            # Fill first half of bit period
            audio_samples[start_sample:mid_sample] = current_level

            if bit_value == 1:
                # Additional transition at midpoint for '1'
                current_level = -current_level

            # Fill second half of bit period
            audio_samples[mid_sample:end_sample] = current_level

        return audio_samples

    def _apply_drop_frame(self, hours: int, minutes: int, seconds: int, frames: int) -> int:
        """
        Apply drop frame compensation for 29.97 and 59.94 fps

        Drop frame rules:
        - 29.97 DF: skip frames 0-1 at the start of each minute (except every 10th)
        - 59.94 DF: skip frames 0-3 at the start of each minute (except every 10th)
        """
        if not self.config.frame_rate.is_drop_frame():
            return frames

        if self.config.frame_rate == FrameRate.FR_29_97_DF:
            if seconds == 0 and frames < 2 and minutes % 10 != 0:
                logger.debug(
                    "Drop frame adjustment: %02d:%02d:%02d:%02d -> frame %d",
                    hours, minutes, seconds, frames, frames + 2,
                )
                return frames + 2
        elif self.config.frame_rate == FrameRate.FR_59_94_DF:
            if seconds == 0 and frames < 4 and minutes % 10 != 0:
                logger.debug(
                    "Drop frame adjustment: %02d:%02d:%02d:%02d -> frame %d",
                    hours, minutes, seconds, frames, frames + 4,
                )
                return frames + 4

        return frames

    def _increment_timecode(self, timecode: List[int]):
        """Increment timecode by one frame"""
        max_frames = round(self.config.frame_rate.get_fps())

        timecode[3] += 1  # frames

        if timecode[3] >= max_frames:
            timecode[3] = 0
            timecode[2] += 1  # seconds

            if timecode[2] >= 60:
                timecode[2] = 0
                timecode[1] += 1  # minutes

                if timecode[1] >= 60:
                    timecode[1] = 0
                    timecode[0] += 1  # hours

                    if timecode[0] >= 24:
                        timecode[0] = 0

        # Issue #19: Apply drop frame skip after incrementing to frame 0 of a new second
        if self.config.frame_rate.is_drop_frame() and timecode[2] == 0 and timecode[1] % 10 != 0:
            if self.config.frame_rate == FrameRate.FR_29_97_DF:
                if timecode[3] == 0:
                    timecode[3] = 2
            elif self.config.frame_rate == FrameRate.FR_59_94_DF:
                if timecode[3] == 0:
                    timecode[3] = 4

    def export_wav(self, filename: str):
        """Export LTC as WAV file"""
        audio_data, sample_rate = self.generate_ltc()

        # Scale and convert to integer format
        if self.config.bit_depth == 16:
            audio_int = (audio_data * MAX_INT16).astype(np.int16)
            sample_width = 2
        elif self.config.bit_depth == 24:
            audio_int = (audio_data * MAX_INT24).astype(np.int32)
            sample_width = 3
        else:  # 32-bit
            scaled = (audio_data * np.float64(MAX_INT32))
            audio_int = np.clip(scaled, -MAX_INT32, MAX_INT32).astype(np.int32)
            sample_width = 4

        # [2.4] Stereo duplication
        if self.config.channels == 2:
            if self.config.bit_depth == 16:
                audio_int = np.column_stack([audio_int, audio_int]).ravel()
            elif self.config.bit_depth == 32:
                audio_int = np.column_stack([audio_int, audio_int]).ravel()
            # For 24-bit, stereo interleaving is handled after byte conversion

        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(self.config.channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)

            if self.config.bit_depth == 16:
                wav_file.writeframes(audio_int.tobytes())
            elif self.config.bit_depth == 24:
                # [1.1] Vectorized 24-bit WAV export
                raw = audio_int.astype('<i4').tobytes()
                raw_bytes = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 4)[:, :3]
                if self.config.channels == 2:
                    # Interleave: duplicate each sample's 3 bytes
                    mono_frames = raw_bytes  # shape (N, 3)
                    stereo_frames = np.column_stack([mono_frames, mono_frames]).reshape(-1, 3)
                    wav_file.writeframes(stereo_frames.tobytes())
                else:
                    wav_file.writeframes(raw_bytes.tobytes())
            else:  # 32-bit
                wav_file.writeframes(audio_int.tobytes())

        file_size = os.path.getsize(filename)
        logger.info("WAV exported: %s (%d bytes)", filename, file_size)

    def export_wav_streaming(self, filename: str, progress_callback: Optional[Callable[[float], None]] = None):
        """
        [9.1] Streaming export — generates and writes one frame at a time
        without holding all audio in memory.

        Args:
            filename: Output WAV file path.
            progress_callback: Optional callable receiving percent (0-100) every 100 frames.
        """
        total_samples = int(self.config.duration_seconds * self.config.sample_rate)
        fps = self.config.frame_rate.get_fps()
        total_frames = int(self.config.duration_seconds * fps)

        # Determine sample width and scaling
        if self.config.bit_depth == 16:
            max_val = MAX_INT16
            sample_width = 2
        elif self.config.bit_depth == 24:
            max_val = MAX_INT24
            sample_width = 3
        else:  # 32
            max_val = MAX_INT32
            sample_width = 4

        logger.info(
            "Streaming WAV export started: %s, %d estimated frames",
            filename, total_frames,
        )

        current_time = list(self.config.start_time)
        sample_pos = 0
        frame_count = 0

        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(self.config.channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(self.config.sample_rate)

            while sample_pos < total_samples:
                ltc_word = self._generate_ltc_word(current_time)
                frame_audio = self._ltc_word_to_audio(ltc_word)

                # Trim last frame if it extends beyond total_samples
                remaining = total_samples - sample_pos
                if len(frame_audio) > remaining:
                    frame_audio = frame_audio[:remaining]

                # Convert to integer samples
                if self.config.bit_depth == 16:
                    frame_int = (frame_audio * max_val).astype(np.int16)
                    if self.config.channels == 2:
                        frame_int = np.column_stack([frame_int, frame_int]).ravel()
                    wav_file.writeframes(frame_int.tobytes())
                elif self.config.bit_depth == 24:
                    frame_int = (frame_audio * max_val).astype(np.int32)
                    raw = frame_int.astype('<i4').tobytes()
                    raw_bytes = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 4)[:, :3]
                    if self.config.channels == 2:
                        raw_bytes = np.column_stack([raw_bytes, raw_bytes]).reshape(-1, 3)
                    wav_file.writeframes(raw_bytes.tobytes())
                else:  # 32-bit
                    frame_int = np.clip(frame_audio * max_val, -max_val, max_val).astype(np.int32)
                    if self.config.channels == 2:
                        frame_int = np.column_stack([frame_int, frame_int]).ravel()
                    wav_file.writeframes(frame_int.tobytes())

                sample_pos += len(frame_audio)
                frame_count += 1
                self._increment_timecode(current_time)

                if progress_callback and frame_count % 100 == 0:
                    percent = min(sample_pos / total_samples * 100.0, 100.0)
                    progress_callback(percent)

        if progress_callback:
            progress_callback(100.0)

        file_size = os.path.getsize(filename)
        logger.info("Streaming WAV export complete: %s (%d bytes, %d frames)", filename, file_size, frame_count)

# Usage Example
def main():
    """Example usage of LTC Generator"""

    # Configuration
    config = LTCConfig(
        frame_rate=FrameRate.FR_29_97_DF,  # 29.97 fps Drop Frame
        sample_rate=48000,                  # 48 kHz
        bit_depth=24,                      # 24-bit
        start_time=(10, 30, 15, 0),        # 10:30:15:00
        duration_seconds=60.0              # 1 minute
    )

    # Generate LTC
    generator = LTCGenerator(config)
    generator.export_wav("ltc_timecode.wav")
    print(f"Generated LTC timecode: {config.start_time[0]:02d}:{config.start_time[1]:02d}:{config.start_time[2]:02d}:{config.start_time[3]:02d}")
    print(f"Frame rate: {config.frame_rate.get_fps():.3f} fps {'(Drop Frame)' if config.frame_rate.is_drop_frame() else '(Non-Drop Frame)'}")
    print(f"Sample rate: {config.sample_rate} Hz")
    print(f"Bit depth: {config.bit_depth} bits")
    print(f"Duration: {config.duration_seconds} seconds")

if __name__ == "__main__":
    main()
