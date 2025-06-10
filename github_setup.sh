#!/bin/bash
# GitHub Repository Setup Script for LTC Timecode Generator

echo "🚀 Setting up LTC Timecode Generator for GitHub..."

# Initialize git repository if not already done
if [ ! -d ".git" ]; then
    echo "📝 Initializing Git repository..."
    git init
    git branch -M main
fi

# Add all files to git
echo "📁 Adding files to git..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "Initial release: LTC Timecode Generator v1.0.0

- Professional SMPTE-compliant LTC generation
- Support for all standard frame rates (23.976-60fps)
- Modern web-based user interface
- Cross-platform compatibility
- Windows executable included
- Complete documentation and build scripts"

# Instructions for GitHub setup
echo ""
echo "🎉 Repository ready for GitHub!"
echo ""
echo "Next steps to upload to GitHub:"
echo "1. Create a new repository on GitHub: 'LTC-Timecode-Generator'"
echo "2. Add your GitHub remote:"
echo "   git remote add origin https://github.com/sithulaka/LTC-Timecode-Generator.git"
echo ""
echo "3. Push to GitHub:"
echo "   git push -u origin main"
echo ""
echo "4. Create your first release:"
echo "   git tag v1.0.0"
echo "   git push origin v1.0.0"
echo ""
echo "5. Go to GitHub Releases page and create a new release:"
echo "   - Tag: v1.0.0"
echo "   - Title: LTC Timecode Generator v1.0.0"
echo "   - Upload: dist/LTC_Timecode_Generator.exe"
echo "   - Use RELEASE_NOTES.md content for description"
echo ""
echo "📂 Files ready for upload:"
echo "✅ Source code (automatic from GitHub)"
echo "✅ Windows executable: dist/LTC_Timecode_Generator.exe (26.4 MB)"
echo "✅ Complete documentation"
echo "✅ MIT License"
echo "✅ GitHub Actions workflow for automated builds"
echo ""
