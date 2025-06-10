import eel
import os
import sys
import json
from pathlib import Path
from ltc_generator import FrameRate, LTCConfig, LTCGenerator

# Set web files folder
eel.init('web')

@eel.expose
def get_frame_rates():
    """Get all available frame rates for the UI"""
    return FrameRate.get_all_frame_rates()

@eel.expose
def get_sample_rates():
    """Get all available sample rates for the UI"""
    return [44100, 48000, 96000, 192000]

@eel.expose
def get_bit_depths():
    """Get all available bit depths for the UI"""
    return [16, 24]

@eel.expose
def generate_ltc(frame_rate_name, sample_rate, bit_depth, 
                 hours, minutes, seconds, frames, duration, output_path):
    """Generate LTC timecode file"""
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
        
        # Get frame rate enum from name
        frame_rate = FrameRate.get_frame_rate_by_name(frame_rate_name)
        
        # Validate frame number against frame rate
        max_frames = int(frame_rate.get_fps())
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
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Generate LTC file
        generator.export_wav(output_path)
        
        # Return success
        return {
            "success": True,
            "message": f"Generated LTC timecode file: {output_path}",
            "file_path": output_path
        }
    except Exception as e:
        # Return error
        return {
            "success": False,
            "message": f"Error generating LTC: {str(e)}"
        }

@eel.expose
def get_default_output_path():
    """Get default output path based on user's desktop"""
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    return os.path.join(desktop_path, "ltc_timecode.wav")

@eel.expose
def generate_filename(hours, minutes, seconds, frames, duration, frame_rate_name, bit_depth, sample_rate, preroll=False):
    """Generate a filename based on the parameters"""
    try:
        # Format time components
        time_str = f"{hours:02d}-{minutes:02d}-{seconds:02d}-{frames:02d}"
        
        # Format duration
        duration_mins = int(duration // 60)
        duration_secs = int(duration % 60)
        duration_str = f"{duration_mins}m{duration_secs:02d}s"
        
        # Get frame rate display name and format it
        frame_rate = FrameRate.get_frame_rate_by_name(frame_rate_name)
        fps_str = frame_rate.get_display_name().replace(' ', '').lower().replace('fps', 'fps')
        
        # Format sample rate
        if sample_rate >= 1000:
            sample_rate_str = f"{sample_rate // 1000}khz"
        else:
            sample_rate_str = f"{sample_rate}hz"
        
        # Build filename
        filename = f"LTC_{time_str}_{duration_str}_{fps_str}_{bit_depth}bit_{sample_rate_str}"
        
        if preroll:
            filename += "_preroll"
        
        filename += ".wav"
        
        return filename
    except Exception as e:
        return f"ltc_timecode_{int(duration)}s.wav"

@eel.expose
def browse_output_path():
    """
    Tell the JavaScript to handle file dialog using the browser's native dialogs
    We'll use a workaround since Eel doesn't directly support file dialogs
    """
    return "USE_JS_DIALOG"

@eel.expose
def browse_output_folder():
    """
    Tell the JavaScript to handle folder dialog using the browser's capabilities
    We'll use a workaround since Eel doesn't directly support folder dialogs
    """
    return "USE_JS_DIALOG"

def main():
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
