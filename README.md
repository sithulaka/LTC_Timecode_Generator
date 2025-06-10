# LTC Timecode Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/sithulaka/LTC_Timecode_Generator)](https://github.com/sithulaka/LTC_Timecode_Generator/releases)

A professional Linear Time Code (LTC) generator with a modern web-based user interface. This application generates SMPTE-compliant LTC audio files for broadcast and post-production use.

## 🚀 Quick Start

**Download the ready-to-use executable from the [Releases](https://github.com/sithulaka/LTC_Timecode_Generator/releases) page - no installation required!**

For Windows users, simply download `LTC_Timecode_Generator.exe` and run it directly.

## Features

- **Professional SMPTE Compliance**: Generates industry-standard LTC audio signals
- **Multiple Frame Rates**: Support for all standard broadcast frame rates including drop-frame
- **High-Quality Audio**: 16/24-bit depth at various sample rates (44.1kHz to 192kHz)
- **Modern Web UI**: Clean, responsive interface built with HTML5, CSS3, and JavaScript
- **Real-time Preview**: Live filename preview based on your settings
- **Pre-roll Support**: Optional 10-second pre-roll before main timecode
- **Cross-Platform**: Runs on Windows, macOS, and Linux

## Supported Formats

### Frame Rates
- 23.976 fps (Non-Drop Frame)
- 24 fps (Non-Drop Frame)
- 25 fps (PAL - Non-Drop Frame)
- 29.97 fps (Non-Drop Frame & Drop Frame)
- 30 fps (Non-Drop Frame)
- 50 fps (Non-Drop Frame)
- 59.94 fps (Non-Drop Frame & Drop Frame)
- 60 fps (Non-Drop Frame)

### Audio Specifications
- **Sample Rates**: 44.1 kHz, 48 kHz, 96 kHz, 192 kHz
- **Bit Depths**: 16-bit, 24-bit
- **Format**: Mono WAV files
- **Encoding**: Bi-phase mark encoding (Manchester encoding)

## Installation Options

### Option 1: Download Executable (Recommended)
1. Go to the [Releases](https://github.com/sithulaka/LTC-Timecode-Generator/releases) page
2. Download `LTC_Timecode_Generator.exe` for Windows
3. Run the executable directly - no installation needed!

### Option 2: Run from Source
1. **Clone this repository**:
   ```bash
   git clone https://github.com/sithulaka/LTC-Timecode-Generator.git
   cd LTC-Timecode-Generator
   ```
2. **Install Python 3.7 or higher**
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **The application will open in your default web browser**

3. **Configure your LTC parameters**:
   - **Start Time**: Set hours, minutes, seconds, and frames (hh:mm:ss:ff)
   - **Duration**: Specify length in minutes (0.1 to 120 minutes)
   - **Frame Rate**: Choose from available SMPTE frame rates
   - **Audio Format**: Select bit depth and sample rate
   - **Pre-roll**: Optionally add 10 seconds before start time

4. **Generate the file**: Click "Generate & Download LTC" and the WAV file will be created

## File Naming Convention

Generated files follow this naming pattern:
```
LTC_[start-time]_[duration]_[frame-rate]_[bit-depth]_[sample-rate][_preroll].wav
```

Example: `LTC_01-00-00-00_10m00s_30fpsndf_16bit_48khz.wav`

## Technical Details

### LTC Signal Structure
- **80 bits per frame** containing:
  - Timecode data (hours, minutes, seconds, frames)
  - User bits (available for custom data)
  - Control flags (drop frame, color frame)
  - Sync word (0x3FFD)

### Audio Characteristics
- **Signal Type**: Square wave alternating between positive and negative levels
- **Encoding**: Bi-phase mark (Manchester) encoding
- **Frequency Range**: Varies with frame rate (typically 960-4800 Hz)
- **Amplitude**: Full-scale audio signal

### Standards Compliance
- **SMPTE 12M**: Time and Control Code standard
- **IEC 60461**: Timecode for audio systems
- **ITU-R BR.780**: Timecode systems for broadcasting

## Professional Software Compatibility

Generated LTC files are compatible with:
- Avid Pro Tools
- Adobe Premiere Pro/After Effects
- DaVinci Resolve
- Professional hardware sync generators

## Drop Frame Timecode

For 29.97 fps and 59.94 fps drop frame formats:
- Frames 00 and 01 are skipped at the start of each minute
- Exception: Every 10th minute (00, 10, 20, 30, 40, 50) - no frames are skipped
- This compensates for the difference between nominal and actual frame rates

## Troubleshooting

### Common Issues

1. **Application won't start**:
   - Ensure Python 3.7+ is installed
   - Install all dependencies: `pip install -r requirements.txt`
   - Check if port 8000 is available

2. **Browser doesn't open automatically**:
   - Manually navigate to `http://localhost:8000`
   - Try a different browser

3. **File generation fails**:
   - Check disk space
   - Ensure write permissions to output directory
   - Verify input parameters are within valid ranges

4. **Audio playback issues**:
   - LTC is not meant for standard audio playback
   - Use professional audio software or timecode readers
   - Signal appears as digital noise in consumer players

### Performance Notes

- Large duration files (>60 minutes) may take time to generate
- Higher sample rates increase file size and generation time
- 24-bit files are roughly 50% larger than 16-bit files

## Development

### Project Structure
```
LTC_Timecode_Generator/
├── app.py                      # Eel backend application
├── ltc_generator.py           # Core LTC generation logic
├── requirements.txt           # Python dependencies
├── web/                      # Frontend assets
│   ├── index.html           # Main UI
│   ├── styles.css           # Styling
│   └── script.js            # Frontend logic
└── README.md                # This file
```
### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sithulaka/LTC-Timecode-Generator.git
   cd LTC-Timecode-Generator
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

## License

This project is provided as-is for educational and professional use. Please ensure compliance with local broadcast standards and regulations when using generated timecode in professional environments.

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing style conventions
- New features include appropriate error handling
- Changes maintain SMPTE compliance
- Updates to documentation as needed

## Technical Support

For technical issues or questions about LTC implementation, please refer to:
- SMPTE standards documentation
- Professional audio engineering resources
- Broadcast engineering communities

A professional-grade Linear Time Code (LTC) generator compliant with SMPTE standards for broadcast and post-production applications. This tool produces industry-standard LTC audio signals compatible with professional audio/video equipment and software.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## 🌐 Connect with me  

<p align="left">
<a href="https://linkedin.com/in/sithulaka" target="blank"><img align="center" src="https://github.com/sithulaka/sithulaka/blob/main/image/icon/linked-in-alt.svg" alt="sithulaka" height="30" width="40" /></a>
<a href="https://twitter.com/sithulaka" target="blank"><img align="center" src="https://github.com/sithulaka/sithulaka/blob/main/image/icon/twitter.svg" alt="sithulaka" height="30" width="40" /></a>
<a href="https://fb.com/senithu.sithulaka.7" target="blank"><img align="center" src="https://github.com/sithulaka/sithulaka/blob/main/image/icon/facebook.svg" alt="sithulaka" height="30" width="40" /></a>
<a href="https://instagram.com/_sithulaka_" target="blank"><img align="center" src="https://github.com/sithulaka/sithulaka/blob/main/image/icon/instagram.svg" alt="sithulaka" height="30" width="40" /></a>
</p>

