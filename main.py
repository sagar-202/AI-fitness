# The Flask backend now includes user authentication, session management,
# and enhanced workout tracking with user-specific data.

from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import mediapipe as mp
import numpy as np
import json
import sqlite3
from datetime import datetime, date, timedelta
from collections import deque
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import requests
import time
from functools import wraps

app = Flask(__name__)

# CORS configuration - Allow credentials for session management
CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])

# Secret key for session management - CHANGE THIS IN PRODUCTION!
app.secret_key = 'your-secret-key-change-this-in-production'

# Session configuration
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS

# Gemini API configuration
API_KEY = ""
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

# Initialize MediaPipe
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

class AdvancedExerciseAnalyzer:
    """
    Advanced exercise analyzer with machine learning capabilities
    and enhanced pose analysis features
    """
    
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose_buffer = deque(maxlen=30)
        self.reference_poses = self.load_reference_poses()
        self.scaler = StandardScaler()
        self.exercise_models = {}
        
        # Exercise-specific parameters
        self.exercise_configs = {
            'squats': {
                'key_joints': [23, 24, 25, 26, 27, 28],
                'angle_joints': [(23, 25, 27), (24, 26, 28)],
                'movement_threshold': 0.02,
                'min_angle': 60,
                'max_angle': 170
            },
            'pushups': {
                'key_joints': [11, 12, 13, 14, 15, 16],
                'angle_joints': [(11, 13, 15), (12, 14, 16)],
                'movement_threshold': 0.015,
                'min_angle': 70,
                'max_angle': 160
            },
            'lunges': {
                'key_joints': [23, 24, 25, 26, 27, 28],
                'angle_joints': [(23, 25, 27), (24, 26, 28)],
                'movement_threshold': 0.025,
                'min_angle': 70,
                'max_angle': 160
            },
            'bicep_curls': {
                'key_joints': [11, 12, 13, 14, 15, 16],
                'angle_joints': [(11, 13, 15), (12, 14, 16)],
                'movement_threshold': 0.01,
                'min_angle': 30,
                'max_angle': 140
            }
        }
        
        # State tracking
        self.exercise_state = 'neutral'
        self.rep_count = 0
        self.current_exercise = None
        self.form_scores = []
        self.current_rep_scores = []
        self.movement_quality_scores = []
        self.session_start_time = None
        
    def load_reference_poses(self):
        """Load reference poses for each exercise"""
        return {
            'squats': {
                'start_pose': None,
                'bottom_pose': None,
                'end_pose': None
            },
            'pushups': {
                'start_pose': None,
                'bottom_pose': None,
                'end_pose': None
            }
        }
    
    def extract_pose_features(self, landmarks):
        """Extract comprehensive features from pose landmarks"""
        if not landmarks:
            return None
            
        features = []
        
        for landmark in landmarks:
            features.extend([landmark.x, landmark.y, landmark.z])
        
        angles = self.calculate_all_joint_angles(landmarks)
        features.extend(angles)
        
        distances = self.calculate_key_distances(landmarks)
        features.extend(distances)
        
        ratios = self.calculate_body_ratios(landmarks)
        features.extend(ratios)
        
        return np.array(features)
    
    def calculate_all_joint_angles(self, landmarks):
        """Calculate angles for all major joints"""
        angles = []
        
        joint_triplets = [
            (11, 13, 15), (12, 14, 16),
            (13, 15, 19), (14, 16, 20),
            (23, 25, 27), (24, 26, 28),
            (25, 27, 31), (26, 28, 32),
            (11, 23, 25), (12, 24, 26),
        ]
        
        for triplet in joint_triplets:
            try:
                angle = self.calculate_angle(
                    landmarks[triplet[0]],  
                    landmarks[triplet[1]],  
                    landmarks[triplet[2]]
                )
                angles.append(angle)
            except:
                angles.append(0)
                
        return angles
    
    def calculate_key_distances(self, landmarks):
        """Calculate distances between key body points"""
        distances = []
        
        distance_pairs = [
            (11, 12), (23, 24), (27, 28),
            (11, 23), (12, 24),
            (23, 27), (24, 28),
        ]
        
        for pair in distance_pairs:
            try:
                dist = self.calculate_distance(landmarks[pair[0]], landmarks[pair[1]])
                distances.append(dist)
            except:
                distances.append(0)
                
        return distances
    
    def calculate_body_ratios(self, landmarks):
        """Calculate body proportion ratios"""
        ratios = []
        
        try:
            torso_height = abs(landmarks[11].y - landmarks[23].y)
            leg_length = abs(landmarks[23].y - landmarks[27].y)
            if leg_length > 0:
                ratios.append(torso_height / leg_length)
            else:
                ratios.append(0)
                
            arm_span = abs(landmarks[15].x - landmarks[16].x)
            body_height = abs(landmarks[0].y - landmarks[27].y)
            if body_height > 0:
                ratios.append(arm_span / body_height)
            else:
                ratios.append(0)
                
        except:
            ratios.extend([0, 0])
            
        return ratios
    
    def calculate_angle(self, a, b, c):
        """Calculate angle between three points using vectors"""
        if not all([a, b, c]):
            return 0
            
        a_pos = np.array([a.x, a.y])
        b_pos = np.array([b.x, b.y])  
        c_pos = np.array([c.x, c.y])
        
        ba = a_pos - b_pos
        bc = c_pos - b_pos
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        angle = np.arccos(cosine_angle)
        
        return np.degrees(angle)
    
    def calculate_distance(self, point1, point2):
        """Calculate Euclidean distance between two points"""
        return np.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)
    
    def analyze_movement_quality(self, landmarks):
        """Analyze movement quality using temporal analysis"""
        current_features = self.extract_pose_features(landmarks)
        if current_features is None:
            return {'quality_score': 0, 'smoothness': 0, 'stability': 0}
            
        self.pose_buffer.append(current_features)
        
        if len(self.pose_buffer) < 10:
            return {'quality_score': 50, 'smoothness': 50, 'stability': 50}
        
        smoothness = self.calculate_movement_smoothness()
        stability = self.calculate_pose_stability()
        quality_score = (smoothness * 0.4 + stability * 0.6)
        
        return {
            'quality_score': quality_score,
            'smoothness': smoothness,
            'stability': stability
        }
    
    def calculate_movement_smoothness(self):
        """Calculate how smooth the movement is over time"""
        if len(self.pose_buffer) < 5:
            return 50
            
        differences = []
        poses = list(self.pose_buffer)
        
        for i in range(1, len(poses)):
            diff = np.linalg.norm(poses[i] - poses[i-1])
            differences.append(diff)
        
        avg_diff = np.mean(differences)
        std_diff = np.std(differences)
        
        if std_diff == 0:
            smoothness = 100
        else:
            smoothness = max(0, 100 - (std_diff * 1000))
            
        return min(100, smoothness)
    
    def calculate_pose_stability(self, ):
        """Calculate pose stability (reduced jitter/noise)"""
        if len(self.pose_buffer) < 10:
            return 50
            
        poses = np.array(list(self.pose_buffer))
        pose_variance = np.var(poses, axis=0)
        avg_variance = np.mean(pose_variance)
        stability = max(0, 100 - (avg_variance * 10000))
        
        return min(100, stability)
    
    def detect_exercise_phase(self, landmarks, exercise_type):
        """Detect current phase of exercise"""
        config = self.exercise_configs.get(exercise_type, {})
        angle_joints = config.get('angle_joints', [])
        
        if not angle_joints:
            return 'unknown'
            
        avg_angle = 0
        if self.pose_buffer and len(self.pose_buffer) >= 5:
            recent_poses = list(self.pose_buffer)[-5:]
            recent_angles = []
            for pose_features in recent_poses:
                landmark_coords = pose_features[:99]
                
                def get_landmark(idx):
                    lm = type('Landmark', (), {})()
                    lm.x = landmark_coords[idx * 3]
                    lm.y = landmark_coords[idx * 3 + 1]
                    lm.z = landmark_coords[idx * 3 + 2]
                    return lm

                angles_in_frame = []
                for triplet in angle_joints:
                    try:
                        angle = self.calculate_angle(
                            get_landmark(triplet[0]),
                            get_landmark(triplet[1]),
                            get_landmark(triplet[2])
                        )
                        angles_in_frame.append(angle)
                    except:
                        continue
                
                if angles_in_frame:
                    avg_angle = np.mean(angles_in_frame)

        min_angle = config.get('min_angle', 60)
        max_angle = config.get('max_angle', 160)
        
        if avg_angle <= min_angle + 10:
            return 'bottom'
        elif avg_angle >= max_angle - 10:
            return 'top'
        else:
            return 'transition'

    def generate_detailed_feedback(self, landmarks, exercise_type):
        """Generate detailed feedback for exercise form"""
        feedback = []
        form_score = 100
        
        config = self.exercise_configs.get(exercise_type, {})
        
        if exercise_type == 'squats':
            feedback, form_score = self._analyze_squat_form(landmarks, config)
        elif exercise_type == 'pushups':
            feedback, form_score = self._analyze_pushup_form(landmarks, config)
        elif exercise_type == 'lunges':
            feedback, form_score = self._analyze_lunge_form(landmarks, config)
        elif exercise_type == 'bicep_curls':
            feedback, form_score = self._analyze_bicep_curl_form(landmarks, config)
        
        movement_analysis = self.analyze_movement_quality(landmarks)
        
        if movement_analysis['smoothness'] < 60:
            feedback.append("Try to move more smoothly")
            form_score -= 10
            
        if movement_analysis['stability'] < 50:
            feedback.append("Reduce body sway and maintain stability")
            form_score -= 15
        
        self.current_rep_scores.append(form_score)
        self.form_scores.append(form_score)
        
        return {
            'feedback': feedback,
            'form_score': max(0, form_score),
            'movement_quality': movement_analysis,
            'exercise_phase': self.detect_exercise_phase(landmarks, exercise_type)
        }
    
    def _analyze_squat_form(self, landmarks, config):
        """Detailed squat form analysis"""
        feedback = []
        form_score = 100
        
        try:
            left_hip = landmarks[23]
            right_hip = landmarks[24]  
            left_knee = landmarks[25]
            right_knee = landmarks[26]
            left_ankle = landmarks[27]
            right_ankle = landmarks[28]
            
            left_knee_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
            right_knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
            
            angle_diff = abs(left_knee_angle - right_knee_angle)
            if angle_diff > 15:
                feedback.append(f"Uneven squat - left: {left_knee_angle:.0f}°, right: {right_knee_angle:.0f}°")
                form_score -= 20
            
            avg_angle = (left_knee_angle + right_knee_angle) / 2
            if avg_angle < 60:
                feedback.append("Excellent squat depth!")
                form_score += 5
            elif avg_angle < 90:
                feedback.append("Good squat depth")
            elif avg_angle < 120:
                feedback.append("Try to go deeper")
                form_score -= 10
            else:
                feedback.append("Squat deeper for better results")
                form_score -= 20
            
            knee_distance = abs(left_knee.x - right_knee.x)
            hip_distance = abs(left_hip.x - right_hip.x)
            
            if knee_distance < hip_distance * 0.8:
                feedback.append("Keep knees aligned with hips - don't let them cave inward")
                form_score -= 15
            
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            shoulder_hip_angle = self.calculate_angle(left_shoulder, left_hip, left_knee)
            
            if shoulder_hip_angle < 160:
                feedback.append("Keep your back straight")
                form_score -= 15
                
        except Exception as e:
            feedback.append("Unable to analyze pose completely")
            form_score = 50
            
        return feedback, form_score
    
    def _analyze_pushup_form(self, landmarks, config):
        """Detailed push-up form analysis"""
        feedback = []
        form_score = 100
        
        try:
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            left_elbow = landmarks[13]
            right_elbow = landmarks[14]
            left_wrist = landmarks[15]
            right_wrist = landmarks[16]
            left_hip = landmarks[23]
            right_hip = landmarks[24]
            
            left_elbow_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
            right_elbow_angle = self.calculate_angle(right_shoulder, right_elbow, right_wrist)
            
            angle_diff = abs(left_elbow_angle - right_elbow_angle)
            if angle_diff > 20:
                feedback.append("Keep both arms moving together")
                form_score -= 20
            
            avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
            if avg_elbow_angle < 70:
                feedback.append("Excellent push-up depth!")
                form_score += 5
            elif avg_elbow_angle < 90:
                feedback.append("Good push-up form")
            else:
                feedback.append("Lower your chest closer to the ground")
                form_score -= 15
            
            shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
            hip_y = (left_hip.y + right_hip.y) / 2
            
            body_alignment = abs(shoulder_y - hip_y)
            if body_alignment > 0.1:
                feedback.append("Keep your body in a straight line")
                form_score -= 20
                
        except Exception as e:
            feedback.append("Unable to analyze pose completely")
            form_score = 50
            
        return feedback, form_score
    
    def _analyze_lunge_form(self, landmarks, config):
        """Detailed lunge form analysis"""
        feedback = []
        form_score = 100
        
        try:
            left_hip = landmarks[23]
            right_hip = landmarks[24]
            left_knee = landmarks[25]
            right_knee = landmarks[26]
            left_ankle = landmarks[27]
            right_ankle = landmarks[28]
            
            if left_knee.y > right_knee.y:
                front_hip, front_knee, front_ankle = left_hip, left_knee, left_ankle
                back_hip, back_knee, back_ankle = right_hip, right_knee, right_ankle
            else:
                front_hip, front_knee, front_ankle = right_hip, right_knee, right_ankle
                back_hip, back_knee, back_ankle = left_hip, left_knee, left_ankle
            
            front_knee_angle = self.calculate_angle(front_hip, front_knee, front_ankle)
            
            if front_knee_angle < 90:
                feedback.append("Perfect lunge depth!")
                form_score += 5
            elif front_knee_angle < 110:
                feedback.append("Good lunge form")
            else:
                feedback.append("Step deeper into the lunge")
                form_score -= 15
            
            if abs(front_knee.x - front_ankle.x) > 0.05:
                feedback.append("Ensure your knee is aligned over your ankle")
                form_score -= 20
                
        except Exception as e:
            feedback.append("Unable to analyze pose completely")
            form_score = 50
            
        return feedback, form_score
    
    def _analyze_bicep_curl_form(self, landmarks, config):
        """Detailed bicep curl form analysis"""
        feedback = []
        form_score = 100
        
        try:
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            left_elbow = landmarks[13]
            right_elbow = landmarks[14]
            left_wrist = landmarks[15]
            right_wrist = landmarks[16]
            
            left_elbow_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
            right_elbow_angle = self.calculate_angle(right_shoulder, right_elbow, right_wrist)
            
            angle_diff = abs(left_elbow_angle - right_elbow_angle)
            if angle_diff > 15:
                feedback.append("Curl both arms evenly")
                form_score -= 15
            
            avg_angle = (left_elbow_angle + right_elbow_angle) / 2
            if avg_angle < 45:
                feedback.append("Full contraction achieved!")
                form_score += 5
            elif avg_angle < 90:
                feedback.append("Good curl range")
            else:
                feedback.append("Curl up more for full contraction")
                form_score -= 10
            
            left_elbow_movement = abs(left_elbow.x - left_shoulder.x)
            right_elbow_movement = abs(right_elbow.x - right_shoulder.x)
            
            if left_elbow_movement > 0.1 or right_elbow_movement > 0.1:
                feedback.append("Keep your elbows stable at your sides")
                form_score -= 20
                
        except Exception as e:
            feedback.append("Unable to analyze pose completely")
            form_score = 50
            
        return feedback, form_score
    
    def process_repetition_counting(self, landmarks, exercise_type):
        """Advanced repetition counting with state machine"""
        config = self.exercise_configs.get(exercise_type, {})
        angle_joints = config.get('angle_joints', [])
        
        if not angle_joints:
            return False
        
        avg_angle = 0
        if self.pose_buffer and len(self.pose_buffer) >= 5:
            recent_poses = list(self.pose_buffer)[-5:]
            recent_angles = []
            for pose_features in recent_poses:
                landmark_coords = pose_features[:99]
                
                def get_landmark(idx):
                    lm = type('Landmark', (), {})()
                    lm.x = landmark_coords[idx * 3]
                    lm.y = landmark_coords[idx * 3 + 1]
                    lm.z = landmark_coords[idx * 3 + 2]
                    return lm

                angles_in_frame = []
                for triplet in angle_joints:
                    try:
                        angle = self.calculate_angle(
                            get_landmark(triplet[0]),
                            get_landmark(triplet[1]),
                            get_landmark(triplet[2])
                        )
                        angles_in_frame.append(angle)
                    except:
                        continue
                
                if angles_in_frame:
                    avg_angle = np.mean(angles_in_frame)

        min_angle = config.get('min_angle', 60)
        max_angle = config.get('max_angle', 160)
        
        rep_completed = False
        
        if self.exercise_state == 'neutral':
            if avg_angle < min_angle + 20:
                self.exercise_state = 'down_phase'
            
        elif self.exercise_state == 'down_phase':
            if avg_angle > max_angle - 15:
                self.exercise_state = 'up_phase'
                
        elif self.exercise_state == 'up_phase':
            if avg_angle < min_angle + 15:
                if self.current_rep_scores and np.mean(self.current_rep_scores) > 70:
                    self.rep_count += 1
                    rep_completed = True
                
                self.exercise_state = 'neutral'
                self.current_rep_scores = []
        
        return rep_completed
    
    def reset_session(self):
        """Reset all session data"""
        self.exercise_state = 'neutral'
        self.rep_count = 0
        self.form_scores = []
        self.current_rep_scores = []
        self.movement_quality_scores = []
        self.pose_buffer.clear()
        self.session_start_time = datetime.now()
    
    def get_session_duration(self):
        """Get session duration in seconds"""
        if self.session_start_time:
            return int((datetime.now() - self.session_start_time).total_seconds())
        return 0

# Global analyzer instance
analyzer = AdvancedExerciseAnalyzer()

DATABASE = 'fitness_trainer.db'

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the provided schema"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        schema = """
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Exercises table
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL,
            description TEXT,
            muscle_groups TEXT,
            difficulty_level INTEGER DEFAULT 1,
            instructions TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Workout sessions table (updated to use exercise name directly)
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            exercise_name TEXT NOT NULL,
            total_reps INTEGER DEFAULT 0,
            avg_form_score FLOAT DEFAULT 0,
            duration_seconds INTEGER DEFAULT 0,
            calories_burned FLOAT DEFAULT 0,
            session_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Rep details table
        CREATE TABLE IF NOT EXISTS rep_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            rep_number INTEGER,
            form_score FLOAT,
            angle_data TEXT,
            feedback TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES workout_sessions(id)
        );

        -- User preferences table
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            preferred_exercises TEXT,
            difficulty_preference INTEGER DEFAULT 1,
            workout_reminders BOOLEAN DEFAULT FALSE,
            form_strictness INTEGER DEFAULT 2,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Exercise progress tracking
        CREATE TABLE IF NOT EXISTS progress_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            exercise_id INTEGER,
            week_start_date DATE,
            total_reps INTEGER DEFAULT 0,
            avg_form_score FLOAT DEFAULT 0,
            total_sessions INTEGER DEFAULT 0,
            best_single_session_reps INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id),
            UNIQUE(user_id, exercise_id, week_start_date)
        );

        -- Insert default exercises
        INSERT OR IGNORE INTO exercises (name, description, muscle_groups, difficulty_level, instructions) VALUES
        ('Squats', 'Lower body compound exercise targeting legs and glutes', '["quadriceps", "glutes", "hamstrings", "calves"]', 1, 'Stand with feet shoulder-width apart. Lower your body by bending knees until thighs are parallel to ground.'),
        ('Push-ups', 'Upper body compound exercise for chest, shoulders, and triceps', '["chest", "shoulders", "triceps", "core"]', 2, 'Start in plank position. Lower body until chest nearly touches ground.'),
        ('Lunges', 'Single-leg exercise for lower body strength and balance', '["quadriceps", "glutes", "hamstrings", "calves"]', 2, 'Step forward with one leg, lowering hips until both knees are bent at 90 degrees.'),
        ('Bicep Curls', 'Isolated arm exercise targeting biceps', '["biceps"]', 1, 'Hold weights at your sides. Curl weights up by flexing biceps.');

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_date ON workout_sessions(user_id, session_date);
        CREATE INDEX IF NOT EXISTS idx_rep_details_session ON rep_details(session_id);
        CREATE INDEX IF NOT EXISTS idx_progress_tracking_user_exercise ON progress_tracking(user_id, exercise_id);
        """
        cursor.executescript(schema)
        conn.commit()

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Initialize database
with app.app_context():
    init_db()

@app.route('/')
def index():
    # Check if templates folder exists
    import os
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    if os.path.exists(template_path):
        return render_template('index.html')
    else:
        # Fallback: serve from current directory
        html_path = os.path.join(os.path.dirname(__file__), 'index.html')
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return """
            <h1>Setup Required</h1>
            <p>Please create a 'templates' folder and move 'index.html' into it.</p>
            <p>Or place 'index.html' in the same directory as 'app.py'.</p>
            <p>Current directory: {}</p>
            """.format(os.path.dirname(__file__)), 404

@app.route('/favicon.ico')
def favicon():
    """Return empty response for favicon to prevent 404 errors"""
    return '', 204

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            conn.commit()
            user_id = cursor.lastrowid
            
            # Create session
            session['user_id'] = user_id
            session['username'] = username
            
            conn.close()
            
            return jsonify({
                'message': 'Registration successful',
                'user': {'id': user_id, 'username': username, 'email': email}
            }), 201
            
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Username or email already exists'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if login is by email or username
        cursor.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, username)
        )
        user = cursor.fetchone()
        conn.close()
        
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Create session
        session['user_id'] = user['id']
        session['username'] = user['username']
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/check_session', methods=['GET'])
def check_session():
    """Check if user is logged in"""
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user': {
                'id': session['user_id'],
                'username': session['username']
            }
        }), 200
    return jsonify({'logged_in': False}), 200

# ==================== POSE ANALYSIS ROUTES ====================

@app.route('/api/analyze_pose', methods=['POST'])
@login_required
def analyze_pose():
    """Analyze pose data from frontend using the advanced analyzer"""
    try:
        data = request.get_json()
        exercise = data.get('exercise', 'squats')
        landmarks_data = data.get('landmarks', [])
        
        if not landmarks_data:
            return jsonify({'error': 'No landmarks provided'}), 400
        
        # Convert landmarks data
        landmarks = []
        for landmark_data in landmarks_data:
            landmark = type('Landmark', (), {})()
            landmark.x = landmark_data['x']
            landmark.y = landmark_data['y']
            landmark.z = landmark_data.get('z', 0)
            landmark.visibility = landmark_data.get('visibility', 1)
            landmarks.append(landmark)

        analyzer.current_exercise = exercise
        
        # Start session timer if not started
        if analyzer.session_start_time is None:
            analyzer.session_start_time = datetime.now()
        
        analysis_result = analyzer.generate_detailed_feedback(landmarks, exercise)
        rep_completed = analyzer.process_repetition_counting(landmarks, exercise)

        response = {
            'reps': analyzer.rep_count,
            'feedback': analysis_result['feedback'],
            'form_score': analysis_result['form_score'],
            'movement_quality': analysis_result['movement_quality'],
            'exercise_phase': analysis_result['exercise_phase'],
            'rep_completed': rep_completed
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset_session', methods=['POST'])
@login_required
def reset_session():
    """Reset current exercise session"""
    analyzer.reset_session()
    return jsonify({'message': 'Session reset successfully'})

@app.route('/api/save_workout', methods=['POST'])
@login_required
def save_workout():
    """Save workout session to database"""
    try:
        data = request.get_json()
        exercise_name = data.get('exercise', 'Unknown')
        total_reps = data.get('reps', 0)
        
        if total_reps == 0:
            return jsonify({'message': 'No reps to save'}), 200
        
        duration = analyzer.get_session_duration()
        avg_form_score = np.mean(analyzer.form_scores) if analyzer.form_scores else 0
        
        # Estimate calories burned (rough calculation)
        calories_per_rep = {'squats': 0.32, 'pushups': 0.29, 'lunges': 0.35, 'bicep_curls': 0.20}
        calories = total_reps * calories_per_rep.get(exercise_name, 0.25)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        user_id = session['user_id']
        
        cursor.execute("""
            INSERT INTO workout_sessions 
            (user_id, exercise_name, total_reps, avg_form_score, duration_seconds, calories_burned)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, exercise_name, total_reps, avg_form_score, duration, calories))
        
        conn.commit()
        conn.close()
        
        analyzer.reset_session()
        return jsonify({'message': 'Workout saved successfully'}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/workout_history', methods=['GET'])
@login_required
def get_workout_history():
    """Get workout history for logged-in user"""
    try:
        user_id = session['user_id']
        limit = request.args.get('limit', 20, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                session_date,
                exercise_name,
                total_reps,
                avg_form_score,
                duration_seconds,
                calories_burned
            FROM workout_sessions
            WHERE user_id = ?
            ORDER BY session_date DESC
            LIMIT ?
        """, (user_id, limit))
        
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== REPORTS & ANALYTICS ROUTES ====================

@app.route('/api/reports/summary', methods=['GET'])
@login_required
def get_reports_summary():
    """Get summary statistics for reports page"""
    try:
        user_id = session['user_id']
        days = request.args.get('days', 30, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate date range
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Total workouts
        cursor.execute("""
            SELECT COUNT(*) as total_workouts
            FROM workout_sessions
            WHERE user_id = ? AND session_date >= ?
        """, (user_id, start_date))
        total_workouts = cursor.fetchone()['total_workouts']
        
        # Total reps
        cursor.execute("""
            SELECT SUM(total_reps) as total_reps
            FROM workout_sessions
            WHERE user_id = ? AND session_date >= ?
        """, (user_id, start_date))
        total_reps = cursor.fetchone()['total_reps'] or 0
        
        # Average form score
        cursor.execute("""
            SELECT AVG(avg_form_score) as avg_form
            FROM workout_sessions
            WHERE user_id = ? AND session_date >= ?
        """, (user_id, start_date))
        avg_form = cursor.fetchone()['avg_form'] or 0
        
        # Total calories
        cursor.execute("""
            SELECT SUM(calories_burned) as total_calories
            FROM workout_sessions
            WHERE user_id = ? AND session_date >= ?
        """, (user_id, start_date))
        total_calories = cursor.fetchone()['total_calories'] or 0
        
        # Total time
        cursor.execute("""
            SELECT SUM(duration_seconds) as total_time
            FROM workout_sessions
            WHERE user_id = ? AND session_date >= ?
        """, (user_id, start_date))
        total_time = cursor.fetchone()['total_time'] or 0
        
        conn.close()
        
        return jsonify({
            'total_workouts': total_workouts,
            'total_reps': int(total_reps),
            'avg_form_score': round(avg_form, 1),
            'total_calories': round(total_calories, 1),
            'total_time_minutes': round(total_time / 60, 1)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/exercise_breakdown', methods=['GET'])
@login_required
def get_exercise_breakdown():
    """Get exercise breakdown for charts"""
    try:
        user_id = session['user_id']
        days = request.args.get('days', 30, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT 
                exercise_name,
                SUM(total_reps) as total_reps,
                COUNT(*) as session_count,
                AVG(avg_form_score) as avg_form
            FROM workout_sessions
            WHERE user_id = ? AND session_date >= ?
            GROUP BY exercise_name
            ORDER BY total_reps DESC
        """, (user_id, start_date))
        
        breakdown = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(breakdown)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/progress_timeline', methods=['GET'])
@login_required
def get_progress_timeline():
    """Get progress over time for line charts"""
    try:
        user_id = session['user_id']
        days = request.args.get('days', 30, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT 
                DATE(session_date) as date,
                SUM(total_reps) as daily_reps,
                AVG(avg_form_score) as daily_form,
                COUNT(*) as daily_sessions
            FROM workout_sessions
            WHERE user_id = ? AND session_date >= ?
            GROUP BY DATE(session_date)
            ORDER BY date ASC
        """, (user_id, start_date))
        
        timeline = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(timeline)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate_report', methods=['POST'])
@login_required
def generate_report():
    """Generate AI-powered workout report using Gemini"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'Provide a comprehensive analysis of my workout history.')
        
        user_id = session['user_id']
        
        # Fetch user's workout history
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                session_date,
                exercise_name,
                total_reps,
                avg_form_score,
                duration_seconds,
                calories_burned
            FROM workout_sessions
            WHERE user_id = ?
            ORDER BY session_date DESC
            LIMIT 20
        """, (user_id,))
        
        workout_history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Format history
        history_str = "Recent Workout History:\n"
        for entry in workout_history:
            date = datetime.fromisoformat(entry['session_date']).strftime('%Y-%m-%d')
            history_str += (
                f"- {date}: {entry['exercise_name'].replace('_', ' ').title()} - "
                f"{entry['total_reps']} reps, Form: {entry['avg_form_score']:.1f}%, "
                f"Duration: {entry['duration_seconds']}s, Calories: {entry['calories_burned']:.1f}\n"
            )
        
        full_prompt = (
            f"You are an expert AI fitness coach. Based on the user's workout history, "
            f"provide detailed analysis and personalized recommendations. User's question: '{prompt}'\n\n"
            f"{history_str}\n\n"
            f"Provide a friendly, motivating response with clear sections: "
            f"Performance Summary, Form Analysis, and Personalized Recommendations."
        )

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.7}
        }
        
        retries = 0
        while retries < 5:
            try:
                response = requests.post(f"{GEMINI_API_URL}?key={API_KEY}", json=payload)
                response.raise_for_status()
                response_data = response.json()
                report_text = response_data['candidates'][0]['content']['parts'][0]['text']
                return jsonify({'report': report_text})
            except requests.exceptions.RequestException as e:
                time.sleep(2 ** retries)
                retries += 1
                if retries == 5:
                    return jsonify({'error': f'Failed to generate report: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)