#!/bin/bash
# Release preparation script for LTC Timecode Generator

echo "🚀 Preparing LTC Timecode Generator for release..."

# Clean build artifacts
echo "🧹 Cleaning build artifacts..."
rm -rf build/
rm -rf dist/
rm -rf __pycache__/
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.pyd" -delete
find . -name "*.so" -delete
find . -name ".DS_Store" -delete

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# Build executable
echo "🔨 Building Windows executable..."
pyinstaller app.spec

# Check if build was successful
if [ -f "dist/LTC_Timecode_Generator.exe" ]; then
    echo "✅ Build successful! Executable created at dist/LTC_Timecode_Generator.exe"
    
    # Get file size
    size=$(ls -lh dist/LTC_Timecode_Generator.exe | awk '{print $5}')
    echo "📏 Executable size: $size"
else
    echo "❌ Build failed! Executable not found."
    exit 1
fi

echo ""
echo "🎉 Release preparation complete!"
echo ""
echo "Next steps:"
echo "1. Test the executable in dist/LTC_Timecode_Generator.exe"
echo "2. Commit all changes to git"
echo "3. Create and push a git tag: git tag v1.0.0 && git push origin v1.0.0"
echo "4. Create a GitHub release and upload the executable"
echo ""
echo "Files to include in release:"
echo "- dist/LTC_Timecode_Generator.exe (Windows executable)"
echo "- Source code archive (GitHub will create this automatically)"
echo ""
