import eel
import os
import sys
import logging
import threading
from ltc_generator import FrameRate, LTCConfig, LTCGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_generation_lock = threading.Lock()


@eel.expose
def get_frame_rates() -> list:
    """Get all available frame rates for the UI"""
    return FrameRate.get_all_frame_rates()


@eel.expose
def get_sample_rates() -> list:
    """Get all available sample rates for the UI"""
    return [44100, 48000, 96000, 192000]


@eel.expose
def get_bit_depths() -> list:
    """Get all available bit depths for the UI"""
    return [16, 24]


@eel.expose
def generate_ltc(frame_rate_name: str, sample_rate: int, bit_depth: int,
                 hours: int, minutes: int, seconds: int, frames: int,
                 duration: float, output_path: str) -> dict:
    """Generate LTC timecode file"""
    logger.info("LTC generation requested: frame_rate=%s, sample_rate=%s, "
                "bit_depth=%s, start=%02d:%02d:%02d:%02d, duration=%s, output=%s",
                frame_rate_name, sample_rate, bit_depth,
                int(hours), int(minutes), int(seconds), int(frames),
                duration, output_path)

    if not _generation_lock.acquire(blocking=False):
        logger.warning("Generation rejected: another generation is already in progress")
        return {
            "success": False,
            "message": "Another generation is already in progress. Please wait."
        }

    try:
        # Convert parameters to appropriate types
        sample_rate = int(sample_rate)
        bit_depth = int(bit_depth)
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds)
        frames = int(frames)
        duration = float(duration)

        # Validate inputs
        if duration <= 0:
            raise ValueError("Duration must be greater than 0")

        if duration > 7200:  # 2 hours in seconds
            raise ValueError("Duration cannot exceed 2 hours")

        # Validate output path is within user home directory
        resolved = os.path.abspath(output_path)
        home = os.path.expanduser("~")
        if not resolved.startswith(home):
            raise ValueError("Output path must be within user home directory")

        # Get frame rate enum from name
        frame_rate = FrameRate.get_frame_rate_by_name(frame_rate_name)

        # Validate frame number against frame rate
        max_frames = round(frame_rate.get_fps())
        if frames >= max_frames:
            raise ValueError(f"Frame number must be less than {max_frames} for {frame_rate.get_display_name()}")

        # Create configuration
        config = LTCConfig(
            frame_rate=frame_rate,
            sample_rate=sample_rate,
            bit_depth=bit_depth,
            start_time=(hours, minutes, seconds, frames),
            duration_seconds=duration
        )

        # Create generator
        generator = LTCGenerator(config)

        # Make sure output directory exists
        os.makedirs(os.path.dirname(resolved), exist_ok=True)

        # Generate LTC file
        try:
            generator.export_wav(output_path)
        except Exception:
            # Clean up partial file on failure
            if os.path.exists(output_path):
                os.remove(output_path)
            raise

        logger.info("LTC generation successful: %s", output_path)

        # Return success
        return {
            "success": True,
            "message": f"Generated LTC timecode file: {output_path}",
            "file_path": output_path
        }
    except (ValueError, IOError, OSError) as e:
        logger.error("LTC generation failed: %s", e)
        # Return error
        return {
            "success": False,
            "message": f"Error generating LTC: {str(e)}"
        }
    finally:
        _generation_lock.release()


@eel.expose
def browse_save_path() -> str:
    """Open a file dialog for choosing where to save the LTC file"""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.asksaveasfilename(
        defaultextension=".wav",
        filetypes=[("WAV files", "*.wav")],
        title="Save LTC File"
    )
    root.destroy()
    return path or ""


@eel.expose
def get_default_output_path() -> str:
    """Get default output path based on user's desktop"""
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    return os.path.join(desktop_path, "ltc_timecode.wav")


def main() -> None:
    """Main application entry point"""
    try:
        # Set configuration options
        eel.init('web')

        # Start Eel with Chrome (or default browser if Chrome not found)
        eel.start('index.html', size=(1000, 700))
    except EnvironmentError:
        # If Chrome isn't found, fallback to Microsoft Edge on Windows
        if sys.platform in ['win32', 'win64']:
            eel.start('index.html', mode='edge')
        else:
            # Fallback to the default browser
            eel.start('index.html', mode='default')


if __name__ == "__main__":
    main()
