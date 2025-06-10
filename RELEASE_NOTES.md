# Release Notes - LTC Timecode Generator v1.0.0

## 🎉 Initial Release

Welcome to the first release of **LTC Timecode Generator** - a professional SMPTE-compliant Linear Time Code generator with a modern web interface!

## 📥 Download

### Windows Users
- **[LTC_Timecode_Generator.exe](https://github.com/sithulaka/LTC-Timecode-Generator/releases/download/v1.0.0/LTC_Timecode_Generator.exe)** (26.4 MB)
  - Ready-to-run executable (no installation required)
  - Windows 10/11 compatible
  - Self-contained with all dependencies

### All Platforms
- **Source Code** - Available as ZIP or TAR.GZ from this release

## ✨ Features

### Professional LTC Generation
- **SMPTE 12M Compliant** - Industry-standard timecode generation
- **All Standard Frame Rates** - 23.976, 24, 25, 29.97, 30, 50, 59.94, 60fps
- **Drop Frame Support** - Accurate drop frame compensation for 29.97fps and 59.94fps
- **High-Quality Audio** - 16/24-bit depth at 44.1kHz to 192kHz sample rates
- **Bi-Phase Mark Encoding** - Professional Manchester encoding implementation

### Modern User Interface
- **Web-Based GUI** - Clean, responsive interface using HTML5/CSS3/JavaScript
- **Real-Time Preview** - Live filename generation based on settings
- **Theme Toggle** - Light and dark mode support
- **Progress Tracking** - Real-time generation progress indicator
- **Cross-Platform** - Runs on Windows, macOS, and Linux

### Export Options
- **WAV Format** - Professional uncompressed audio export
- **Flexible Duration** - Generate timecode from seconds to hours
- **Pre-Roll Support** - Optional 10-second pre-roll before main timecode
- **Custom Naming** - Automatic filename generation with manual override

## 🎯 Use Cases

Perfect for:
- **Broadcast Production** - Professional timecode sync
- **Post-Production** - Video editing and audio sync
- **Live Events** - Timecode reference for multi-camera setups
- **Testing & Calibration** - Equipment testing and validation

## 🔧 Technical Specifications

### Supported Frame Rates
| Frame Rate | Type | Drop Frame |
|------------|------|------------|
| 23.976fps | Non-Drop | ❌ |
| 24fps | Non-Drop | ❌ |
| 25fps (PAL) | Non-Drop | ❌ |
| 29.97fps | Non-Drop & Drop | ✅ |
| 30fps | Non-Drop | ❌ |
| 50fps | Non-Drop | ❌ |
| 59.94fps | Non-Drop & Drop | ✅ |
| 60fps | Non-Drop | ❌ |

### Audio Specifications
- **Sample Rates**: 44.1kHz, 48kHz, 96kHz, 192kHz
- **Bit Depths**: 16-bit, 24-bit
- **Format**: Mono WAV files
- **Encoding**: Professional bi-phase mark (Manchester)

## 🧪 Software Compatibility

Generated LTC files work with:
- Avid Pro Tools
- Adobe Premiere Pro/After Effects
- DaVinci Resolve
- Final Cut Pro
- Logic Pro
- Reaper
- Professional hardware sync generators

## 🚀 Quick Start

### Windows (Executable)
1. Download `LTC_Timecode_Generator.exe`
2. Double-click to run (no installation needed)
3. Configure your timecode settings
4. Click "Generate LTC" to create your file

### From Source
1. Clone the repository
2. Install Python 3.7+ and dependencies: `pip install -r requirements.txt`
3. Run: `python app.py`

## 📋 System Requirements

### Windows Executable
- Windows 10 or later (64-bit)
- ~30MB free disk space
- Internet browser (Chrome, Firefox, Edge, etc.)

### From Source
- Python 3.7 or later
- NumPy 1.20.0+
- Eel 0.14.0+
- Modern web browser

## 🐛 Known Issues

- None currently reported

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- SMPTE for the timecode standards
- The broadcast and post-production community for feedback and requirements
- Open source contributors who made this project possible

---

**Full Changelog**: Initial release

For questions, issues, or feature requests, please visit our [GitHub Issues](https://github.com/sithulaka/LTC-Timecode-Generator/issues) page.
