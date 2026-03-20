// LTC Timecode Generator JavaScript

class LTCApp {
    constructor() {
        this.frameRates = [];
        this.sampleRates = [];
        this.bitDepths = [];
        this.init();
    }

    async init() {
        await this.loadConfigData();
        this.setupEventListeners();
        this.initDarkMode();
        this.updateFilenamePreview();
        this.updateSizeEstimate();
    }

    async loadConfigData() {
        try {
            // Load frame rates
            this.frameRates = await eel.get_frame_rates()();
            this.populateFrameRates();

            // Load sample rates
            this.sampleRates = await eel.get_sample_rates()();
            this.populateSampleRates();

            // Load bit depths
            this.bitDepths = await eel.get_bit_depths()();
            this.populateBitDepths();
        } catch (error) {
            console.error('Error loading configuration data:', error);
            this.showToast('Error loading configuration data', 'error');
        }
    }

    populateFrameRates() {
        const frameRateSelect = document.getElementById('frameRate');
        frameRateSelect.innerHTML = '';

        this.frameRates.forEach(frameRate => {
            const option = document.createElement('option');
            option.value = frameRate.name;
            option.textContent = frameRate.display;
            if (frameRate.name === 'FR_30_NDF') {
                option.selected = true;
            }
            frameRateSelect.appendChild(option);
        });
    }

    populateSampleRates() {
        const sampleRateSelect = document.getElementById('sampleRate');
        sampleRateSelect.innerHTML = '';

        this.sampleRates.forEach(rate => {
            const option = document.createElement('option');
            option.value = rate;

            if (rate >= 1000) {
                option.textContent = `${(rate / 1000).toFixed(1)} kHz`;
            } else {
                option.textContent = `${rate} Hz`;
            }

            if (rate === 48000) {
                option.selected = true;
            }
            sampleRateSelect.appendChild(option);
        });
    }

    populateBitDepths() {
        const bitDepthSelect = document.getElementById('bitDepth');
        bitDepthSelect.innerHTML = '';

        this.bitDepths.forEach(depth => {
            const option = document.createElement('option');
            option.value = depth;
            option.textContent = `${depth}-bit`;
            if (depth === 16) {
                option.selected = true;
            }
            bitDepthSelect.appendChild(option);
        });
    }

    setupEventListeners() {
        // Form submission
        document.getElementById('ltcForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateLTC();
        });

        // Update filename preview on input changes
        const inputs = ['hours', 'minutes', 'seconds', 'frames', 'duration', 'frameRate', 'bitDepth', 'sampleRate'];
        inputs.forEach(inputId => {
            const element = document.getElementById(inputId);
            if (element) {
                element.addEventListener('input', () => { this.updateFilenamePreview(); this.updateSizeEstimate(); });
                element.addEventListener('change', () => { this.updateFilenamePreview(); this.updateSizeEstimate(); });
            }
        });

        // Frame rate change handler to update max frames
        document.getElementById('frameRate').addEventListener('change', (e) => {
            this.updateMaxFrames(e.target.value);
            this.updateFilenamePreview();
            this.updateSizeEstimate();
        });

        // Preroll checkbox
        document.getElementById('preroll').addEventListener('change', () => {
            this.updateFilenamePreview();
            this.updateSizeEstimate();
        });

        // Duration preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.getElementById('duration').value = btn.dataset.duration;
                this.updateFilenamePreview();
                this.updateSizeEstimate();
            });
        });

        // Dark mode toggle
        document.getElementById('darkToggle').addEventListener('click', () => {
            this.toggleDarkMode();
        });
    }

    updateMaxFrames(frameRateName) {
        const framesInput = document.getElementById('frames');
        const maxFramesMap = {
            'FR_23_976_NDF': 23, 'FR_24_NDF': 23, 'FR_25_NDF': 24,
            'FR_29_97_NDF': 29, 'FR_29_97_DF': 29, 'FR_30_NDF': 29,
            'FR_50_NDF': 49, 'FR_59_94_NDF': 59, 'FR_59_94_DF': 59, 'FR_60_NDF': 59
        };
        const maxFrame = maxFramesMap[frameRateName];
        if (maxFrame !== undefined) {
            framesInput.max = maxFrame;
            if (parseInt(framesInput.value) > maxFrame) {
                framesInput.value = maxFrame;
            }
        }
    }

    updateFilenamePreview() {
        const hours = document.getElementById('hours').value.padStart(2, '0');
        const minutes = document.getElementById('minutes').value.padStart(2, '0');
        const seconds = document.getElementById('seconds').value.padStart(2, '0');
        const frames = document.getElementById('frames').value.padStart(2, '0');
        const duration = parseFloat(document.getElementById('duration').value);
        const frameRate = document.getElementById('frameRate').value;
        const bitDepth = document.getElementById('bitDepth').value;
        const sampleRate = parseInt(document.getElementById('sampleRate').value);
        const preroll = document.getElementById('preroll').checked;

        // Format duration
        const durationMins = Math.floor(duration);
        const durationSecs = Math.round((duration - durationMins) * 60);
        const durationStr = `${durationMins}m${durationSecs.toString().padStart(2, '0')}s`;

        // Format frame rate for filename
        const frameRateDisplay = this.frameRates.find(fr => fr.name === frameRate)?.display || '30fps';
        const fpsStr = frameRateDisplay.replace(' ', '').toLowerCase().replace('fps', 'fps');

        // Format sample rate
        const sampleRateStr = sampleRate >= 1000 ? `${sampleRate / 1000}khz` : `${sampleRate}hz`;

        // Build filename
        let filename = `LTC_${hours}-${minutes}-${seconds}-${frames}_${durationStr}_${fpsStr}_${bitDepth}bit_${sampleRateStr}`;

        if (preroll) {
            filename += '_preroll';
        }

        filename += '.wav';

        document.getElementById('filenamePreview').textContent = filename;
    }

    updateSizeEstimate() {
        const duration = parseFloat(document.getElementById('duration').value) * 60; // seconds
        const sampleRate = parseInt(document.getElementById('sampleRate').value);
        const bitDepth = parseInt(document.getElementById('bitDepth').value);
        const preroll = document.getElementById('preroll').checked;

        let totalDuration = duration;
        if (preroll) {
            totalDuration += 10;
        }

        // Mono WAV: duration * sampleRate * (bitDepth / 8) bytes
        const sizeBytes = totalDuration * sampleRate * (bitDepth / 8);
        const sizeMB = sizeBytes / 1048576;

        const sizeEstimateEl = document.getElementById('sizeEstimate');
        if (sizeEstimateEl) {
            if (sizeMB >= 1) {
                sizeEstimateEl.textContent = `Estimated file size: ~${sizeMB.toFixed(1)} MB`;
            } else {
                const sizeKB = sizeBytes / 1024;
                sizeEstimateEl.textContent = `Estimated file size: ~${sizeKB.toFixed(0)} KB`;
            }
        }
    }

    async generateLTC() {
        const generateBtn = document.getElementById('generateBtn');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');

        try {
            // Validate inputs before proceeding
            const errors = this.validateInputs();
            if (errors.length > 0) {
                this.showToast(errors.join(', '), 'error');
                return;
            }

            // Get form values
            const hours = parseInt(document.getElementById('hours').value);
            const minutes = parseInt(document.getElementById('minutes').value);
            const seconds = parseInt(document.getElementById('seconds').value);
            const frames = parseInt(document.getElementById('frames').value);
            const duration = parseFloat(document.getElementById('duration').value) * 60; // Convert to seconds
            const frameRate = document.getElementById('frameRate').value;
            const bitDepth = parseInt(document.getElementById('bitDepth').value);
            const sampleRate = parseInt(document.getElementById('sampleRate').value);
            const preroll = document.getElementById('preroll').checked;

            // Confirmation for long generations
            if (duration > 600) {
                const size = Math.round(duration * sampleRate * (bitDepth / 8) / 1048576);
                if (!confirm(`This will generate ~${size} MB of audio (${Math.round(duration/60)} min). Continue?`)) return;
            }

            // Disable button and show progress
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fas fa-spinner loading" aria-hidden="true"></i> Generating...';
            progressContainer.style.display = 'block';

            // Simulate progress
            this.animateProgress(progressFill, progressText);

            // Adjust duration for preroll
            let actualDuration = duration;
            let startHours = hours;
            let startMinutes = minutes;
            let startSeconds = seconds;
            let startFrames = frames;

            if (preroll) {
                actualDuration += 10; // Add 10 seconds for preroll
                // Calculate preroll start time (10 seconds before)
                let totalSeconds = hours * 3600 + minutes * 60 + seconds - 10;
                if (totalSeconds < 0) {
                    totalSeconds += 24 * 3600; // Wrap around midnight
                }
                startHours = Math.floor(totalSeconds / 3600);
                startMinutes = Math.floor((totalSeconds % 3600) / 60);
                startSeconds = totalSeconds % 60;
                startFrames = frames;  // Preserve original frame offset
            }

            if (actualDuration > 7200) {
                this.showToast('Error: Duration with preroll exceeds 2 hour maximum', 'error');
                return;
            }

            // Generate filename
            const filename = document.getElementById('filenamePreview').textContent;
            const outputPath = await this.getOutputPath(filename);

            // Call Python backend to generate LTC
            const result = await eel.generate_ltc(
                frameRate, sampleRate, bitDepth,
                startHours, startMinutes, startSeconds, startFrames,
                actualDuration, outputPath
            )();

            if (result.success) {
                progressFill.value = 100;
                progressText.textContent = 'Generation complete!';

                // Show success message
                this.showToast(`LTC file generated successfully: ${filename}`, 'success');

                // Trigger download
                this.downloadFile(outputPath, filename);
            } else {
                throw new Error(result.message);
            }

        } catch (error) {
            console.error('Error generating LTC:', error);
            this.showToast(`Error: ${error.message || 'Failed to generate LTC file'}`, 'error');
        } finally {
            // Reset button and hide progress
            setTimeout(() => {
                generateBtn.disabled = false;
                generateBtn.innerHTML = '<i class="fas fa-download" aria-hidden="true"></i> Generate & Download LTC';
                progressContainer.style.display = 'none';
                progressFill.value = 0;
            }, 2000);
        }
    }

    async getOutputPath(filename) {
        try {
            const defaultPath = await eel.get_default_output_path()();
            const result = defaultPath.replace(/[^\/\\]*\.wav$/, filename);
            if (result === defaultPath) {
                // Regex didn't match — construct path by joining directory + filename
                const separator = defaultPath.includes('\\') ? '\\' : '/';
                const dir = defaultPath.substring(0, defaultPath.lastIndexOf(separator) + 1);
                return dir ? dir + filename : filename;
            }
            return result;
        } catch (error) {
            return `./${filename}`;
        }
    }

    downloadFile(filePath, filename) {
        this.showToast('File saved to: ' + filePath, 'success');
    }

    animateProgress(progressFill, progressText) {
        progressFill.value = 50;
        progressText.textContent = 'Generating...';
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type}`;
        toast.classList.add('show');

        toast.addEventListener('click', () => toast.classList.remove('show'), { once: true });

        setTimeout(() => {
            toast.classList.remove('show');
        }, 8000);
    }

    // Dark mode
    initDarkMode() {
        const darkMode = localStorage.getItem('darkMode') === 'true';
        if (darkMode) {
            document.body.classList.add('dark-mode');
            this.updateDarkToggleIcon(true);
        }
    }

    toggleDarkMode() {
        const isDark = document.body.classList.toggle('dark-mode');
        localStorage.setItem('darkMode', isDark);
        this.updateDarkToggleIcon(isDark);
    }

    updateDarkToggleIcon(isDark) {
        const toggle = document.getElementById('darkToggle');
        if (toggle) {
            toggle.innerHTML = isDark
                ? '<i class="fas fa-sun" aria-hidden="true"></i>'
                : '<i class="fas fa-moon" aria-hidden="true"></i>';
        }
    }

    // Utility function to format time
    formatTime(hours, minutes, seconds, frames) {
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
    }

    // Validate form inputs
    validateInputs() {
        const hours = parseInt(document.getElementById('hours').value);
        const minutes = parseInt(document.getElementById('minutes').value);
        const seconds = parseInt(document.getElementById('seconds').value);
        const frames = parseInt(document.getElementById('frames').value);
        const duration = parseFloat(document.getElementById('duration').value);

        const errors = [];

        if (hours < 0 || hours > 23) errors.push('Hours must be between 0 and 23');
        if (minutes < 0 || minutes > 59) errors.push('Minutes must be between 0 and 59');
        if (seconds < 0 || seconds > 59) errors.push('Seconds must be between 0 and 59');
        if (frames < 0) errors.push('Frames cannot be negative');
        if (duration <= 0 || duration > 120) errors.push('Duration must be between 0.1 and 120 minutes');

        return errors;
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.ltcApp = new LTCApp();
});

// Handle Eel connection errors
window.addEventListener('error', (e) => {
    if (e.message.includes('eel')) {
        console.error('Eel connection error:', e);
        document.getElementById('toast').textContent = 'Connection error with backend service';
        document.getElementById('toast').className = 'toast error show';
    }
});
