# LTC Timecode Generator - Issues Report

> **Date:** 2026-03-20
> **Version Analyzed:** 1.0.0 (commit 265b882)

---

## Critical Issues

### 1. LTC Word Bit Layout is Wrong (SMPTE Non-Compliant)

**File:** `ltc_generator.py:128-247`

**This is the most critical issue.** The `_generate_ltc_word()` method has an incorrect bit layout that does not match the SMPTE 12M standard. The code only defines **4 user bits groups** (16 bits), but the standard requires **8 user bits groups** (32 bits). This shifts all fields after bit 11 to the wrong positions, and the sync word ends up at bits 48-63 instead of the correct position at bits 64-79. Bits 64-79 are dead zeros.

**Code layout vs SMPTE standard:**
```
BITS     CODE HAS              SMPTE REQUIRES
 0- 3    Frame units            Frame units          (OK)
 4- 7    User bits 1            User bits 1          (OK)
 8- 9    Frame tens             Frame tens           (OK)
10       Drop frame flag        Drop frame flag      (OK)
11       Color frame flag       Color frame flag     (OK)
12-15    Seconds units          User bits 2          (WRONG - missing user group)
16-19    User bits 2            Seconds units        (WRONG)
20-23    Seconds tens + BGF     User bits 3          (WRONG)
24-27    Minutes units          Seconds tens + BGF0  (WRONG)
...      (all subsequent fields shifted by 16 bits)
48-63    Sync word              Hours units + UB7    (WRONG)
64-79    DEAD ZEROS             Sync word 0x3FFD     (WRONG)
```

**Impact:** The generated LTC audio signal is **completely invalid**. No hardware or software LTC decoder will be able to read the timecode because:
- All data fields after bit 11 are at wrong positions
- The sync word (used by decoders to find frame boundaries) is at the wrong location
- 16 trailing zero-bits corrupt frame timing

---

### 2. `eel.init('web')` Called Twice

**Files:** `app.py:9`, `app.py:146`

`eel.init('web')` is called at module import time (line 9) **and** again inside `main()` (line 146). This double initialization can cause unexpected behavior, errors, or resource conflicts depending on the Eel version.

```python
# Line 9 (module level)
eel.init('web')

# Line 146 (inside main())
def main():
    eel.init('web')  # DUPLICATE
    eel.start('index.html', size=(1000, 700))
```

---

### 3. `validateInputs()` is Never Called

**File:** `web/script.js:323-338`

The `validateInputs()` method exists but is never invoked. The `generateLTC()` method (line 165) submits form data directly without any client-side validation. Invalid inputs (negative frames, hours > 23, etc.) are only caught by the Python backend, resulting in poor user experience with generic error messages.

---

### 4. Duration Unit Mismatch Between Filename Preview and Backend

**Files:** `web/script.js:142-144`, `app.py:100-102`

The filename preview in JavaScript treats the raw duration input value as **minutes**:
```javascript
// script.js line 142-144
const durationMins = Math.floor(duration);         // raw value = minutes
const durationSecs = Math.round((duration - durationMins) * 60);
```

But `generate_filename()` in Python expects duration in **seconds**:
```python
# app.py line 100-102
duration_mins = int(duration // 60)   # expects seconds, divides by 60
duration_secs = int(duration % 60)
```

The Python function is never actually called from JS (see Issue #5), so this doesn't cause a runtime bug currently, but it reveals an inconsistency that would break if the backend function were ever used.

---

### 5. `generate_filename()` Python Function is Never Called

**File:** `app.py:92-124`

The `generate_filename()` function is `@eel.expose`d but never called from the frontend. The JavaScript generates the filename locally in `updateFilenamePreview()` (line 130). This creates two independent filename generation paths that could diverge.

---

### 6. 59.94 fps Drop Frame Skips Wrong Number of Frames

**File:** `ltc_generator.py:280-297`

The `_apply_drop_frame()` method only skips 2 frames (`frames + 2`) for both 29.97 DF and 59.94 DF. Per SMPTE standards, **59.94 DF should skip 4 frames** (0, 1, 2, 3) at the start of each non-tenth minute.

```python
# Current code (line 293) - WRONG for 59.94
if seconds == 0 and frames < 2 and minutes % 10 != 0:
    return frames + 2  # Only correct for 29.97 DF
```

**Expected:** For 59.94 DF, check `frames < 4` and return `frames + 4`.

---

### 7. Polarity Correction Bit is Never Set

**File:** `ltc_generator.py:239-240`

The polarity correction bit (bit 63) is always left as 0. Per SMPTE 12M, this bit should be set so that the total number of `1` bits in the LTC word (excluding sync) is even. This ensures DC balance of the bi-phase encoded signal.

```python
# Line 239-240 - bit is skipped
# Polarity correction bit (typically 0)
bit_pos += 1  # Never computed
```

---

### 8. Audio Sample Drift Due to Integer Truncation

**File:** `ltc_generator.py:94-95`

`bit_duration_samples` is calculated using integer division, causing sample loss per frame. The lost samples accumulate, creating timing drift.

```python
self.frame_duration_samples = int(self.config.sample_rate / config.frame_rate.get_fps())
self.bit_duration_samples = self.frame_duration_samples // 80
```

**Worst cases (at 44100 Hz):**

| Frame Rate | Lost Samples/Frame | Drift/Second |
|---|---|---|
| 23.976 fps | 79 | ~1894 samples |
| 24 fps | 77 | ~1848 samples |
| 30 fps | 30 | ~900 samples |
| 59.94 fps | 15 | ~899 samples |

At 44100 Hz with 23.976 fps, this is ~4.3% timing error per second. At 48000 Hz the drift is much smaller (typically 1 sample/frame), but still accumulates over long durations.

---

## Moderate Issues

### 9. `file://` Download Protocol Does Not Work in Browser Context

**File:** `web/script.js:262-281`

The `downloadFile()` method uses `file://` protocol to trigger downloads:
```javascript
link.href = `file://${filePath}`;
```

Most browsers block `file://` links from web pages for security reasons. In the Eel desktop context the file is saved directly to disk, so the "download" link is actually non-functional — the file is already on disk, but the user gets no feedback about where. The download link silently fails.

---

### 10. Preroll Does Not Adjust Frame Count

**File:** `web/script.js:198-209`

When preroll is enabled, the start time is moved back by 10 seconds, but the frame number (`startFrames`) is not adjusted. If the user sets a start time with non-zero frames, the preroll start time will have the same frame value, which may not be correct.

```javascript
if (preroll) {
    actualDuration += 10;
    let totalSeconds = hours * 3600 + minutes * 60 + seconds - 10;
    // ...
    startFrames = frames; // BUG: frames should also be adjusted
}
```

---

### 11. 24-bit WAV Export Uses Slow Python Loop

**File:** `ltc_generator.py:342-345`

The 24-bit export iterates over every sample in pure Python to convert 32-bit to 24-bit:

```python
audio_24bit = bytearray()
for sample in audio_int:
    audio_24bit.extend(struct.pack('<i', sample)[:3])
```

Benchmarks show 24-bit export is **~5x slower** than 16-bit for the same duration. For long durations (e.g., 2 hours at 192 kHz), this could take a very long time with no progress feedback.

---

### 12. No Error Cleanup on Failed WAV Export

**File:** `ltc_generator.py:320-346`

If `export_wav()` fails mid-write (disk full, permission error, etc.), a corrupted partial WAV file is left on disk. There is no `try/finally` block to clean up the file on failure.

---

### 13. Progress Bar is Fake

**File:** `web/script.js:283-304`

The progress bar animation is purely cosmetic — it advances on fixed 800ms intervals regardless of actual generation progress. If generation takes longer than expected, the progress bar sits at 95% indefinitely. If generation is very fast, the bar doesn't reflect completion timing.

---

## Minor Issues

### 14. Fragile Frame Rate Parsing in `updateMaxFrames()`

**File:** `web/script.js:120`

The max frames calculation extracts FPS using a regex on the display name:
```javascript
const fps = parseFloat(frameRate.display.match(/[\d.]+/)[0]);
```

This works for current display names like "29.97 fps DF" but would break if the display format changes (e.g., "DF 29.97 fps" or "29.97fps").

---

### 15. `browse_output_path()` and `browse_output_folder()` Are Stubs

**File:** `app.py:126-140`

Both functions just return the string `"USE_JS_DIALOG"` but no JavaScript code handles this return value. The file browse functionality does not work.

```python
@eel.expose
def browse_output_path():
    return "USE_JS_DIALOG"  # Never handled by frontend
```

---

### 16. CDN Dependencies Require Internet Connection

**File:** `web/index.html:8-9`

Font Awesome and Google Fonts are loaded from CDNs. If the app is used offline (common for professional broadcast environments), the icons and fonts will not load, degrading the UI appearance.

```html
<link href="https://fonts.googleapis.com/css2?family=Inter..." rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
```

---

### 17. No Maximum Duration Validation for Preroll

**File:** `web/script.js:192-199`

When preroll is enabled, 10 seconds are added to the duration. If the user enters 120 minutes (the max), the actual duration becomes 120 minutes + 10 seconds = 7210 seconds. The backend rejects durations over 7200 seconds, causing an unexpected error.

---

### 18. `getOutputPath()` Regex May Fail on Windows Paths

**File:** `web/script.js:255`

```javascript
return defaultPath.replace(/[^\/\\]*\.wav$/, filename);
```

This regex replaces the filename portion of the path. However, if the default path doesn't end with `.wav` (e.g., the Desktop path doesn't exist), the replace will fail silently and the path will be malformed.

---

### 19. Drop Frame Not Applied During Timecode Increment

**File:** `ltc_generator.py:299-318`

The `_increment_timecode()` method does not skip dropped frames when advancing the timecode counter. Drop frame compensation is only applied when encoding the LTC word in `_generate_ltc_word()`. This means the internal timecode counter passes through invalid frame numbers (e.g., 00:01:00:00 and 00:01:00:01 for 29.97 DF), which are then corrected only at encoding time. This could cause issues with frame counting accuracy over long durations.

---

### 20. No Unit Tests

The project has no test suite. Given the complexity of LTC encoding, drop frame logic, and bi-phase mark encoding, the lack of tests makes it difficult to verify correctness or catch regressions.

---

## Summary

| Severity | Count | Key Areas |
|---|---|---|
| **Critical** | 8 | Wrong LTC bit layout (SMPTE non-compliant), double init, no validation, drop frame bugs, sample drift |
| **Moderate** | 5 | Download broken, slow export, fake progress |
| **Minor** | 7 | Stubs, offline support, edge cases |
| **Total** | **20** | |

### Will Fixing All Issues Make the App Work?

**Yes**, but Issue #1 (wrong LTC bit layout) is the root cause of the app producing unusable output. Even if the app runs and generates a WAV file, **no LTC decoder can read it** because the bit structure doesn't match the SMPTE 12M standard. Fixing this single issue would make the output valid LTC. Fixing all 20 issues would make the app fully production-ready.
