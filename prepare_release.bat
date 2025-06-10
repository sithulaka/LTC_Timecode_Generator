@echo off
REM Release preparation script for LTC Timecode Generator (Windows)

echo 🚀 Preparing LTC Timecode Generator for release...

REM Clean build artifacts
echo 🧹 Cleaning build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
for /r %%i in (*.pyc) do del "%%i"
for /r %%i in (*.pyo) do del "%%i"
for /r %%i in (*.pyd) do del "%%i"

REM Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Build executable
echo 🔨 Building Windows executable...
pyinstaller app.spec

REM Check if build was successful
if exist "dist\LTC_Timecode_Generator.exe" (
    echo ✅ Build successful! Executable created at dist\LTC_Timecode_Generator.exe
    
    REM Get file size
    for %%A in (dist\LTC_Timecode_Generator.exe) do echo 📏 Executable size: %%~zA bytes
) else (
    echo ❌ Build failed! Executable not found.
    pause
    exit /b 1
)

echo.
echo 🎉 Release preparation complete!
echo.
echo Next steps:
echo 1. Test the executable in dist\LTC_Timecode_Generator.exe
echo 2. Commit all changes to git
echo 3. Create and push a git tag: git tag v1.0.0 ^&^& git push origin v1.0.0
echo 4. Create a GitHub release and upload the executable
echo.
echo Files to include in release:
echo - dist\LTC_Timecode_Generator.exe (Windows executable)
echo - Source code archive (GitHub will create this automatically)
echo.
pause
