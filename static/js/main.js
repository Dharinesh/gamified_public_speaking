class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.audioContext = null;
        this.analyser = null;
        this.recordingStartTime = null;
        this.timerInterval = null;
        this.isProcessing = false;
        this.isUploading = false; // NEW: Prevent duplicate uploads
        
        // WAV recording setup
        this.sampleRate = 44100;
        this.recordedBuffers = [];
        this.processor = null;
        
        this.initializeElements();
    }

    initializeElements() {
        this.micBtn = document.getElementById('microphone-btn');
        this.voiceVisualizer = document.getElementById('voice-visualizer');
        this.recordingStatus = document.getElementById('recording-status');
        this.recordingTimer = document.getElementById('recording-timer');
        this.loadingOverlay = document.getElementById('loading-overlay');
        
        if (this.micBtn) {
            // Remove any existing listeners to prevent duplicates
            this.micBtn.replaceWith(this.micBtn.cloneNode(true));
            this.micBtn = document.getElementById('microphone-btn');
            
            // Add single click listener with comprehensive debounce
            this.micBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                this.handleMicrophoneClick();
            }, { once: false });
        }
    }

    handleMicrophoneClick() {
        // Comprehensive state checking to prevent multiple clicks
        if (this.isProcessing || this.isUploading) {
            console.log('Already processing/uploading, ignoring click');
            return;
        }

        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }

    async startRecording() {
        if (this.isRecording || this.isProcessing || this.isUploading) {
            console.log('Already recording, processing, or uploading');
            return;
        }

        try {
            console.log('Starting WAV recording...');
            this.isProcessing = true;
            
            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: this.sampleRate,
                    channelCount: 1
                },
                video: false
            });

            console.log('Microphone access granted');

            // Setup audio context for WAV recording
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate
            });
            
            this.analyser = this.audioContext.createAnalyser();
            const source = this.audioContext.createMediaStreamSource(this.stream);
            source.connect(this.analyser);
            
            this.analyser.fftSize = 256;
            this.analyser.smoothingTimeConstant = 0.8;

            // Setup WAV recording using ScriptProcessorNode
            this.recordedBuffers = [];
            
            // Create processor for recording raw audio data
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            
            this.processor.onaudioprocess = (event) => {
                if (this.isRecording) {
                    const inputBuffer = event.inputBuffer;
                    const inputData = inputBuffer.getChannelData(0);
                    
                    // Copy the data (important: create new array)
                    const bufferCopy = new Float32Array(inputData.length);
                    bufferCopy.set(inputData);
                    this.recordedBuffers.push(bufferCopy);
                }
            };

            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            this.isRecording = true;
            this.isProcessing = false; // Allow stopping
            this.recordingStartTime = Date.now();

            console.log('WAV recording started');

            this.updateUI('recording');
            this.startTimer();
            this.startVisualization();

        } catch (error) {
            console.error('Error accessing microphone:', error);
            this.isProcessing = false;
            this.showError('Could not access microphone. Please check permissions and try again.');
        }
    }

    stopRecording() {
        if (!this.isRecording || this.isProcessing) {
            console.log('Not recording or already processing');
            return;
        }

        console.log('Stopping WAV recording...');
        this.isProcessing = true;
        this.isRecording = false;
        
        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                track.stop();
                console.log('Track stopped:', track.kind);
            });
        }

        this.stopTimer();
        this.updateUI('processing');
        
        // Process the recorded buffers into WAV
        setTimeout(() => {
            this.processWAVRecording();
        }, 100); // Small delay to ensure all processing is done
    }

    processWAVRecording() {
        console.log('Processing WAV recording...');
        console.log('Recorded buffers:', this.recordedBuffers.length);
        
        if (this.recordedBuffers.length === 0) {
            this.showError('No audio recorded');
            this.resetRecorder();
            return;
        }

        // Calculate total length
        const totalLength = this.recordedBuffers.reduce((sum, buffer) => sum + buffer.length, 0);
        console.log('Total samples:', totalLength);

        if (totalLength === 0) {
            this.showError('Audio recording is empty. Please try again.');
            this.resetRecorder();
            return;
        }

        // Check if we have enough audio (at least 1 second at 44100 Hz)
        if (totalLength < 44100) {
            this.showError('Recording too short. Please speak for at least 1 second.');
            this.resetRecorder();
            return;
        }

        // Combine all buffers into one
        const combinedBuffer = new Float32Array(totalLength);
        let offset = 0;
        
        for (const buffer of this.recordedBuffers) {
            combinedBuffer.set(buffer, offset);
            offset += buffer.length;
        }

        // Convert to WAV format
        const wavBlob = this.createWAVBlob(combinedBuffer, this.sampleRate);
        console.log('Created WAV blob:', wavBlob.size, 'bytes');

        // Verify the blob has content
        if (wavBlob.size < 1000) {
            this.showError('Audio file too small. Please try recording again.');
            this.resetRecorder();
            return;
        }

        this.uploadAudio(wavBlob);
    }

    createWAVBlob(audioBuffer, sampleRate) {
        const length = audioBuffer.length;
        const arrayBuffer = new ArrayBuffer(44 + length * 2);
        const view = new DataView(arrayBuffer);

        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };

        const writeUint32 = (offset, value) => {
            view.setUint32(offset, value, true);
        };

        const writeUint16 = (offset, value) => {
            view.setUint16(offset, value, true);
        };

        // RIFF header
        writeString(0, 'RIFF');
        writeUint32(4, 36 + length * 2);
        writeString(8, 'WAVE');

        // fmt chunk
        writeString(12, 'fmt ');
        writeUint32(16, 16);
        writeUint16(20, 1); // PCM format
        writeUint16(22, 1); // Mono
        writeUint32(24, sampleRate);
        writeUint32(28, sampleRate * 2);
        writeUint16(32, 2);
        writeUint16(34, 16);

        // data chunk
        writeString(36, 'data');
        writeUint32(40, length * 2);

        // Convert float samples to 16-bit PCM
        let offset = 44;
        for (let i = 0; i < length; i++) {
            const sample = Math.max(-1, Math.min(1, audioBuffer[i]));
            view.setInt16(offset, sample * 0x7FFF, true);
            offset += 2;
        }

        return new Blob([arrayBuffer], { type: 'audio/wav' });
    }

    async uploadAudio(audioBlob) {
        // CRITICAL: Check if already uploading to prevent duplicates
        if (this.isUploading) {
            console.log('Upload already in progress, skipping');
            return;
        }

        this.isUploading = true; // Set upload flag immediately
        
        try {
            // Show loading overlay
            if (this.loadingOverlay) {
                this.loadingOverlay.classList.add('show');
            }

            const formData = new FormData();
            
            // Use proper WAV filename with timestamp
            const fileName = `recording_${Date.now()}.wav`;
            formData.append('audio', audioBlob, fileName);
            
            console.log('Uploading WAV audio blob of size:', audioBlob.size);

            // Add task info if available
            const levelNumber = window.currentLevelNumber || null;
            const taskId = window.currentTaskId || null;
            const isQuickTask = window.isQuickTask || false;
            const taskPrompt = window.currentTaskPrompt || '';
            
            if (levelNumber) formData.append('level_number', levelNumber);
            if (taskId) formData.append('task_id', taskId);
            formData.append('is_quick_task', isQuickTask);
            if (taskPrompt) formData.append('task_prompt', taskPrompt);

            // SINGLE REQUEST - with timeout to prevent hanging
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

            const response = await fetch('/api/upload-audio', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Upload failed');
            }

            const result = await response.json();
            console.log('Upload successful:', result);
            
            this.displayResults(result.transcription, result.analysis);

        } catch (error) {
            if (error.name === 'AbortError') {
                this.showError('Upload timed out. Please try again.');
            } else {
                console.error('Upload error:', error);
                this.showError(`Upload failed: ${error.message}`);
            }
        } finally {
            // Always reset states
            this.isProcessing = false;
            this.isUploading = false;
            if (this.loadingOverlay) {
                this.loadingOverlay.classList.remove('show');
            }
            this.updateUI('idle');
        }
    }

    resetRecorder() {
        this.isRecording = false;
        this.isProcessing = false;
        this.isUploading = false;
        this.recordedBuffers = [];
        this.updateUI('idle');
        
        if (this.recordingTimer) {
            this.recordingTimer.textContent = '0:00';
        }
    }

    startTimer() {
        this.timerInterval = setInterval(() => {
            if (this.recordingStartTime && this.recordingTimer) {
                const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                this.recordingTimer.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    startVisualization() {
        if (!this.analyser || !this.voiceVisualizer) return;

        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        
        const animate = () => {
            if (!this.isRecording) return;
            
            this.analyser.getByteFrequencyData(dataArray);
            const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
            
            const scale = Math.min(average / 50, 1);
            if (this.voiceVisualizer) {
                this.voiceVisualizer.classList.add('active');
                this.voiceVisualizer.style.transform = 
                    `translate(-50%, -50%) scale(${1 + scale})`;
            }

            requestAnimationFrame(animate);
        };

        animate();
    }

    updateUI(state) {
        if (!this.micBtn) return;

        this.micBtn.className = `microphone-btn ${state}`;
        
        const statusTexts = {
            idle: 'Click to start recording',
            recording: 'Recording... Click to stop',
            processing: 'Processing your speech...'
        };

        if (this.recordingStatus) {
            this.recordingStatus.textContent = statusTexts[state] || statusTexts.idle;
        }

        if (state === 'recording') {
            this.micBtn.innerHTML = '<i class="fas fa-stop"></i>';
            this.micBtn.disabled = false;
        } else if (state === 'processing') {
            this.micBtn.innerHTML = '<i class="fas fa-cog fa-spin"></i>';
            this.micBtn.disabled = true;
        } else {
            this.micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
            this.micBtn.disabled = false;
        }

        // Update voice visualizer
        if (this.voiceVisualizer) {
            if (state === 'recording') {
                this.voiceVisualizer.classList.add('active');
            } else {
                this.voiceVisualizer.classList.remove('active');
                this.voiceVisualizer.style.transform = 'translate(-50%, -50%) scale(1)';
            }
        }
    }

    displayResults(transcription, analysis) {
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="results-display">
                    <div class="transcription-display">
                        <h4><i class="fas fa-quote-left"></i> Your Speech</h4>
                        <p>${transcription}</p>
                    </div>

                    <div class="analysis-grid">
                        <div class="metric-card">
                            <div class="metric-value">${analysis.flow_score || 0}</div>
                            <div class="metric-label">Flow Score</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${analysis.confidence_score || 0}</div>
                            <div class="metric-label">Confidence</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${analysis.filler_count || 0}</div>
                            <div class="metric-label">Filler Words</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${analysis.repetition_score || 0}</div>
                            <div class="metric-label">Clarity</div>
                        </div>
                    </div>

                    <div class="feedback-section">
                        <h4><i class="fas fa-lightbulb"></i> AI Feedback</h4>
                        <div class="feedback-grid">
                            <div class="feedback-item">
                                <h5>Flow Assessment</h5>
                                <p>${analysis.summary?.flow || 'No feedback available'}</p>
                            </div>
                            <div class="feedback-item">
                                <h5>Areas to Improve</h5>
                                <p>${analysis.summary?.weakness || 'No feedback available'}</p>
                            </div>
                            <div class="feedback-item">
                                <h5>Growth Potential</h5>
                                <p>${analysis.summary?.growth_potential || 'No feedback available'}</p>
                            </div>
                        </div>
                        
                        ${analysis.detailed_feedback ? `
                            <div class="detailed-feedback">
                                <h5>Detailed Analysis</h5>
                                <p>${analysis.detailed_feedback}</p>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
            resultsContainer.style.display = 'block';
            resultsContainer.scrollIntoView({ behavior: 'smooth' });
        }
    }

    showError(message) {
        // Create or update error display
        let errorDiv = document.getElementById('error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'error-message';
            errorDiv.className = 'error-message';
            errorDiv.style.cssText = `
                background: #ff4444;
                color: white;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
                text-align: center;
                font-weight: 500;
            `;
            const container = document.querySelector('#recording-section') || document.body;
            container.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (errorDiv && errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }
}

// Quick Task Generator class
class QuickTaskGenerator {
    constructor() {
        this.generateBtn = document.getElementById('generate-task-btn');
        this.initializeElements();
    }

    initializeElements() {
        if (this.generateBtn) {
            this.generateBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.generateTask();
            });
        }
    }

    async generateTask() {
        if (this.generateBtn.disabled) return;

        try {
            this.generateBtn.disabled = true;
            this.generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

            const response = await fetch('/api/generate-quick-task');
            if (!response.ok) {
                throw new Error('Failed to generate task');
            }

            const task = await response.json();
            this.displayTask(task);

            // Update global variables for task context
            window.currentTaskPrompt = task.sentence_starter;
            window.isQuickTask = true;

        } catch (error) {
            console.error('Generate task error:', error);
            this.showError('Failed to generate new task. Please try again.');
        } finally {
            this.generateBtn.disabled = false;
            this.generateBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Generate New Task';
        }
    }

    displayTask(task) {
        const taskContainer = document.getElementById('quick-task-container');
        if (!taskContainer) return;

        document.getElementById('task-prompt').textContent = task.sentence_starter;
        document.getElementById('task-example').textContent = task.example_completion;
        document.getElementById('task-hint').textContent = task.topic_hint;
    }

    showError(message) {
        const recorder = new AudioRecorder();
        recorder.showError(message);
    }
}

// Level page functionality
function setupLevelPage() {
    // Task selection handlers
    const taskBtns = document.querySelectorAll('.task-select-btn');
    taskBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const taskId = this.dataset.taskId;
            const taskCard = this.closest('.task-card');
            const prompt = taskCard.querySelector('.task-prompt').textContent.trim();
            const example = taskCard.querySelector('.task-example')?.textContent.trim();
            
            // Set global variables
            window.currentTaskId = taskId;
            window.currentTaskPrompt = prompt;
            window.isQuickTask = false;
            
            // Update UI
            document.getElementById('task-prompt').textContent = prompt;
            if (example) {
                document.getElementById('task-example').textContent = example;
                document.getElementById('task-example').style.display = 'block';
            }
            
            // Show recording interface
            document.getElementById('task-selection').style.display = 'none';
            document.getElementById('selected-task').style.display = 'block';
            document.getElementById('recording-section').style.display = 'block';
        });
    });
}

function backToTaskSelection() {
    document.getElementById('task-selection').style.display = 'block';
    document.getElementById('selected-task').style.display = 'none';
    document.getElementById('recording-section').style.display = 'none';
    document.getElementById('results-container').style.display = 'none';
    
    // Clear global variables
    window.currentTaskId = null;
    window.currentTaskPrompt = '';
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize audio recorder if microphone button exists
    if (document.getElementById('microphone-btn')) {
        window.audioRecorder = new AudioRecorder();
    }

    // Initialize quick task generator if on quick task page
    if (document.getElementById('generate-task-btn')) {
        new QuickTaskGenerator();
    }

    // Setup level page functionality
    if (document.querySelector('.task-select-btn')) {
        setupLevelPage();
    }

    // Auto-remove flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            if (message.parentNode) {
                message.remove();
            }
        }, 5000);
    });

    // Level card click handlers
    const levelCards = document.querySelectorAll('.level-card:not(.locked)');
    levelCards.forEach(card => {
        card.addEventListener('click', () => {
            const levelNumber = card.dataset.level;
            if (levelNumber) {
                window.location.href = `/level/${levelNumber}`;
            }
        });
    });
});

// Utility functions
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('show');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('show');
    }
}