const API_BASE_URL = 'http://127.0.0.1:5000';
const THROTTLE_FRAMES = 3; // Reduced for better responsiveness
let currentUser = null;
let backendAvailable = false;

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 AI Fitness Trainer Loading...');

    // Check if browser supports required features
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('⚠️ Your browser does not support camera access.\n\nPlease use Chrome, Firefox, or Edge.');
        return;
    }

    await checkBackendConnection();

    const homeLink = document.querySelector('.nav-link[onclick*="home-page"]');
    if (homeLink) showPage('home-page', homeLink);

    // Check for HTTPS
    if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
        console.warn('⚠️ HTTPS recommended for camera access');
    }

    console.log('✅ Application Ready!');



    // Modal close on outside click
    const authModal = document.getElementById('authModal');
    if (authModal) {
        authModal.addEventListener('click', (e) => {
            if (e.target.id === 'authModal') closeAuthModal();
        });
    }

    // Login Form Handler
    const loginForm = document.getElementById('loginFormElement');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('loginUsername').value.trim();
            const password = document.getElementById('loginPassword').value;

            try {
                const response = await fetch(`${API_BASE_URL}/api/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();
                if (response.ok) {
                    currentUser = data.user;
                    showAlert('Login successful! Welcome back.', 'success');
                    setTimeout(() => {
                        closeAuthModal();
                        updateUIForLoggedInUser();
                    }, 1000);
                } else {
                    showAlert(data.error || 'Login failed');
                }
            } catch (error) {
                console.error('Login error:', error);
                showAlert('Network error. Please check your connection.');
            }
        });
    }

    // Register Form Handler
    const registerForm = document.getElementById('registerFormElement');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('registerUsername').value.trim();
            const email = document.getElementById('registerEmail').value.trim();
            const password = document.getElementById('registerPassword').value;

            try {
                const response = await fetch(`${API_BASE_URL}/api/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ username, email, password })
                });

                const data = await response.json();
                if (response.ok) {
                    currentUser = data.user;
                    showAlert('Account created successfully! Welcome aboard.', 'success');
                    setTimeout(() => {
                        closeAuthModal();
                        updateUIForLoggedInUser();
                    }, 1000);
                } else {
                    showAlert(data.error || 'Registration failed');
                }
            } catch (error) {
                console.error('Registration error:', error);
                showAlert('Network error. Please try again.');
            }
        });
    }
});

// ==================== BACKEND CONNECTION CHECK ====================

async function checkBackendConnection() {
    const statusEl = document.getElementById('connectionStatus');

    try {
        const response = await fetch(`${API_BASE_URL}/api/check_session`, {
            credentials: 'include',
            timeout: 5000
        });

        if (response.ok) {
            backendAvailable = true;
            if (statusEl) statusEl.classList.add('hidden');
            const data = await response.json();
            if (data.logged_in) {
                currentUser = data.user;
                updateUIForLoggedInUser();
            }
        } else {
            showConnectionError('Backend Error');
        }
    } catch (error) {
        console.error('Backend connection error:', error);
        showConnectionError('Backend Offline');
    }
}

function showConnectionError(message) {
    backendAvailable = false;
    const statusEl = document.getElementById('connectionStatus');
    const statusText = document.getElementById('connectionText');
    if (statusEl && statusText) {
        statusEl.classList.remove('hidden');
        statusEl.className = 'connection-status bg-red-600/20 border border-red-500';
        statusText.innerHTML = `<i class="fas fa-exclamation-circle mr-2"></i>${message}`;
    }
}

// ==================== AUTHENTICATION FUNCTIONS ====================

function showAlert(message, type = 'error') {
    const container = document.getElementById('alertContainer');
    if (!container) return;

    const icon = type === 'error' ? 'exclamation-circle' : 'check-circle';
    container.innerHTML = `
        <div class="alert alert-${type}">
            <i class="fas fa-${icon} mr-2"></i>${message}
        </div>`;
    setTimeout(() => container.innerHTML = '', 5000);
}

function openAuthModal() {
    if (!backendAvailable) {
        alert('⚠️ Backend server is not running!\n\nPlease start the Flask server:\n\n$ python main.py');
        return;
    }
    document.getElementById('authModal').classList.add('active');
}

function closeAuthModal() {
    document.getElementById('authModal').classList.remove('active');
    const alertContainer = document.getElementById('alertContainer');
    if (alertContainer) alertContainer.innerHTML = '';
}

function showLoginForm() {
    document.getElementById('loginForm').classList.remove('hidden');
    document.getElementById('registerForm').classList.add('hidden');
    const alertContainer = document.getElementById('alertContainer');
    if (alertContainer) alertContainer.innerHTML = '';
}

function showRegisterForm() {
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerForm').classList.remove('hidden');
    const alertContainer = document.getElementById('alertContainer');
    if (alertContainer) alertContainer.innerHTML = '';
}

function updateUIForLoggedInUser() {
    const loginBtn = document.getElementById('loginButton');
    const userSection = document.getElementById('userSection');
    const usernameDisplay = document.getElementById('usernameDisplay');
    const workoutLink = document.getElementById('workoutNavLink');
    const reportsLink = document.getElementById('reportsNavLink');

    if (loginBtn) loginBtn.classList.add('hidden');
    if (userSection) userSection.classList.remove('hidden');
    if (usernameDisplay && currentUser) usernameDisplay.textContent = currentUser.username;
    if (workoutLink) workoutLink.classList.remove('hidden');
    if (reportsLink) reportsLink.classList.remove('hidden');
}

function updateUIForLoggedOutUser() {
    const loginBtn = document.getElementById('loginButton');
    const userSection = document.getElementById('userSection');
    const workoutLink = document.getElementById('workoutNavLink');
    const reportsLink = document.getElementById('reportsNavLink');

    if (loginBtn) loginBtn.classList.remove('hidden');
    if (userSection) userSection.classList.add('hidden');
    if (workoutLink) workoutLink.classList.add('hidden');
    if (reportsLink) reportsLink.classList.add('hidden');
    currentUser = null;
}

async function logout() {
    try {
        await fetch(`${API_BASE_URL}/api/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        updateUIForLoggedOutUser();
        showPage('home-page', document.querySelector('.nav-link[onclick*="home-page"]'));
    } catch (error) {
        console.error('Logout failed:', error);
    }
}

// ==================== PAGE NAVIGATION ====================

function showPage(pageId, element) {
    if ((pageId === 'workout-page' || pageId === 'reports-page') && !currentUser) {
        openAuthModal();
        return;
    }

    document.querySelectorAll('main.page-section').forEach(page => {
        page.classList.remove('active');
    });

    const pageElement = document.getElementById(pageId);
    if (pageElement) {
        pageElement.classList.add('active');
    }

    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });

    if (element && element.classList.contains('nav-link')) {
        element.classList.add('active');
    }

    if (pageId === 'reports-page') {
        loadReportsData();
    }

    if (pageId === 'workout-page' && !window.aiTrainerInstance) {
        setTimeout(() => {
            window.aiTrainerInstance = new EnhancedAIFitnessTrainer();
            console.log('AI Trainer instance created');
        }, 100);
    }
}

function startWorkout() {
    if (!backendAvailable) {
        alert('⚠️ Backend server is not running!\n\nPlease start the Flask server first:\n\n$ python main.py');
        return;
    }
    if (!currentUser) {
        openAuthModal();
        return;
    }
    showPage('workout-page', document.querySelector('.nav-link[onclick*="workout-page"]'));
}

// ==================== REPORTS PAGE FUNCTIONS ====================

let exerciseChart = null;
let progressChart = null;

async function loadReportsData() {
    if (!backendAvailable) {
        alert('⚠️ Backend server is not running. Cannot load reports.');
        return;
    }
    try {
        // Load summary
        const summaryResponse = await fetch(`${API_BASE_URL}/api/reports/summary?days=30`, {
            credentials: 'include'
        });
        const summary = await summaryResponse.json();

        document.getElementById('totalWorkouts').textContent = summary.total_workouts;
        document.getElementById('totalReps').textContent = summary.total_reps;
        document.getElementById('avgForm').textContent = `${summary.avg_form_score}%`;
        document.getElementById('totalCalories').textContent = summary.total_calories;

        // Load exercise breakdown
        const breakdownResponse = await fetch(`${API_BASE_URL}/api/reports/exercise_breakdown?days=30`, {
            credentials: 'include'
        });
        const breakdown = await breakdownResponse.json();
        renderExerciseChart(breakdown);

        // Load timeline
        const timelineResponse = await fetch(`${API_BASE_URL}/api/reports/progress_timeline?days=30`, {
            credentials: 'include'
        });
        const timeline = await timelineResponse.json();
        renderProgressChart(timeline);

    } catch (error) {
        console.error('Error loading reports:', error);
    }
}

function renderExerciseChart(data) {
    const ctx = document.getElementById('exerciseChart').getContext('2d');

    if (exerciseChart) {
        exerciseChart.destroy();
    }

    exerciseChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.exercise_name),
            datasets: [{
                data: data.map(item => item.total_reps),
                backgroundColor: [
                    '#38e1a1', '#1abc9c', '#3498db', '#9b59b6', '#f1c40f', '#e74c3c'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#ecf0f1' }
                }
            }
        }
    });
}

function renderProgressChart(data) {
    const ctx = document.getElementById('progressChart').getContext('2d');

    if (progressChart) {
        progressChart.destroy();
    }

    progressChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(item => item.date),
            datasets: [{
                label: 'Total Reps',
                data: data.map(item => item.total_reps),
                borderColor: '#38e1a1',
                tension: 0.4,
                yAxisID: 'y'
            }, {
                label: 'Avg Form Score',
                data: data.map(item => item.avg_form_score),
                borderColor: '#f1c40f',
                tension: 0.4,
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { labels: { color: '#ecf0f1' } }
            },
            scales: {
                x: {
                    ticks: { color: '#bdc3c7' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    ticks: { color: '#38e1a1' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    ticks: { color: '#f1c40f' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

async function generateAIReport() {
    if (!backendAvailable) {
        alert('⚠️ Backend server is not running. Cannot generate AI report.');
        return;
    }
    const prompt = document.getElementById('aiPrompt').value || 'Provide a comprehensive analysis of my workout history.';
    const container = document.getElementById('aiReportContainer');
    const textElement = document.getElementById('aiReportText');

    container.classList.remove('hidden');
    textElement.innerHTML = `
        <div class="text-center py-8">
            <div class="loading-spinner mx-auto mb-4"></div>
            <p class="text-green-400">Analyzing your workout data...</p>
        </div>`;

    try {
        const response = await fetch(`${API_BASE_URL}/api/generate_report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ prompt })
        });

        const data = await response.json();

        if (response.ok) {
            // Convert markdown-style bold to HTML bold
            let formattedReport = data.report
                .replace(/\*\*(.*?)\*\*/g, '<strong class="text-green-300">$1</strong>')
                .replace(/\n/g, '<br>');

            textElement.innerHTML = formattedReport;
        } else {
            textElement.innerHTML = `
                <div class="text-red-400">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    Error: ${data.error || 'Unknown error'}
                </div>`;
        }
    } catch (error) {
        console.error('AI Report generation error:', error);
        textElement.innerHTML = `
            <div class="text-red-400">
                <i class="fas fa-exclamation-circle mr-2"></i>
                Failed to generate report due to network error. Please try again.
            </div>`;
    }
}
