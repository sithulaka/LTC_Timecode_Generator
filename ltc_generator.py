import numpy as np
import wave
import struct
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, List

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
    bit_depth: int    # 16, 24
    start_time: Tuple[int, int, int, int]  # (hours, minutes, seconds, frames)
    duration_seconds: float
    
    def __post_init__(self):
        """Validate configuration parameters"""
        valid_sample_rates = [44100, 48000, 96000, 192000]
        if self.sample_rate not in valid_sample_rates:
            raise ValueError(f"Sample rate must be one of {valid_sample_rates}")
        
        if self.bit_depth not in [16, 24]:
            raise ValueError("Bit depth must be 16 or 24")
        
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
            
        max_frames = int(self.frame_rate.get_fps())
        if frames < 0 or frames >= max_frames:
            raise ValueError(f"Frames must be between 0 and {max_frames-1}")
            
        if self.duration_seconds <= 0:
            raise ValueError("Duration must be greater than 0")

class LTCGenerator:
    """Professional LTC Timecode Generator"""
    
    def __init__(self, config: LTCConfig):
        self.config = config
        self.frame_duration_samples = int(self.config.sample_rate / config.frame_rate.get_fps())
        self.bit_duration_samples = self.frame_duration_samples // 80  # 80 bits per frame
        
    def generate_ltc(self) -> Tuple[np.ndarray, int]:
        """
        Generate complete LTC audio signal
        
        Returns:
            Tuple of (audio_data, sample_rate)
        """
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
        
        return audio_data, self.config.sample_rate
    
    def _generate_ltc_word(self, timecode: List[int]) -> List[int]:
        """
        Generate 80-bit LTC word for given timecode
        
        LTC Word Structure (80 bits):
        - Frame units (4 bits)
        - User bits 1 (4 bits)  
        - Frame tens (2 bits)
        - Drop frame flag (1 bit)
        - Color frame flag (1 bit)
        - Seconds units (4 bits)
        - User bits 2 (4 bits)
        - Seconds tens (3 bits)
        - Binary group flag (1 bit)
        - Minutes units (4 bits)
        - User bits 3 (4 bits)
        - Minutes tens (3 bits)
        - Binary group flag (1 bit)
        - Hours units (4 bits)
        - User bits 4 (4 bits)
        - Hours tens (2 bits)
        - Binary group flag (1 bit)
        - Polarity correction (1 bit)
        - Sync word (16 bits) - 0x3FFD
        """
        
        hours, minutes, seconds, frames = timecode
        
        # Apply drop frame compensation if needed
        if self.config.frame_rate.is_drop_frame():
            frames = self._apply_drop_frame(hours, minutes, seconds, frames)
        
        ltc_word = [0] * 80
        bit_pos = 0
        
        # Frame units (4 bits)
        frame_units = frames % 10
        for i in range(4):
            ltc_word[bit_pos + i] = (frame_units >> i) & 1
        bit_pos += 4
        
        # User bits 1 (4 bits) - typically zero
        bit_pos += 4
        
        # Frame tens (2 bits)
        frame_tens = frames // 10
        for i in range(2):
            ltc_word[bit_pos + i] = (frame_tens >> i) & 1
        bit_pos += 2
        
        # Drop frame flag
        ltc_word[bit_pos] = 1 if self.config.frame_rate.is_drop_frame() else 0
        bit_pos += 1
        
        # Color frame flag (typically 0)
        bit_pos += 1
        
        # Seconds units (4 bits)
        seconds_units = seconds % 10
        for i in range(4):
            ltc_word[bit_pos + i] = (seconds_units >> i) & 1
        bit_pos += 4
        
        # User bits 2 (4 bits)
        bit_pos += 4
        
        # Seconds tens (3 bits)
        seconds_tens = seconds // 10
        for i in range(3):
            ltc_word[bit_pos + i] = (seconds_tens >> i) & 1
        bit_pos += 3
        
        # Binary group flag
        bit_pos += 1
        
        # Minutes units (4 bits)
        minutes_units = minutes % 10
        for i in range(4):
            ltc_word[bit_pos + i] = (minutes_units >> i) & 1
        bit_pos += 4
        
        # User bits 3 (4 bits)
        bit_pos += 4
        
        # Minutes tens (3 bits)
        minutes_tens = minutes // 10
        for i in range(3):
            ltc_word[bit_pos + i] = (minutes_tens >> i) & 1
        bit_pos += 3
        
        # Binary group flag
        bit_pos += 1
        
        # Hours units (4 bits)
        hours_units = hours % 10
        for i in range(4):
            ltc_word[bit_pos + i] = (hours_units >> i) & 1
        bit_pos += 4
        
        # User bits 4 (4 bits)
        bit_pos += 4
        
        # Hours tens (2 bits)
        hours_tens = hours // 10
        for i in range(2):
            ltc_word[bit_pos + i] = (hours_tens >> i) & 1
        bit_pos += 2
        
        # Binary group flag
        bit_pos += 1
        
        # Polarity correction bit (typically 0)
        bit_pos += 1
        
        # Sync word: 0x3FFD (0011111111111101)
        sync_word = 0x3FFD
        for i in range(16):
            ltc_word[bit_pos + i] = (sync_word >> i) & 1
        
        return ltc_word
    
    def _ltc_word_to_audio(self, ltc_word: List[int]) -> np.ndarray:
        """
        Convert LTC word to bi-phase mark encoded audio
        
        Bi-phase mark encoding:
        - '0' bit: no transition at bit boundary
        - '1' bit: transition at bit boundary
        - Clock transitions occur at bit center
        """
        audio_samples = np.zeros(self.frame_duration_samples, dtype=np.float32)
        
        current_level = 1.0  # Start with positive level
        
        for bit_index, bit_value in enumerate(ltc_word):
            start_sample = bit_index * self.bit_duration_samples
            end_sample = start_sample + self.bit_duration_samples
            
            if bit_value == 1:
                # Transition at bit boundary for '1'
                current_level = -current_level
            
            # Fill first half of bit period
            mid_sample = start_sample + self.bit_duration_samples // 2
            audio_samples[start_sample:mid_sample] = current_level
            
            # Clock transition at bit center (always occurs)
            current_level = -current_level
            audio_samples[mid_sample:end_sample] = current_level
        
        return audio_samples
    
    def _apply_drop_frame(self, hours: int, minutes: int, seconds: int, frames: int) -> int:
        """
        Apply drop frame compensation for 29.97 and 59.94 fps
        
        Drop frame rules:
        - Skip frames 00 and 01 at the start of each minute
        - Except for minutes 00, 10, 20, 30, 40, 50 (every 10th minute)
        """
        if not self.config.frame_rate.is_drop_frame():
            return frames
            
        # Only apply to 29.97 and 59.94 fps
        if self.config.frame_rate in [FrameRate.FR_29_97_DF, FrameRate.FR_59_94_DF]:
            if seconds == 0 and frames < 2 and minutes % 10 != 0:
                # Skip frames 00 and 01
                return frames + 2
        
        return frames
    
    def _increment_timecode(self, timecode: List[int]):
        """Increment timecode by one frame"""
        max_frames = int(self.config.frame_rate.get_fps())
        
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
    
    def export_wav(self, filename: str):
        """Export LTC as WAV file"""
        audio_data, sample_rate = self.generate_ltc()
        
        # Scale and convert to integer format
        if self.config.bit_depth == 16:
            max_val = 32767
            audio_int = (audio_data * max_val).astype(np.int16)
            sample_width = 2
        else:  # 24-bit
            max_val = 8388607
            audio_int = (audio_data * max_val).astype(np.int32)
            sample_width = 3
        
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            
            if self.config.bit_depth == 16:
                wav_file.writeframes(audio_int.tobytes())
            else:  # 24-bit
                # Convert 32-bit to 24-bit
                audio_24bit = bytearray()
                for sample in audio_int:
                    audio_24bit.extend(struct.pack('<i', sample)[:3])
                wav_file.writeframes(bytes(audio_24bit))

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
