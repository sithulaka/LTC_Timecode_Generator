# Contributing to LTC Timecode Generator

First off, thank you for considering contributing to LTC Timecode Generator! It's people like you that make this tool better for everyone in the broadcast and post-production community.

## Ways to Contribute

### 🐛 Reporting Bugs
- Use the GitHub Issues page to report bugs
- Include your OS, Python version, and browser information
- Provide steps to reproduce the issue
- Include any error messages or screenshots

### 💡 Suggesting Features
- Open an issue with the "enhancement" label
- Describe the feature and why it would be useful
- Consider if it fits with the project's scope and goals

### 🔧 Code Contributions
- Fork the repository
- Create a feature branch from `main`
- Make your changes following the coding standards below
- Test your changes thoroughly
- Submit a pull request with a clear description

## Development Setup

1. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/LTC-Timecode-Generator.git
   cd LTC-Timecode-Generator
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

## Coding Standards

### Python Code
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Include docstrings for all functions and classes
- Add type hints where appropriate
- Keep functions focused and small

### Web Interface
- Use semantic HTML5 elements
- Follow modern CSS practices
- Ensure responsive design
- Test across different browsers
- Maintain accessibility standards

### Documentation
- Update README.md for user-visible changes
- Update CHANGELOG.md following Keep a Changelog format
- Include inline comments for complex logic
- Update docstrings when changing function behavior

## Testing

### Before Submitting
- Test the application on your target platform
- Verify LTC files play correctly in professional software
- Check that the web interface works in multiple browsers
- Ensure all frame rates and sample rates work correctly

### Test Cases to Verify
- Generate LTC at different frame rates
- Test drop frame vs non-drop frame
- Verify different sample rates and bit depths
- Test pre-roll functionality
- Validate generated files in DAW software

## Pull Request Process

1. **Branch Naming**: Use descriptive names like `feature/add-new-framerate` or `fix/audio-export-bug`

2. **Commit Messages**: Write clear, concise commit messages:
   ```
   Add support for 48fps frame rate
   
   - Implement 48fps in FrameRate enum
   - Update UI dropdown options
   - Add validation for 48fps timecode
   ```

3. **Pull Request Description**: Include:
   - What changes were made
   - Why the changes were necessary
   - How to test the changes
   - Any potential breaking changes

4. **Code Review**: Be responsive to feedback and make requested changes promptly

## Building and Testing the Executable

If your changes affect the executable build:

1. **Test the PyInstaller build**:
   ```bash
   pyinstaller ltc_generator.spec
   ```

2. **Test the executable**:
   - Run the .exe file
   - Verify all features work
   - Test on a clean system if possible

## Community Guidelines

- Be respectful and constructive in all interactions
- Help others learn and grow
- Focus on the technical merits of contributions
- Welcome newcomers and help them get started

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the "question" label
- Reach out to the maintainers
- Check existing issues and pull requests for similar questions

Thank you for contributing to LTC Timecode Generator! 🎬🎵
