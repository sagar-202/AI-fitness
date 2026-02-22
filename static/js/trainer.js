class EnhancedAIFitnessTrainer {
    constructor() {
        this.pose = null;
        this.currentExercise = 'squats';
        this.frameCount = 0;
        this.isProcessing = false;
        this.animationFrameId = null;
        this.sessionStartTime = null;
        this.voiceEnabled = false;
        this.lastSpokenTime = 0;

        console.log('Initializing AI Fitness Trainer...');

        this.initializeElements();
        this.setupEventListeners();
        this.populateCameraList();
        this.initializePose();

        console.log('AI Fitness Trainer initialized');
    }

    initializeElements() {
        this.videoElement = document.getElementById('videoElement');
        this.canvasElement = document.getElementById('output_canvas');
        this.canvasCtx = this.canvasElement.getContext('2d');
        this.startBtn = document.getElementById('startBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.repCountElement = document.getElementById('repCount');
        this.accuracyElement = document.getElementById('accuracy');
        this.phaseElement = document.getElementById('phase');
        this.feedbackElement = document.getElementById('feedbackText');
        this.loadingElement = document.getElementById('loading');
        this.showHistoryBtn = document.getElementById('showHistoryBtn');
        this.historySection = document.getElementById('history-section');
        this.historyList = document.getElementById('history-list');
        this.cameraSelect = document.getElementById('cameraSelect');
        this.voiceToggle = document.getElementById('voiceToggle');
    }

    setupEventListeners() {
        document.querySelectorAll('.exercise-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('[v0] Exercise button clicked:', btn.dataset.exercise);
                this.selectExercise(btn);
            });
        });
        this.startBtn.addEventListener('click', () => this.startCamera());
        this.stopBtn.addEventListener('click', () => this.stopCamera());
        this.showHistoryBtn.addEventListener('click', () => this.toggleHistory());
        navigator.mediaDevices.addEventListener('devicechange', () => this.populateCameraList());

        if (this.voiceToggle) {
            this.voiceToggle.addEventListener('change', (e) => {
                this.voiceEnabled = e.target.checked;
                if (this.voiceEnabled) {
                    this.speak('Voice feedback enabled');
                }
            });
        }
    }

    async populateCameraList() {
        try {
            // Request permission first to get device labels
            await navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => {
                    // Stop the test stream immediately
                    stream.getTracks().forEach(track => track.stop());
                })
                .catch(() => {
                    console.log('Camera permission not granted yet');
                });

            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');

            this.cameraSelect.innerHTML = '';

            if (videoDevices.length === 0) {
                const option = document.createElement('option');
                option.textContent = 'No cameras found';
                option.disabled = true;
                this.cameraSelect.appendChild(option);
                return;
            }

            videoDevices.forEach((device, index) => {
                const option = document.createElement('option');
                option.value = device.deviceId;
                option.textContent = device.label || `Camera ${index + 1}`;
                this.cameraSelect.appendChild(option);
            });

            console.log(`Found ${videoDevices.length} camera(s)`);
        } catch (error) {
            console.error('Error enumerating devices:', error);
            this.cameraSelect.innerHTML = '<option>Default Camera</option>';
        }
    }

    async selectExercise(button) {
        const exercise = button.dataset.exercise;
        console.log('[v0] Selecting exercise:', exercise);

        try {
            await fetch(`${API_BASE_URL}/api/reset_session`, {
                method: 'POST',
                credentials: 'include'
            });
            console.log('[v0] Backend session reset');
        } catch (error) {
            console.error('[v0] Error resetting backend session:', error);
        }

        document.querySelectorAll('.exercise-btn').forEach(b => b.classList.remove('active'));
        button.classList.add('active');
        this.currentExercise = exercise;
        this.resetStats();

        const exerciseName = exercise.replace('_', ' ');
        document.getElementById('currentExercise').innerHTML = `Current: <strong>${exerciseName.charAt(0).toUpperCase() + exerciseName.slice(1)}</strong>`;

        this.updateFeedback(`${button.textContent.trim().split('\n')[1]} selected. Ready to start!`, 'good');
        console.log('[v0] Current exercise set to:', this.currentExercise);
    }

    async initializePose() {
        this.loadingElement.classList.remove('hidden');
        console.log('Initializing MediaPipe Pose...');

        try {
            this.pose = new Pose({
                locateFile: (file) => {
                    return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
                }
            });

            this.pose.setOptions({
                modelComplexity: 1,
                smoothLandmarks: true,
                enableSegmentation: false,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            });

            this.pose.onResults((results) => this.onPoseResults(results));

            await this.pose.initialize();

            this.loadingElement.classList.add('hidden');
            this.updateFeedback('✅ AI model loaded! Click "Start Camera" to begin.', 'good');
            console.log('MediaPipe Pose initialized successfully');
        } catch (error) {
            console.error('Error initializing pose:', error);
            this.loadingElement.classList.add('hidden');
            this.updateFeedback('Error loading AI model. Please refresh the page.', 'error');
        }
    }

    async startCamera() {
        console.log('🎥 Start Camera button clicked!');
        try {
            const selectedCameraId = this.cameraSelect.value;
            const constraints = {
                video: {
                    deviceId: selectedCameraId === 'Default Camera' ? undefined : { exact: selectedCameraId },
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: false
            };

            const stream = await navigator.mediaDevices.getUserMedia(constraints);

            this.videoElement.srcObject = stream;
            this.videoElement.onloadedmetadata = () => {
                this.videoElement.play();
            };

            await new Promise((resolve) => {
                this.videoElement.onloadeddata = resolve;
            });
            this.sessionStartTime = Date.now();
            this.startPoseDetection();

            this.startBtn.disabled = true;
            this.stopBtn.disabled = false;
            this.updateFeedback('🎥 Camera active! Position yourself and begin.', 'good');

        } catch (error) {
            console.error('Error starting camera:', error);
            let errorMessage = '❌ Camera access denied. ';

            if (error.name === 'NotAllowedError') {
                errorMessage += 'Please allow camera access in browser settings.';
            } else if (error.name === 'NotFoundError') {
                errorMessage += 'No camera found on this device or selected camera is unavailable.';
            } else if (error.name === 'NotReadableError') {
                errorMessage += 'Camera is being used by another application.';
            } else {
                errorMessage += error.message;
            }

            this.updateFeedback(errorMessage, 'error');
            alert('Camera Error:\n\n' + errorMessage + '\n\nPlease check:\n1. Camera permissions in browser settings\n2. Camera is not used by another app\n3. Try selecting a different camera from the dropdown\n4. Try refreshing the page');
        }
    }

    startPoseDetection() {
        const sendFrame = async () => {
            if (this.videoElement.srcObject && this.pose) {
                try {
                    await this.pose.send({ image: this.videoElement });
                } catch (error) {
                    console.error('Error sending frame:', error);
                }
            }
            if (this.videoElement.srcObject) {
                requestAnimationFrame(sendFrame);
            }
        };
        requestAnimationFrame(sendFrame);
    }

    stopCamera() {
        if (this.videoElement.srcObject) {
            const tracks = this.videoElement.srcObject.getTracks();
            tracks.forEach(track => {
                track.stop();
                console.log('Track stopped:', track.kind);
            });
            this.videoElement.srcObject = null;
        }

        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.updateFeedback('Session ended. Great work!', 'good');
        this.saveWorkout();
        this.sessionStartTime = null;
        this.canvasCtx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height);
    }

    async saveWorkout() {
        const reps = parseInt(this.repCountElement.textContent);
        if (reps === 0) return;

        // compute duration (track sessionStartTime on the client when starting)
        const now = Date.now();
        const duration_seconds = this.sessionStartTime ? Math.round((now - this.sessionStartTime) / 1000) : 0;

        // take the last known form score from UI
        const form_score = parseFloat(this.accuracyElement ? this.accuracyElement.textContent : '0') || 0;

        // lightweight calories estimate (client-side)
        const calories_per_rep = { 'squats': 0.32, 'pushups': 0.29, 'lunges': 0.35, 'bicep_curls': 0.20 };
        const base_cal = reps * (calories_per_rep[this.currentExercise] || 0.25);
        const calories_burned = Math.round(base_cal * (0.8 + form_score / 500));

        try {
            const response = await fetch(`${API_BASE_URL}/api/save_workout`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    exercise: this.currentExercise,
                    reps,
                    duration_seconds,
                    form_score,
                    calories_burned
                })
            });
            if (response.ok) {
                const data = await response.json();
                console.log('Workout saved:', data);
                this.fetchAndRenderHistory();
            } else if (response.status === 401) {
                console.error('User not authenticated, cannot save workout.');
            } else {
                console.error('Save workout failed', response.status);
            }
        } catch (error) {
            console.error('Failed to save workout:', error);
        }
        this.resetStats();
    }


    async onPoseResults(results) {
        this.canvasCtx.save();
        this.canvasCtx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height);
        this.canvasElement.width = this.videoElement.videoWidth;
        this.canvasElement.height = this.videoElement.videoHeight;

        if (results.poseLandmarks) {
            drawConnectors(this.canvasCtx, results.poseLandmarks, POSE_CONNECTIONS,
                { color: '#38e1a1', lineWidth: 4 });
            drawLandmarks(this.canvasCtx, results.poseLandmarks,
                { color: '#FFFFFF', lineWidth: 2, radius: 5, fillColor: '#38e1a1' });

            const landmarksArray = results.poseLandmarks.map(l => ({
                x: l.x, y: l.y, z: l.z, visibility: l.visibility
            }));

            this.frameCount++;
            if (this.frameCount % THROTTLE_FRAMES === 0 && !this.isProcessing) {
                this.isProcessing = true;
                try {
                    const exerciseType = this.currentExercise || 'Squats';
                    const response = await fetch(`${API_BASE_URL}/api/analyze_pose`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({
                            exercise: this.currentExercise,
                            landmarks: landmarksArray
                        })
                    });

                    if (response.ok) {
                        const data = await response.json();
                        this.updateStats(data);

                        let feedbackMessage = data.feedback.length > 0
                            ? data.feedback.join(' • ')
                            : 'Keep going! You\'re doing great!';

                        const status = this.determineStatus(data.form_score);
                        this.updateFeedback(feedbackMessage, status);
                        this.updatePhase(data.exercise_phase);
                    } else if (response.status === 401) {
                        this.stopCamera();
                        openAuthModal();
                    } else {
                        this.updateFeedback('Connection error. Check backend.', 'error');
                    }
                } catch (error) {
                    console.error('Analysis error:', error);
                    this.updateFeedback('Error during analysis. Please check console.', 'error');
                } finally {
                    this.isProcessing = false;
                }
            }
        } else {
            this.updateFeedback('⚠️ No pose detected. Ensure you\'re fully visible.', 'warning');
        }

        this.canvasCtx.restore();
    }

    updateStats(data) {
        this.repCountElement.textContent = data.reps;
        this.accuracyElement.textContent = `${Math.round(data.form_score)}%`;

        // Color coding for accuracy
        if (data.form_score >= 80) {
            this.accuracyElement.className = 'text-5xl font-extrabold text-green-400 mb-1';
        } else if (data.form_score >= 50) {
            this.accuracyElement.className = 'text-5xl font-extrabold text-yellow-400 mb-1';
        } else {
            this.accuracyElement.className = 'text-5xl font-extrabold text-red-400 mb-1';
        }
    }

    updatePhase(phase) {
        this.phaseElement.textContent = phase.charAt(0).toUpperCase() + phase.slice(1);
    }

    updateFeedback(message, status) {
        this.feedbackElement.textContent = message;

        const container = this.feedbackElement.parentElement;
        container.className = 'bg-glass p-4 rounded-xl shadow-lg border-l-4 transition-all duration-300';

        if (status === 'good') {
            container.classList.add('border-green-500');
            this.feedbackElement.className = 'text-xl font-bold text-green-300';
        } else if (status === 'warning') {
            container.classList.add('border-yellow-500');
            this.feedbackElement.className = 'text-xl font-bold text-yellow-300';
        } else if (status === 'error') {
            container.classList.add('border-red-500');
            this.feedbackElement.className = 'text-xl font-bold text-red-300';
        } else {
            container.classList.add('border-blue-500');
            container.classList.add('border-blue-500');
            this.feedbackElement.className = 'text-xl font-bold text-blue-300';
        }

        if (this.voiceEnabled && message !== this.lastSpokenMessage) {
            // Throttle speech to avoid overlapping
            const now = Date.now();
            if (now - this.lastSpokenTime > 2000) {
                this.speak(message);
                this.lastSpokenMessage = message;
                this.lastSpokenTime = now;
            }
        }
    }

    speak(text) {
        if (!window.speechSynthesis) return;

        // Cancel previous speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        window.speechSynthesis.speak(utterance);
    }

    determineStatus(score) {
        if (score >= 80) return 'good';
        if (score >= 50) return 'warning';
        return 'error';
    }

    resetStats() {
        this.repCountElement.textContent = '0';
        this.accuracyElement.textContent = '0%';
        this.phaseElement.textContent = 'Ready';
        this.updateFeedback('Ready to start! Press "Start Camera".', 'neutral');
    }

    async toggleHistory() {
        const isHidden = this.historySection.classList.contains('hidden');
        if (isHidden) {
            this.historySection.classList.remove('hidden');
            this.showHistoryBtn.innerHTML = '<i class="fas fa-chevron-up mr-2"></i>Hide Workout History';
            await this.fetchAndRenderHistory();
        } else {
            this.historySection.classList.add('hidden');
            this.showHistoryBtn.innerHTML = '<i class="fas fa-history mr-2"></i>Show Workout History';
        }
    }

    async fetchAndRenderHistory() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/workout_history?limit=10`, {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                this.renderHistory(data.history);
            } else {
                this.historyList.innerHTML = '<li class="p-3 text-red-400">Failed to load history.</li>';
            }
        } catch (error) {
            console.error('Error fetching history:', error);
            this.historyList.innerHTML = '<li class="p-3 text-red-400">Error fetching history.</li>';
        }
    }

    renderHistory(history) {
        if (!history || history.length === 0) {
            this.historyList.innerHTML = '<li class="text-gray-400 text-center py-4">No workouts recorded yet.</li>';
            return;
        }

        this.historyList.innerHTML = history.map(item => {
            const date = new Date(item.session_date).toLocaleDateString();
            const time = new Date(item.session_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            return `
                <li class="history-item bg-gray-800/50 p-4 rounded-lg border border-gray-700 relative group">
                    <button onclick="aiTrainerInstance.deleteWorkout(${item.id})" class="absolute top-2 right-2 text-gray-500 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                        <i class="fas fa-trash"></i>
                    </button>
                    <div class="flex justify-between items-center mb-2 pr-6">
                        <span class="font-bold text-green-400 text-lg capitalize">${item.exercise_name.replace('_', ' ')}</span>
                        <span class="text-xs text-gray-400">${date} • ${time}</span>
                    </div>
                    <div class="grid grid-cols-3 gap-2 text-sm">
                        <div class="bg-gray-900/50 p-2 rounded text-center">
                            <div class="text-gray-400 text-xs">Reps</div>
                            <div class="font-bold text-white">${item.total_reps}</div>
                        </div>
                        <div class="bg-gray-900/50 p-2 rounded text-center">
                            <div class="text-gray-400 text-xs">Form</div>
                            <div class="font-bold ${item.avg_form_score >= 80 ? 'text-green-400' : 'text-yellow-400'}">
                                ${Math.round(item.avg_form_score)}%
                            </div>
                        </div>
                        <div class="bg-gray-900/50 p-2 rounded text-center">
                            <div class="text-gray-400 text-xs">Cals</div>
                            <div class="font-bold text-orange-400">${item.calories_burned}</div>
                        </div>
                    </div>
                </li>
            `;
        }).join('');
    }

    async deleteWorkout(id) {
        if (!confirm('Are you sure you want to delete this workout?')) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/workout/${id}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (response.ok) {
                this.fetchAndRenderHistory();
                this.updateFeedback('Workout deleted successfully', 'good');
            } else {
                this.updateFeedback('Failed to delete workout', 'error');
            }
        } catch (error) {
            console.error('Error deleting workout:', error);
            this.updateFeedback('Error deleting workout', 'error');
        }
    }
}
