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
        this.updateFilenamePreview();
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
                element.addEventListener('input', () => this.updateFilenamePreview());
                element.addEventListener('change', () => this.updateFilenamePreview());
            }
        });

        // Frame rate change handler to update max frames
        document.getElementById('frameRate').addEventListener('change', (e) => {
            this.updateMaxFrames(e.target.value);
            this.updateFilenamePreview();
        });

        // Preroll checkbox
        document.getElementById('preroll').addEventListener('change', () => this.updateFilenamePreview());
    }

    updateMaxFrames(frameRateName) {
        const framesInput = document.getElementById('frames');
        // Get the frame rate info to determine max frames
        const frameRate = this.frameRates.find(fr => fr.name === frameRateName);
        if (frameRate) {
            // Extract fps from display name and set max frames
            const fps = parseFloat(frameRate.display.match(/[\d.]+/)[0]);
            framesInput.max = Math.floor(fps) - 1;
            
            // Validate current value
            if (parseInt(framesInput.value) > parseInt(framesInput.max)) {
                framesInput.value = framesInput.max;
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

    async generateLTC() {
        const generateBtn = document.getElementById('generateBtn');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');

        try {
            // Disable button and show progress
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fas fa-spinner loading"></i> Generating...';
            progressContainer.style.display = 'block';

            // Simulate progress
            this.animateProgress(progressFill, progressText);

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
                // Keep the same frame for simplicity
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
                progressFill.style.width = '100%';
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
                generateBtn.innerHTML = '<i class="fas fa-download"></i> Generate & Download LTC';
                progressContainer.style.display = 'none';
                progressFill.style.width = '0%';
            }, 2000);
        }
    }

    async getOutputPath(filename) {
        // For web environment, we'll use a default path
        // In a real implementation, you might want to use the browser's download folder
        try {
            const defaultPath = await eel.get_default_output_path()();
            // Replace the default filename with our generated filename
            return defaultPath.replace(/[^\/\\]*\.wav$/, filename);
        } catch (error) {
            // Fallback to current directory
            return `./${filename}`;
        }
    }

    downloadFile(filePath, filename) {
        // In a web environment, we need to handle file download differently
        // This is a simplified approach - in production, you'd want to serve the file via HTTP
        
        // Create a temporary link for download
        const link = document.createElement('a');
        link.style.display = 'none';
        
        // For local files, we can use the file:// protocol (with limitations)
        // In production, you'd serve the file via a web server
        try {
            link.href = `file://${filePath}`;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.warn('Direct file download not supported, file saved to:', filePath);
        }
    }

    animateProgress(progressFill, progressText) {
        const steps = [
            { progress: 20, text: 'Initializing LTC generator...' },
            { progress: 40, text: 'Generating timecode data...' },
            { progress: 60, text: 'Encoding bi-phase mark audio...' },
            { progress: 80, text: 'Creating WAV file...' },
            { progress: 95, text: 'Finalizing output...' }
        ];

        let currentStep = 0;
        const animate = () => {
            if (currentStep < steps.length) {
                const step = steps[currentStep];
                progressFill.style.width = `${step.progress}%`;
                progressText.textContent = step.text;
                currentStep++;
                setTimeout(animate, 800);
            }
        };

        animate();
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type}`;
        toast.classList.add('show');

        setTimeout(() => {
            toast.classList.remove('show');
        }, 5000);
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
