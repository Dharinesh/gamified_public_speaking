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
        
        this.initializeElements();
    }

    initializeElements() {
        this.micBtn = document.getElementById('microphone-btn');
        this.voiceVisualizer = document.getElementById('voice-visualizer');
        this.recordingStatus = document.getElementById('recording-status');
        this.recordingTimer = document.getElementById('recording-timer');
        this.loadingOverlay = document.getElementById('loading-overlay');
        
        if (this.micBtn) {
            this.micBtn.addEventListener('click', () => this.toggleRecording());
        }
    }

    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            console.log('Starting recording...');
            
            // Request microphone with specific constraints
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: false,  // Turn off processing that might interfere
                    noiseSuppression: false,
                    autoGainControl: false,
                    sampleRate: 44100,
                    channelCount: 1  // Mono audio
                },
                video: false
            });

            console.log('Microphone access granted');
            console.log('Stream tracks:', this.stream.getTracks());

            // Setup audio context for visualization
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            const source = this.audioContext.createMediaStreamSource(this.stream);
            source.connect(this.analyser);
            
            this.analyser.fftSize = 256;
            this.analyser.smoothingTimeConstant = 0.8;

            // Configure MediaRecorder with simple, reliable options
            let options = {};
            
            // Try different MIME types in order of preference
            const mimeTypes = [
                'audio/webm;codecs=opus',
                'audio/webm',
                'audio/mp4',
                'audio/ogg;codecs=opus',
                ''  // Let browser choose
            ];
            
            for (const mimeType of mimeTypes) {
                if (mimeType === '' || MediaRecorder.isTypeSupported(mimeType)) {
                    options.mimeType = mimeType;
                    console.log('Using MIME type:', mimeType);
                    break;
                }
            }

            this.mediaRecorder = new MediaRecorder(this.stream, options);
            
            console.log('MediaRecorder created with options:', options);
            console.log('MediaRecorder state:', this.mediaRecorder.state);

            this.audioChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                console.log('Data available:', event.data.size, 'bytes');
                if (event.data && event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                console.log('MediaRecorder stopped');
                console.log('Total chunks:', this.audioChunks.length);
                console.log('Total size:', this.audioChunks.reduce((sum, chunk) => sum + chunk.size, 0), 'bytes');
                this.processRecording();
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
                this.showError('Recording error: ' + event.error);
            };

            // Start recording with time slice for better data collection
            this.mediaRecorder.start(1000); // Collect data every second
            this.isRecording = true;
            this.recordingStartTime = Date.now();

            console.log('Recording started');

            this.updateUI('recording');
            this.startTimer();
            this.startVisualization();

        } catch (error) {
            console.error('Error accessing microphone:', error);
            this.showError('Could not access microphone. Please check permissions and try again.');
        }
    }

    stopRecording() {
        console.log('Stopping recording...');
        
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            console.log('MediaRecorder.stop() called');
            
            if (this.stream) {
                this.stream.getTracks().forEach(track => {
                    track.stop();
                    console.log('Track stopped:', track.kind);
                });
            }
            
            if (this.audioContext) {
                this.audioContext.close();
            }

            this.stopTimer();
            this.updateUI('processing');
        }
    }

    startTimer() {
        this.timerInterval = setInterval(() => {
            if (this.recordingStartTime) {
                const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                
                if (this.recordingTimer) {
                    this.recordingTimer.textContent = 
                        `${minutes}:${seconds.toString().padStart(2, '0')}`;
                }
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
        const animate = () => {
            if (!this.isRecording || !this.analyser) return;

            const bufferLength = this.analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            this.analyser.getByteFrequencyData(dataArray);

            // Calculate average volume
            const average = dataArray.reduce((sum, value) => sum + value, 0) / bufferLength;
            const normalizedAverage = average / 255;

            // Update visualizer based on audio input
            if (this.voiceVisualizer && normalizedAverage > 0.1) {
                this.voiceVisualizer.classList.add('active');
                
                // Scale based on audio intensity
                const scale = 1 + (normalizedAverage * 0.5);
                this.voiceVisualizer.style.transform = 
                    `translate(-50%, -50%) scale(${scale})`;
            } else if (this.voiceVisualizer) {
                this.voiceVisualizer.classList.remove('active');
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
        } else if (state === 'processing') {
            this.micBtn.innerHTML = '<i class="fas fa-cog fa-spin"></i>';
        } else {
            this.micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        }
    }

    async processRecording() {
        console.log('Processing recording...');
        console.log('Audio chunks:', this.audioChunks.length);
        
        if (this.audioChunks.length === 0) {
            this.showError('No audio recorded');
            this.updateUI('idle');
            return;
        }

        // Calculate total size
        const totalSize = this.audioChunks.reduce((sum, chunk) => sum + chunk.size, 0);
        console.log('Total audio size:', totalSize, 'bytes');

        if (totalSize === 0) {
            this.showError('Audio file is empty. Please try recording again.');
            this.updateUI('idle');
            return;
        }

        // Create blob from chunks
        const audioBlob = new Blob(this.audioChunks, { 
            type: this.mediaRecorder.mimeType || 'audio/webm' 
        });
        
        console.log('Created audio blob:', audioBlob.size, 'bytes, type:', audioBlob.type);

        // Test the blob by creating a URL (for debugging)
        const audioUrl = URL.createObjectURL(audioBlob);
        console.log('Audio blob URL created:', audioUrl);

        await this.uploadAudio(audioBlob);
    }

    async uploadAudio(audioBlob) {
        // Show loading overlay
        if (this.loadingOverlay) {
            this.loadingOverlay.classList.add('show');
        }

        const formData = new FormData();
        
        // Use the original blob with proper filename
        const fileName = `recording.webm`;
        formData.append('audio', audioBlob, fileName);
        
        console.log('Uploading audio blob:', audioBlob.size, 'bytes');
        
        // Get task context
        const levelNumber = document.getElementById('level-number')?.value;
        const taskId = document.getElementById('task-id')?.value;
        const isQuickTask = document.getElementById('is-quick-task')?.value === 'true';
        const taskPrompt = document.getElementById('task-prompt')?.textContent || '';

        if (levelNumber) formData.append('level_number', levelNumber);
        if (taskId) formData.append('task_id', taskId);
        if (isQuickTask !== undefined) formData.append('is_quick_task', isQuickTask);
        if (taskPrompt) formData.append('task_prompt', taskPrompt);

        try {
            const response = await fetch('/api/upload-audio', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.displayResults(result);
            } else {
                this.showError(result.error || 'Failed to process audio');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showError('Network error. Please try again.');
        } finally {
            // Hide loading overlay
            if (this.loadingOverlay) {
                this.loadingOverlay.classList.remove('show');
            }
            this.updateUI('idle');
            
            // Reset timer display
            if (this.recordingTimer) {
                this.recordingTimer.textContent = '0:00';
            }
        }
    }

    displayResults(result) {
        const resultsContainer = document.getElementById('results-container');
        if (!resultsContainer) return;

        const { transcription, analysis } = result;

        resultsContainer.innerHTML = `
            <div class="results-container">
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
                        <div style="margin-top: 1rem; padding: 1rem; background: var(--bg-primary); border-radius: var(--radius);">
                            <h5>Detailed Analysis</h5>
                            <p>${analysis.detailed_feedback}</p>
                        </div>
                    ` : ''}
                </div>

                <div style="text-align: center; margin-top: 2rem;">
                    <button class="btn btn-primary" onclick="location.reload()">
                        <i class="fas fa-redo"></i> Try Again
                    </button>
                    <a href="/dashboard" class="btn btn-secondary">
                        <i class="fas fa-home"></i> Back to Dashboard
                    </a>
                </div>
            </div>
        `;

        resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }

    showError(message) {
        // Create error flash message
        const flashContainer = document.querySelector('.flash-messages') || 
                             document.querySelector('.main-content');
        
        if (flashContainer) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'flash-message flash-error';
            errorDiv.innerHTML = `
                <span>${message}</span>
                <button class="flash-close" onclick="this.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            if (flashContainer.classList.contains('flash-messages')) {
                flashContainer.appendChild(errorDiv);
            } else {
                flashContainer.insertBefore(errorDiv, flashContainer.firstChild);
            }

            // Auto-remove after 5 seconds
            setTimeout(() => errorDiv.remove(), 5000);
        }
    }
}

// Quick Task Generator
class QuickTaskGenerator {
    constructor() {
        this.generateBtn = document.getElementById('generate-task-btn');
        if (this.generateBtn) {
            this.generateBtn.addEventListener('click', () => this.generateNewTask());
        }
    }

    async generateNewTask() {
        const taskContainer = document.getElementById('quick-task-container');
        if (!taskContainer) return;

        try {
            this.generateBtn.disabled = true;
            this.generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

            const response = await fetch('/api/generate-quick-task');
            const task = await response.json();

            if (response.ok) {
                this.displayTask(task);
            } else {
                throw new Error(task.error || 'Failed to generate task');
            }
        } catch (error) {
            console.error('Task generation error:', error);
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
        // Reuse the error display method from AudioRecorder
        const recorder = new AudioRecorder();
        recorder.showError(message);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize audio recorder if microphone button exists
    if (document.getElementById('microphone-btn')) {
        new AudioRecorder();
    }

    // Initialize quick task generator if on quick task page
    if (document.getElementById('generate-task-btn')) {
        new QuickTaskGenerator();
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