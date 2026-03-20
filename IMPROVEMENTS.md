# LTC Timecode Generator - Improvements Roadmap

> **Date:** 2026-03-20
> **Baseline:** Post-bugfix state (all 20 issues from ISSUES.md resolved)

---

## Priority Legend

| Tag | Meaning |
|-----|---------|
| **P0** | Should fix before any release |
| **P1** | Next release |
| **P2** | Nice to have |

---

## 1. Performance

### 1.1 [P0] 24-bit WAV Export is ~5x Slower Than 16-bit

**File:** `ltc_generator.py:354-356`

The 24-bit path iterates every sample in pure Python to strip the 4th byte:

```python
audio_24bit = bytearray()
for sample in audio_int:
    audio_24bit.extend(struct.pack('<i', sample)[:3])
```

For a 2-hour file at 192 kHz this loop runs ~1.38 billion iterations. Replace with a vectorized numpy approach:

```python
raw = audio_int.astype('<i4').tobytes()
idx = np.arange(len(audio_int)) * 4
idx = np.stack([idx, idx+1, idx+2], axis=1).ravel()
audio_24bit = np.frombuffer(raw, dtype=np.uint8)[idx].tobytes()
```

---

### 1.2 [P1] No Real-Time Progress Feedback

**File:** `ltc_generator.py:97-126`

`generate_ltc()` runs to completion with no callback. The frontend progress bar sits at 50% until the backend returns. For long durations this looks frozen.

**Options:**
- Add an optional `progress_callback(percent)` parameter to `generate_ltc()`
- Expose a polling endpoint (`get_generation_progress`) and call it from JS on a timer
- Use Eel's `eel.spawn()` with periodic `eel.update_progress(pct)()` calls

---

### 1.3 [P2] LTC Word Generation Could Use Lookup Table

**File:** `ltc_generator.py:128-243`

Each frame rebuilds the 80-bit word from scratch. For long files at high frame rates this is millions of calls. A precomputed BCD lookup table for digits 0-9 would reduce per-frame work.

---

## 2. Missing Features

### 2.1 [P0] No CLI Interface

The app is GUI-only. Professional workflows need scriptable batch generation.

**Proposed usage:**
```
python -m ltc_generator \
  --start 01:00:00:00 \
  --duration 60 \
  --frame-rate FR_29_97_DF \
  --sample-rate 48000 \
  --bit-depth 24 \
  --output ltc_output.wav
```

Add an `argparse` block to `ltc_generator.py:main()` alongside the existing example code.

---

### 2.2 [P1] No User Bits (UB1-UB8) Support

**File:** `ltc_generator.py:170-221`

All 32 user bits are hardcoded to zero. SMPTE 12M allocates 8 groups of 4 user bits for metadata (reel number, date per SMPTE 309M, custom data).

**Recommendation:** Add a `user_bits: int = 0` field to `LTCConfig` (32-bit value) and distribute it across UB1-UB8 in `_generate_ltc_word()`.

---

### 2.3 [P1] No 32-bit Float Audio Export

**File:** `ltc_generator.py:54, 64`

Only 16-bit and 24-bit integer supported. Some DAWs prefer 32-bit float WAV. The audio is already generated as float32 internally — just needs a write path.

---

### 2.4 [P1] No Stereo or Dual-Mono Export

**File:** `ltc_generator.py:346`

Always mono. Some workflows embed LTC on channel 2 of a stereo pair, or need identical LTC on both channels.

---

### 2.5 [P2] No Batch Processing

No way to generate multiple files with different start times in one operation. A CSV/JSON input mode would serve post-production workflows.

---

### 2.6 [P2] Duration Preset Buttons

Common durations (30 s, 1 m, 5 m, 10 m, 30 m, 1 h) require manual typing. Quick-select buttons above the duration field would save time.

---

### 2.7 [P2] No File Browse Dialog

**File:** `app.py` (stubs were removed in bugfix)

Users can't pick an output folder visually. Eel doesn't support native file dialogs natively, but `tkinter.filedialog` can be called from the backend:

```python
from tkinter import filedialog, Tk
root = Tk(); root.withdraw()
path = filedialog.asksaveasfilename(defaultextension=".wav")
```

---

## 3. Code Quality

### 3.1 [P0] No Type Hints on Backend Functions

**File:** `app.py:24-25`

```python
def generate_ltc(frame_rate_name, sample_rate, bit_depth,
                 hours, minutes, seconds, frames, duration, output_path):
```

Nine untyped parameters. Add full PEP 484 annotations for IDE support and static analysis.

---

### 3.2 [P0] Overly Broad Exception Handler

**File:** `app.py:82`

```python
except Exception as e:
    return {"success": False, "message": f"Error generating LTC: {str(e)}"}
```

Catches everything — including `KeyboardInterrupt`, `SystemExit`, and programming bugs. Narrow to `(ValueError, IOError, OSError)`.

---

### 3.3 [P1] No Logging

**Files:** `ltc_generator.py`, `app.py`

Zero logging. Use `logging` module for:
- Generation start/end with config summary
- WAV write start/end with file size
- Errors with stack traces
- Drop frame adjustments for debugging

---

### 3.4 [P1] Unused Imports

**File:** `app.py:4-5`

```python
import json      # never used
from pathlib import Path  # never used
```

---

### 3.5 [P2] Magic Numbers

**File:** `ltc_generator.py`

`80` (bits per frame), `7200` (max duration), `32767`/`8388607` (max sample values) appear as raw numbers. Extract to named constants:

```python
LTC_BITS_PER_FRAME = 80
MAX_DURATION_SECONDS = 7200
```

---

## 4. Security

### 4.1 [P0] No Output Path Validation

**File:** `app.py:65`

```python
os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
```

Accepts arbitrary paths from the frontend without traversal checks. A crafted path could write outside the user's home directory.

**Fix:** Resolve the path and verify it's under an allowed base directory (e.g., user's home or Desktop).

---

### 4.2 [P2] No Rate Limiting on Generate Endpoint

Rapid-fire calls to `generate_ltc()` could exhaust CPU and disk. Add a simple lock or cooldown to prevent concurrent generation.

---

## 5. Testing

### 5.1 [P0] CI Doesn't Run Tests

**File:** `.github/workflows/build.yml:61-65`

The `build-source` job only does an import check:

```yaml
python -c "import ltc_generator; print('LTC Generator imported successfully')"
```

Should run `python -m pytest tests/ -v` instead. Also missing `pytest` in CI dependencies.

---

### 5.2 [P1] No Frontend Tests

No JavaScript tests for:
- `validateInputs()` boundary values
- `updateMaxFrames()` frame rate switching
- `updateFilenamePreview()` format output
- Preroll time calculation and midnight wrap
- `getOutputPath()` regex fallback

Add Jest or Vitest test suite under `web/tests/`.

---

### 5.3 [P1] Missing Edge Case Tests

Current test suite doesn't cover:
- Starting at a drop frame skip boundary (e.g., `00:01:00:00` for 29.97 DF)
- Maximum valid timecode `23:59:59:xx` as start time
- Very short durations (< 1 frame)
- Sample rates that don't divide evenly by frame rate (44100 / 23.976)
- Concurrent export to same file path

---

### 5.4 [P1] Real Decode Tests Require Manual Setup

**File:** `tests/test_real_decode.py`

Tests depend on `/tmp/libltc/libltc.so` which must be built manually. Add a `conftest.py` fixture that builds libltc automatically, or skip with a clear message.

---

### 5.5 [P2] No Performance Benchmarks

No tests that verify generation time stays within acceptable bounds. A 1-minute 48 kHz 16-bit file should generate in under 2 seconds.

---

## 6. Deployment & Packaging

### 6.1 [P0] No `pyproject.toml`

The project isn't installable via pip. Add:

```toml
[project]
name = "ltc-timecode-generator"
version = "1.1.0"
requires-python = ">=3.9"
dependencies = ["numpy>=1.20.0", "eel>=0.14.0"]

[project.optional-dependencies]
dev = ["pytest", "pytest-cov", "mypy", "ruff"]

[project.scripts]
ltc-generator = "app:main"
```

---

### 6.2 [P1] Requirements Not Pinned

**File:** `requirements.txt`

```
numpy>=1.20.0
eel>=0.14.0
```

No upper bounds or lock file. A breaking numpy 3.x release could break installs. Pin tested versions or add a `requirements-lock.txt`.

---

### 6.3 [P1] Windows-Only Build in CI

**File:** `.github/workflows/build.yml`

Only builds a Windows `.exe`. No macOS `.app` or Linux AppImage/deb. The `build-source` job creates a tarball but doesn't test installation from it.

---

### 6.4 [P2] No Docker Support

No Dockerfile for containerized or headless server deployment (useful with CLI mode from 2.1).

---

### 6.5 [P2] `app.spec` Not in Repository

**File:** `.github/workflows/build.yml:29`

```yaml
pyinstaller app.spec
```

The `.spec` file is referenced by CI but not tracked in git (`.gitignore` likely excludes it). CI build would fail on a fresh clone.

---

## 7. Accessibility (HTML/CSS)

### 7.1 [P0] Missing ARIA Labels on Time Inputs

**File:** `web/index.html:37-43`

```html
<label for="startTime">Start Time (hh:mm:ss:ff)</label>
<input type="number" id="hours" ...>
```

The label targets `startTime` but the actual inputs are `hours`, `minutes`, `seconds`, `frames`. Screen readers can't associate the label.

**Fix:** Add `aria-label` to each input:

```html
<input type="number" id="hours" aria-label="Hours" ...>
<input type="number" id="minutes" aria-label="Minutes" ...>
```

---

### 7.2 [P1] Progress Bar Not Semantic

**File:** `web/index.html:121-126`

Uses `<div class="progress-bar">` instead of `<progress>` element. Screen readers can't announce progress state.

**Fix:**
```html
<progress id="progressFill" max="100" value="0"
          aria-label="Generation progress"></progress>
```

---

### 7.3 [P1] Toast Notifications Not Announced

**File:** `web/script.js:286-295`

Toast uses CSS animation only. Screen readers won't announce it.

**Fix:** Add `role="alert"` and `aria-live="assertive"` to the toast element:

```html
<div class="toast" id="toast" role="alert" aria-live="assertive"></div>
```

---

### 7.4 [P1] Icons Have No Accessible Text

**File:** `web/index.html:16, 29, 69, 102, 117`

Font Awesome icons like `<i class="fas fa-clock"></i>` have no alt text. Add `aria-hidden="true"` (decorative) or `aria-label` (meaningful).

---

### 7.5 [P2] No Skip-to-Content Link

No mechanism for keyboard users to skip the header and jump to the form.

---

## 8. UX / UI Polish

### 8.1 [P1] No Confirmation for Long Generations

If user sets 120 minutes at 192 kHz / 24-bit, generation runs immediately. Show a confirmation dialog for durations over 10 minutes with estimated file size.

---

### 8.2 [P1] No Help Tooltips

No tooltips explaining:
- What drop frame means and when to use it
- Why frame rates are fractional (NTSC history)
- What preroll is for (broadcast countdown)
- Bit depth / sample rate impact on file size

Add `title` attributes or info-icon popovers next to each field label.

---

### 8.3 [P1] Preroll Doesn't Preserve Frame Offset

**File:** `web/script.js:208-215`

If user sets start time `00:05:00:15` with preroll, preroll starts at `23:59:50:00` — the `:15` frames are lost. Should start at `23:59:50:15`.

---

### 8.4 [P2] Toast Disappears Too Quickly

**File:** `web/script.js:292-294`

5-second timeout may be too short for file path messages. Increase to 8 seconds, or add a dismiss button.

---

### 8.5 [P2] No Dark Mode

The gradient background is fixed. Professional users in dark editing suites would benefit from a dark theme toggle.

---

### 8.6 [P2] No File Size Estimate

Show estimated WAV file size before generation:

```
Size ≈ duration_sec × sample_rate × (bit_depth / 8) bytes
```

Display below the filename preview.

---

## 9. Architecture

### 9.1 [P1] `export_wav()` Does Generation + I/O in One Call

**File:** `ltc_generator.py:331-357`

`export_wav()` calls `generate_ltc()` internally, holding the entire audio buffer in memory. For a 2-hour 192 kHz file, that's ~5.3 GB of float32 data.

**Recommendation:** Add a streaming export mode that generates and writes frame-by-frame:

```python
def export_wav_streaming(self, filename: str):
    """Export LTC without holding entire audio in memory."""
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        # ... setup ...
        for frame_audio in self._generate_frames():
            wav_file.writeframes(frame_audio)
```

---

### 9.2 [P2] No Separation Between LTC Engine and Eel App

`app.py` imports directly from `ltc_generator.py`. If someone wants to use the LTC engine as a library, they get Eel as a transitive dependency. Split into:

```
ltc_generator.py   # Pure library, no dependencies except numpy
app.py             # Eel GUI wrapper
cli.py             # CLI wrapper (new)
```

---

## Summary

| Category | P0 | P1 | P2 | Total |
|----------|----|----|-----|-------|
| Performance | 1 | 1 | 1 | 3 |
| Features | 1 | 3 | 3 | 7 |
| Code Quality | 2 | 2 | 1 | 5 |
| Security | 1 | 0 | 1 | 2 |
| Testing | 1 | 3 | 1 | 5 |
| Deployment | 1 | 2 | 2 | 5 |
| Accessibility | 1 | 3 | 1 | 5 |
| UX/UI | 0 | 3 | 3 | 6 |
| Architecture | 0 | 1 | 1 | 2 |
| **Total** | **8** | **18** | **14** | **40** |
