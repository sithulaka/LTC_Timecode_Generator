# Parallel Development Prompt — LTC Timecode Generator Improvements

> Paste this entire block as a single message to Claude Code.
> It dispatches 5 parallel agents grouped by file scope so they don't conflict.

---

Implement all 40 improvements from IMPROVEMENTS.md for the LTC Timecode Generator app.
Dispatch 5 parallel agents grouped by file scope. Each agent works independently on separate files.
Read IMPROVEMENTS.md first for full context.

=== AGENT 1: ltc_generator.py — Core Engine (Items 1.1, 1.3, 2.2, 2.3, 2.4, 3.3-partial, 3.5, 9.1) ===

Edit /home/ceylond/Desktop/work/LTC_Timecode_Generator/ltc_generator.py only. Do NOT touch app.py or web/ files.

1. **[1.1] Vectorize 24-bit WAV export** — Replace the slow Python loop in `export_wav()` (lines 354-356):
   ```python
   audio_24bit = bytearray()
   for sample in audio_int:
       audio_24bit.extend(struct.pack('<i', sample)[:3])
   ```
   With vectorized numpy:
   ```python
   raw = audio_int.astype('<i4').tobytes()
   raw_bytes = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 4)[:, :3]
   wav_file.writeframes(raw_bytes.tobytes())
   ```

2. **[1.3] Add BCD lookup table** — Create a module-level `_BCD_TABLE` list of 10 entries (digits 0-9) as 4-bit lists. Use it in `_generate_ltc_word()` instead of per-frame bit shifting.

3. **[2.2] Add user_bits support** — Add `user_bits: int = 0` field to `LTCConfig` (default 0, 32-bit unsigned). In `_generate_ltc_word()`, extract 4-bit groups and write to UB1-UB8 positions. Validate in `__post_init__` that `0 <= user_bits <= 0xFFFFFFFF`. Recalculate parity AFTER setting user bits.

4. **[2.3] Add 32-bit float export** — Allow `bit_depth=32` in `LTCConfig` validation. In `export_wav()`, add a 32-bit float path: write float32 samples directly using `sample_width=4`. Python's `wave` module doesn't natively support float32, so write raw bytes and manually set the format tag to 3 (IEEE float) by writing the WAV header manually, OR keep it simple: just use `struct.pack` to write PCM 32-bit int. Simplest approach: support bit_depth 32 as 32-bit integer PCM (`np.int32` with max_val=2147483647).

5. **[2.4] Add channels option** — Add `channels: int = 1` field to `LTCConfig` (1=mono, 2=stereo). Validate 1 or 2. In `export_wav()`, set `setnchannels(channels)`. If stereo, duplicate the mono audio: `audio_data = np.column_stack([audio_data, audio_data]).ravel()` before writing.

6. **[3.3 partial] Add logging to ltc_generator** — Add `import logging` at top, create `logger = logging.getLogger(__name__)`. Add `logger.info()` for generation start/end with config summary in `generate_ltc()`. Add `logger.info()` for WAV export with file path/size in `export_wav()`. Add `logger.debug()` for drop frame adjustments.

7. **[3.5] Extract magic numbers** — Add module-level constants:
   ```python
   LTC_BITS_PER_FRAME = 80
   LTC_SYNC_WORD = 0xBFFC
   MAX_INT16 = 32767
   MAX_INT24 = 8388607
   MAX_INT32 = 2147483647
   ```
   Replace all raw numbers with these constants.

8. **[9.1] Add streaming export** — Add `export_wav_streaming(self, filename, progress_callback=None)` method that generates and writes one frame at a time without holding all audio in memory. Call `progress_callback(percent)` every 100 frames if provided. Keep existing `export_wav()` unchanged for backward compatibility.

After all changes, verify: `python3 -c "from ltc_generator import *; c = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000, bit_depth=16, start_time=(1,0,0,0), duration_seconds=1.0); g = LTCGenerator(c); g.export_wav('/tmp/test_agent1.wav'); print('OK')"`

Also verify 32-bit: `python3 -c "from ltc_generator import *; c = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000, bit_depth=32, start_time=(1,0,0,0), duration_seconds=1.0); g = LTCGenerator(c); g.export_wav('/tmp/test32.wav'); print('32-bit OK')"`

Also verify stereo: `python3 -c "from ltc_generator import *; c = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000, bit_depth=16, start_time=(1,0,0,0), duration_seconds=1.0, channels=2); g = LTCGenerator(c); g.export_wav('/tmp/test_stereo.wav'); import wave; w=wave.open('/tmp/test_stereo.wav','rb'); assert w.getnchannels()==2; print('Stereo OK')"`

Also verify user bits: `python3 -c "from ltc_generator import *; c = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000, bit_depth=16, start_time=(1,0,0,0), duration_seconds=1.0, user_bits=0xDEADBEEF); g = LTCGenerator(c); word = g._generate_ltc_word([1,0,0,0]); ub = 0; ub |= sum(word[4+i]<<i for i in range(4)); ub |= sum(word[12+i]<<i for i in range(4))<<4; ub |= sum(word[20+i]<<i for i in range(4))<<8; ub |= sum(word[28+i]<<i for i in range(4))<<12; ub |= sum(word[36+i]<<i for i in range(4))<<16; ub |= sum(word[44+i]<<i for i in range(4))<<20; ub |= sum(word[52+i]<<i for i in range(4))<<24; ub |= sum(word[60+i]<<i for i in range(4))<<28; print(f'User bits: 0x{ub:08X}'); assert ub == 0xDEADBEEF; print('User bits OK')"`


=== AGENT 2: app.py + cli.py — Backend & CLI (Items 2.1, 2.7, 3.1, 3.2, 3.3-partial, 3.4, 4.1, 4.2) ===

Edit /home/ceylond/Desktop/work/LTC_Timecode_Generator/app.py and create a NEW file /home/ceylond/Desktop/work/LTC_Timecode_Generator/cli.py. Do NOT touch ltc_generator.py or web/ files.

1. **[3.4] Remove unused imports** — Delete `import json` and `from pathlib import Path` from app.py.

2. **[3.1] Add type hints** — Add full PEP 484 type annotations to every function in app.py. Example:
   ```python
   @eel.expose
   def generate_ltc(frame_rate_name: str, sample_rate: int, bit_depth: int,
                    hours: int, minutes: int, seconds: int, frames: int,
                    duration: float, output_path: str) -> dict:
   ```

3. **[3.2] Narrow exception handler** — In generate_ltc(), change the outer `except Exception as e:` to `except (ValueError, IOError, OSError) as e:`.

4. **[3.3 partial] Add logging to app.py** — Add `import logging` and `logging.basicConfig(level=logging.INFO)`. Log generation requests, success, and errors.

5. **[4.1] Add output path validation** — In generate_ltc(), after computing `os.path.abspath(output_path)`, verify the resolved path is under the user's home directory. Reject paths outside with a ValueError.
   ```python
   resolved = os.path.abspath(output_path)
   home = os.path.expanduser("~")
   if not resolved.startswith(home):
       raise ValueError("Output path must be within user home directory")
   ```

6. **[4.2] Add rate limiting** — Add a module-level `_generation_lock = threading.Lock()` and `_last_generation_time = 0`. In generate_ltc(), acquire the lock with a timeout. If another generation is running, return an error immediately.
   ```python
   import threading
   _generation_lock = threading.Lock()
   ```

7. **[2.7] Add file browse dialog** — Add a new `@eel.expose` function `browse_save_path()` that uses tkinter's file dialog:
   ```python
   @eel.expose
   def browse_save_path() -> str:
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
   ```

8. **[2.1] Create CLI interface** — Create a NEW file `cli.py` with argparse:
   ```
   python cli.py --start 01:00:00:00 --duration 60 --frame-rate FR_29_97_DF --sample-rate 48000 --bit-depth 24 --output ltc_output.wav
   ```
   Arguments: --start (HH:MM:SS:FF), --duration (seconds), --frame-rate (enum name), --sample-rate, --bit-depth, --output (file path), --channels (1 or 2, default 1), --user-bits (hex string, default 0). Parse, build LTCConfig, call export_wav(), print summary. Include `if __name__ == "__main__":` block.

Verify app.py: `python3 -c "import ast; ast.parse(open('app.py').read()); print('app.py syntax OK')"`
Verify cli.py: `python3 cli.py --start 01:00:00:00 --duration 5 --frame-rate FR_30_NDF --sample-rate 48000 --bit-depth 16 --output /tmp/cli_test.wav && echo "CLI OK"`


=== AGENT 3: web/ — Frontend UI + Accessibility (Items 2.6, 7.1-7.5, 8.1-8.6) ===

Edit web/script.js, web/index.html, and web/styles.css. Do NOT touch Python files.

**In web/index.html:**

1. **[7.1] Add ARIA labels to time inputs** — Add `aria-label` to each time input:
   ```html
   <input type="number" id="hours" class="time-input" min="0" max="23" value="01" aria-label="Hours">
   <input type="number" id="minutes" class="time-input" min="0" max="59" value="00" aria-label="Minutes">
   <input type="number" id="seconds" class="time-input" min="0" max="59" value="00" aria-label="Seconds">
   <input type="number" id="frames" class="time-input" min="0" max="29" value="00" aria-label="Frames">
   ```

2. **[7.2] Make progress bar semantic** — Replace the progress div with a real `<progress>` element:
   ```html
   <div class="progress-container" id="progressContainer" style="display: none;">
       <progress id="progressFill" class="progress-bar" max="100" value="0" aria-label="Generation progress"></progress>
       <p class="progress-text" id="progressText" aria-live="polite">Generating LTC file...</p>
   </div>
   ```
   Update styles.css to style the `<progress>` element appropriately (keep same appearance).

3. **[7.3] Make toast accessible** — Add `role="alert"` and `aria-live="assertive"` to the toast:
   ```html
   <div class="toast" id="toast" role="alert" aria-live="assertive"></div>
   ```

4. **[7.4] Hide decorative icons from screen readers** — Add `aria-hidden="true"` to ALL `<i class="fas ...">` elements.

5. **[7.5] Add skip-to-content link** — Add at top of body:
   ```html
   <a href="#ltcForm" class="skip-link">Skip to form</a>
   ```
   Add CSS for `.skip-link` (visually hidden until focused).

6. **[2.6] Add duration preset buttons** — After the duration input, add preset buttons:
   ```html
   <div class="duration-presets">
       <button type="button" class="preset-btn" data-duration="0.5">30s</button>
       <button type="button" class="preset-btn" data-duration="1">1m</button>
       <button type="button" class="preset-btn" data-duration="5">5m</button>
       <button type="button" class="preset-btn" data-duration="10">10m</button>
       <button type="button" class="preset-btn" data-duration="30">30m</button>
       <button type="button" class="preset-btn" data-duration="60">1h</button>
   </div>
   ```
   Style them as small pill buttons in styles.css.

7. **[8.6] Add file size estimate** — After the filename preview div, add:
   ```html
   <div class="size-estimate" id="sizeEstimate"></div>
   ```

8. **[8.2] Add help tooltips** — Add `title` attributes to the form labels:
   - Frame Rate: "Timecode frame rate. Drop Frame (DF) compensates for NTSC's 29.97/59.94 rates. Use NDF for film/PAL."
   - Bit Depth: "Audio bit depth. 16-bit is standard, 24-bit for professional use."
   - Sample Rate: "Audio sample rate. 48 kHz is broadcast standard."
   - Pre-roll: "Adds 10 seconds of timecode before your start time, used for broadcast countdown."
   - Duration: "Length of the LTC audio file in minutes."

**In web/script.js:**

9. **[8.1] Add confirmation for long generations** — In generateLTC(), after validation, check duration:
   ```javascript
   if (duration > 600) { // > 10 minutes
       const size = Math.round(duration * sampleRate * (bitDepth / 8) / 1048576);
       if (!confirm(`This will generate ~${size} MB of audio (${Math.round(duration/60)} min). Continue?`)) return;
   }
   ```

10. **[8.3] Preroll preserves frame offset** — Change the preroll block to keep the original frame count:
    ```javascript
    startFrames = frames; // Preserve original frame offset
    ```
    (Change line 215 from `startFrames = 0` back to `startFrames = frames`)

11. **[8.4] Increase toast timeout** — Change 5000 to 8000ms in showToast(). Add a dismiss-on-click:
    ```javascript
    toast.addEventListener('click', () => toast.classList.remove('show'), { once: true });
    ```

12. **[8.6] Add file size estimate function** — Add `updateSizeEstimate()` that calculates and displays:
    ```javascript
    updateSizeEstimate() {
        const duration = parseFloat(document.getElementById('duration').value) * 60;
        const sampleRate = parseInt(document.getElementById('sampleRate').value);
        const bitDepth = parseInt(document.getElementById('bitDepth').value);
        const bytes = duration * sampleRate * (bitDepth / 8);
        const el = document.getElementById('sizeEstimate');
        if (bytes > 1048576) el.textContent = `Estimated file size: ${(bytes / 1048576).toFixed(1)} MB`;
        else el.textContent = `Estimated file size: ${(bytes / 1024).toFixed(0)} KB`;
    }
    ```
    Call it from `updateFilenamePreview()` and on init.

13. **[2.6] Wire up duration preset buttons** — In `setupEventListeners()`:
    ```javascript
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('duration').value = btn.dataset.duration;
            this.updateFilenamePreview();
        });
    });
    ```

14. **[8.5] Add dark mode** — Add a toggle button in the header. Add CSS class `.dark-mode` on body that inverts the color scheme. Store preference in localStorage.

15. Update `animateProgress()` to work with `<progress>` element — set `progressFill.value = 50` instead of `style.width`.

**In web/styles.css:**
- Style `.skip-link` (sr-only until focused)
- Style `.preset-btn` as small pill buttons
- Style `.size-estimate` as muted text below filename preview
- Style `<progress>` element to match existing progress bar appearance
- Style `.dark-mode` theme (dark backgrounds, light text, adjusted gradients)
- Style `.dark-toggle` button in header


=== AGENT 4: tests/ — Testing Improvements (Items 5.3, 5.4, 5.5) ===

Edit files in /home/ceylond/Desktop/work/LTC_Timecode_Generator/tests/ only. Do NOT touch source files.

1. **[5.4] Create conftest.py for libltc auto-build** — Create `tests/conftest.py` that:
   - Checks if `/tmp/libltc/libltc.so` exists
   - If not, clones libltc from GitHub and builds it with gcc
   - If gcc or git not available, marks tests as skipped
   - Provides a `libltc_path` fixture

2. **[5.3] Add edge case tests** — Add to `tests/test_ltc_generator.py`:

   ```python
   class TestEdgeCases:
       def test_start_at_drop_frame_boundary(self):
           """Start at 00:01:00:02 for 29.97 DF — first valid frame after skip"""
           config = LTCConfig(frame_rate=FrameRate.FR_29_97_DF, sample_rate=48000,
                             bit_depth=16, start_time=(0,1,0,2), duration_seconds=1.0)
           gen = LTCGenerator(config)
           audio, sr = gen.generate_ltc()
           assert len(audio) == 48000

       def test_max_timecode_start(self):
           """Start at 23:59:59:29 — should wrap to 00:00:00:00"""
           config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                             bit_depth=16, start_time=(23,59,59,29), duration_seconds=1.0)
           gen = LTCGenerator(config)
           audio, sr = gen.generate_ltc()
           assert len(audio) == 48000

       def test_very_short_duration(self):
           """Duration shorter than one frame"""
           config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                             bit_depth=16, start_time=(0,0,0,0), duration_seconds=0.01)
           gen = LTCGenerator(config)
           audio, sr = gen.generate_ltc()
           assert len(audio) == 480  # 0.01 * 48000

       def test_44100_with_23976(self):
           """Sample rate that doesn't divide evenly by frame rate"""
           config = LTCConfig(frame_rate=FrameRate.FR_23_976_NDF, sample_rate=44100,
                             bit_depth=16, start_time=(0,0,0,0), duration_seconds=2.0)
           gen = LTCGenerator(config)
           audio, sr = gen.generate_ltc()
           assert len(audio) == 88200

       def test_user_bits_preserved(self):
           """User bits 0xDEADBEEF should be encoded in UB1-UB8"""
           config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                             bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0,
                             user_bits=0xDEADBEEF)
           gen = LTCGenerator(config)
           word = gen._generate_ltc_word([0, 0, 0, 0])
           # Extract UB1-UB8 from their bit positions
           ub_positions = [4, 12, 20, 28, 36, 44, 52, 60]
           ub_val = 0
           for idx, pos in enumerate(ub_positions):
               nibble = sum(word[pos + i] << i for i in range(4))
               ub_val |= nibble << (idx * 4)
           assert ub_val == 0xDEADBEEF

       def test_32bit_export(self):
           """32-bit WAV export"""
           config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                             bit_depth=32, start_time=(0,0,0,0), duration_seconds=1.0)
           gen = LTCGenerator(config)
           with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
               path = f.name
           try:
               gen.export_wav(path)
               with wave.open(path, 'rb') as wf:
                   assert wf.getsampwidth() == 4
                   assert wf.getnframes() == 48000
           finally:
               os.unlink(path)

       def test_stereo_export(self):
           """Stereo WAV export has 2 channels"""
           config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                             bit_depth=16, start_time=(0,0,0,0), duration_seconds=1.0,
                             channels=2)
           gen = LTCGenerator(config)
           with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
               path = f.name
           try:
               gen.export_wav(path)
               with wave.open(path, 'rb') as wf:
                   assert wf.getnchannels() == 2
                   assert wf.getnframes() == 48000
           finally:
               os.unlink(path)

       def test_streaming_export_matches_regular(self):
           """Streaming export produces same audio as regular export"""
           config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                             bit_depth=16, start_time=(1,0,0,0), duration_seconds=2.0)
           gen = LTCGenerator(config)
           with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f1, \
                tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f2:
               p1, p2 = f1.name, f2.name
           try:
               gen.export_wav(p1)
               gen.export_wav_streaming(p2)
               with wave.open(p1, 'rb') as w1, wave.open(p2, 'rb') as w2:
                   assert w1.getnframes() == w2.getnframes()
                   d1 = w1.readframes(w1.getnframes())
                   d2 = w2.readframes(w2.getnframes())
                   assert d1 == d2
           finally:
               os.unlink(p1)
               os.unlink(p2)
   ```

3. **[5.5] Add performance benchmark** — Add `tests/test_benchmarks.py`:
   ```python
   import time
   class TestPerformance:
       def test_1min_generation_under_2s(self):
           config = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                             bit_depth=16, start_time=(0,0,0,0), duration_seconds=60.0)
           gen = LTCGenerator(config)
           start = time.time()
           gen.generate_ltc()
           elapsed = time.time() - start
           assert elapsed < 2.0, f"1-min generation took {elapsed:.2f}s (limit: 2s)"

       def test_24bit_vectorized_fast(self):
           """24-bit export should not be dramatically slower than 16-bit"""
           config16 = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                               bit_depth=16, start_time=(0,0,0,0), duration_seconds=60.0)
           config24 = LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                               bit_depth=24, start_time=(0,0,0,0), duration_seconds=60.0)
           gen16 = LTCGenerator(config16)
           gen24 = LTCGenerator(config24)
           t16_start = time.time()
           gen16.export_wav('/tmp/bench16.wav')
           t16 = time.time() - t16_start
           t24_start = time.time()
           gen24.export_wav('/tmp/bench24.wav')
           t24 = time.time() - t24_start
           ratio = t24 / max(t16, 0.001)
           assert ratio < 2.0, f"24-bit is {ratio:.1f}x slower than 16-bit (limit: 2x)"
   ```

4. **Update existing tests** — In test_ltc_generator.py `TestLTCConfig.test_invalid_bit_depth`: change expected behavior since 32 is now valid. Test with 8 instead:
   ```python
   def test_invalid_bit_depth(self):
       with pytest.raises(ValueError):
           LTCConfig(frame_rate=FrameRate.FR_30_NDF, sample_rate=48000,
                    bit_depth=8, start_time=(0,0,0,0), duration_seconds=1.0)
   ```

After creating, run: `python3 -m pytest tests/test_ltc_generator.py tests/test_benchmarks.py -v`


=== AGENT 5: Packaging & CI (Items 5.1, 6.1-6.5) ===

Create/edit packaging and CI files only. Do NOT touch source code files.

1. **[6.1] Create pyproject.toml** at project root:
   ```toml
   [build-system]
   requires = ["setuptools>=68.0", "wheel"]
   build-backend = "setuptools.backends._legacy:_Backend"

   [project]
   name = "ltc-timecode-generator"
   version = "1.1.0"
   description = "Professional SMPTE LTC Linear Timecode Generator"
   readme = "README.md"
   license = {text = "MIT"}
   requires-python = ">=3.9"
   dependencies = [
       "numpy>=1.20.0,<3.0.0",
       "eel>=0.14.0,<1.0.0",
   ]

   [project.optional-dependencies]
   dev = ["pytest>=7.0", "pytest-cov", "mypy", "ruff"]

   [project.scripts]
   ltc-generator = "cli:main"
   ltc-gui = "app:main"

   [tool.pytest.ini_options]
   testpaths = ["tests"]

   [tool.ruff]
   line-length = 120

   [tool.mypy]
   python_version = "3.9"
   warn_return_any = true
   ```

2. **[6.2] Pin requirements** — Update `requirements.txt`:
   ```
   numpy>=1.20.0,<3.0.0
   eel>=0.14.0,<1.0.0
   ```
   Create `requirements-dev.txt`:
   ```
   -r requirements.txt
   pytest>=7.0
   pytest-cov
   mypy
   ruff
   ```

3. **[5.1] Fix CI to run tests** — Update `.github/workflows/build.yml` `build-source` job:
   ```yaml
   - name: Test application
     run: |
       python -m pip install --upgrade pip
       pip install -r requirements.txt
       pip install pytest
       python -m pytest tests/test_ltc_generator.py -v
   ```

4. **[6.3] Add macOS build job** — Add to build.yml:
   ```yaml
   build-macos:
     runs-on: macos-latest
     steps:
     - uses: actions/checkout@v4
     - name: Set up Python
       uses: actions/setup-python@v4
       with:
         python-version: '3.11'
     - name: Install dependencies
       run: |
         python -m pip install --upgrade pip
         pip install -r requirements.txt
         pip install pyinstaller
     - name: Build executable
       run: pyinstaller --onefile --name LTC_Timecode_Generator --add-data "web:web" app.py
     - name: Upload artifact
       uses: actions/upload-artifact@v4
       with:
         name: LTC_Timecode_Generator_macOS
         path: dist/LTC_Timecode_Generator
   ```

5. **[6.4] Create Dockerfile** at project root:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir numpy
   COPY ltc_generator.py cli.py ./
   ENTRYPOINT ["python", "cli.py"]
   ```

6. **[6.5] Create app.spec** if missing — Create a basic PyInstaller spec file:
   ```python
   # app.spec
   a = Analysis(['app.py'],
                pathex=[],
                binaries=[],
                datas=[('web', 'web')],
                hiddenimports=['bottle_websocket'],
                hookspath=[],
                hooksconfig={},
                runtime_hooks=[],
                excludes=[],
                noarchive=False)
   pyz = PYZ(a.pure)
   exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
             name='LTC_Timecode_Generator',
             debug=False,
             bootloader_ignore_signals=False,
             strip=False,
             upx=True,
             console=False)
   ```

Verify: `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('pyproject.toml valid')" 2>/dev/null || python3 -c "import tomli; tomli.load(open('pyproject.toml','rb')); print('pyproject.toml valid')" 2>/dev/null || echo "Install tomli to validate"`
