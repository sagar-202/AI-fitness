from collections import deque
import numpy as np
from sklearn.preprocessing import StandardScaler
import time

class EnhancedExerciseAnalyzer:
    def __init__(self):
        # Buffers
        self.pose_buffer = deque(maxlen=60)
        self.angle_buffer = deque(maxlen=30)
        self.velocity_buffer = deque(maxlen=15)

        # basic state
        self.exercise_state = 'neutral'
        self.rep_count = 0
        self.current_exercise = None
        self.form_scores = []
        self.current_rep_scores = []
        self.movement_quality_scores = []
        self.session_start_time = None
        self.last_rep_time = None
        self.phase_start_time = None
        self.consecutive_good_frames = 0
        self.min_consecutive_frames = 2

        self.scaler = StandardScaler()

        # Exercise configs - make sure keys match frontend data-exercise values
        self.exercise_configs = {
            'squats': {
                'angle_joints': [(23, 25, 27), (24, 26, 28)],
                'min_angle': 80,
                'max_angle': 165,
                'angle_tolerance': 25,
                'min_rep_time': 0.3,
                'max_rep_time': 5.0
            },
            'pushups': {
                'angle_joints': [(11, 13, 15), (12, 14, 16)],
                'min_angle': 100,
                'max_angle': 165,
                'angle_tolerance': 25,
                'min_rep_time': 0.3,
                'max_rep_time': 4.0
            },
            'lunges': {
                'angle_joints': [(23, 25, 27), (24, 26, 28)],
                'min_angle': 90,
                'max_angle': 165,
                'angle_tolerance': 25,
                'min_rep_time': 0.4,
                'max_rep_time': 5.0
            },
            'bicep_curls': {
                'angle_joints': [(11, 13, 15), (12, 14, 16)],
                'min_angle': 30,
                'max_angle': 160,
                'angle_tolerance': 30,
                'min_rep_time': 0.3,
                'max_rep_time': 4.0
            }
        }

        # canonical pattern mapping (normalized exercise name -> pattern)
        self.rep_patterns = {
            'squats': ['standing', 'bottom', 'standing'],
            'pushups': ['standing', 'bottom', 'standing'],
            'lunges': ['standing', 'bottom', 'standing'],
            'bicep_curls': ['standing', 'bottom', 'standing']
        }

        # lightweight session_storage for confirmed phases, etc.
        self.session_state = {
            'current_phase': 'neutral',
            'frames_in_phase': 0,
            'last_confirmed_phase': 'neutral',
            'phase_history': []
        }

    # ------------------------
    # Angle calculation helpers
    # ------------------------
    def calculate_angle_from_points(self, a, b, c):
        """Compute angle at b formed by points a-b-c using 2D positions."""
        try:
            v1 = np.array([a['x'] - b['x'], a['y'] - b['y']])
            v2 = np.array([c['x'] - b['x'], c['y'] - b['y']])
            denom = (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
            cosang = np.dot(v1, v2) / denom
            cosang = float(np.clip(cosang, -1.0, 1.0))
            angle = float(np.degrees(np.arccos(cosang)))
            return angle
        except Exception:
            return None

    def calculate_all_joint_angles(self, landmarks, exercise_type):
        """Return list of joint angles corresponding to angle_joints in config."""
        cfg = self.exercise_configs.get(exercise_type, {})
        angle_joints = cfg.get('angle_joints', [])
        angles = []
        for trip in angle_joints:
            try:
                a_idx, b_idx, c_idx = trip
                a = landmarks[a_idx]
                b = landmarks[b_idx]
                c = landmarks[c_idx]
                ang = self.calculate_angle_from_points(a, b, c)
                angles.append(ang if ang is not None else 0.0)
            except Exception:
                angles.append(0.0)
        return angles

    # ------------------------
    # Internal helper: compute a single representative key angle
    # ------------------------
    def _compute_key_angle(self, landmarks, exercise_type):
        cfg = self.exercise_configs.get(exercise_type, {})
        angle_joints = cfg.get('angle_joints', [])
        if not angle_joints:
            return None
        # Use first triplet as key joint
        trip = angle_joints[0]
        try:
            a_idx, b_idx, c_idx = trip
            a = landmarks[a_idx]; b = landmarks[b_idx]; c = landmarks[c_idx]
            ang = self.calculate_angle_from_points(a, b, c)
            return ang
        except Exception:
            return None

    # ------------------------
    # Phase detection (robust & responsive)
    # ------------------------
    def detect_exercise_phase(self, landmarks, exercise_type):
        """
        Returns 'standing' (top), 'bottom', or 'transition' / 'unknown'.
        Uses key angle computed from landmarks and small smoothing window.
        """
        # normalize exercise type to match keys
        ex_key = self._normalize_exercise_name(exercise_type)
        cfg = self.exercise_configs.get(ex_key, {})
        if not cfg:
            return 'unknown'

        key_angle = self._compute_key_angle(landmarks, ex_key)
        if key_angle is None:
            return 'unknown'

        min_angle = cfg.get('min_angle', 60)
        max_angle = cfg.get('max_angle', 160)
        tol = cfg.get('angle_tolerance', 20)

        if key_angle <= min_angle + tol:
            return 'bottom'
        elif key_angle >= max_angle - tol:
            return 'standing'
        else:
            return 'transition'

    # ------------------------
    # Rep counting: robust, uses confirmed phases and pattern matching
    # ------------------------
    def process_repetition_counting(self, landmarks, exercise_type):
        """
        Confirms phase if observed for FRAMES_TO_CONFIRM consecutive frames,
        appends confirmed phase to session phase_history, and counts rep when
        last 3 confirmed phases match canonical pattern for the exercise.
        """
        ex_key = self._normalize_exercise_name(exercise_type)
        cfg = self.exercise_configs.get(ex_key, {})

        # update angle buffer with newest angles (small window)
        angles_now = self.calculate_all_joint_angles(landmarks, ex_key)
        # push latest angles to buffer (for potential other calculations)
        self.angle_buffer.append(angles_now)

        # phase detection
        detected_phase = self.detect_exercise_phase(landmarks, ex_key)
        state = self.session_state

        # unknown -> don't increment frames; keep stable last state
        if detected_phase == 'unknown':
            state['frames_in_phase'] = 0
            return False

        # update frames_in_phase
        if detected_phase == state['current_phase']:
            state['frames_in_phase'] += 1
        else:
            state['current_phase'] = detected_phase
            state['frames_in_phase'] = 1

        FRAMES_TO_CONFIRM = 2  # tradeoff responsiveness vs noise
        rep_completed = False

        # confirm a phase and update history
        if state['frames_in_phase'] >= FRAMES_TO_CONFIRM and detected_phase != state['last_confirmed_phase']:
            state['phase_history'].append(detected_phase)
            if len(state['phase_history']) > 12:
                state['phase_history'] = state['phase_history'][-12:]
            state['last_confirmed_phase'] = detected_phase

            # attempt to match last 3 confirmed phases with canonical pattern
            if len(state['phase_history']) >= 3:
                pattern = state['phase_history'][-3:]
                target_pattern = self.rep_patterns.get(ex_key)
                # soft form score check (non-blocking): if generate_detailed_feedback exists
                try:
                    feedback_info = self.generate_detailed_feedback(landmarks, ex_key)
                    current_form_score = feedback_info.get('form_score', 50) if isinstance(feedback_info, dict) else 50
                except Exception:
                    current_form_score = 50

                FORM_THRESHOLD = 30  # low threshold so correct reps are not dropped
                if target_pattern and pattern == target_pattern and current_form_score >= FORM_THRESHOLD:
                    # honor minimum time between reps
                    now = time.time()
                    if not self.last_rep_time or (now - self.last_rep_time) >= cfg.get('min_rep_time', 0.2):
                        self.rep_count += 1
                        rep_completed = True
                        self.last_rep_time = now
                        # reset per-rep scores
                        self.current_rep_scores = []

        return rep_completed

    # ------------------------
    # Form / feedback generation (keeps existing structure)
    # ------------------------
    def generate_detailed_feedback(self, landmarks, exercise_type):
        """
        Compute feedback and form_score.
        The implementation uses existing per-exercise analyzers if available.
        For compatibility, exercise_type is normalized.
        """
        ex_key = self._normalize_exercise_name(exercise_type)
        feedback = []
        form_score = 100

        # exercise-specific checks (basic fallbacks if detailed functions not present)
        if ex_key == 'squats':
            try:
                left_hip = landmarks[23]; right_hip = landmarks[24]
                left_knee = landmarks[25]; right_knee = landmarks[26]
                left_ankle = landmarks[27]; right_ankle = landmarks[28]
                # compute knee angles
                lk = self.calculate_angle_from_points(left_hip, left_knee, left_ankle)
                rk = self.calculate_angle_from_points(right_hip, right_knee, right_ankle)
                if lk is None or rk is None:
                    pass
                else:
                    avg_knee = (lk + rk) / 2.0
                    if avg_knee > 120:
                        feedback.append("Go deeper for better results")
                        form_score -= 15
                    elif avg_knee < 70:
                        feedback.append("Excellent depth")
                        form_score += 2
                    # symmetry
                    if abs(lk - rk) > 20:
                        feedback.append("Balance both sides evenly")
                        form_score -= 20
            except Exception:
                pass

        elif ex_key == 'pushups':
            try:
                # Use elbow angles
                left_shoulder = landmarks[11]; left_elbow = landmarks[13]; left_wrist = landmarks[15]
                le = self.calculate_angle_from_points(left_shoulder, left_elbow, left_wrist)
                right_shoulder = landmarks[12]; right_elbow = landmarks[14]; right_wrist = landmarks[16]
                re = self.calculate_angle_from_points(right_shoulder, right_elbow, right_wrist)
                if le is not None and re is not None:
                    avg_elbow = (le + re) / 2.0
                    if avg_elbow > 150:
                        feedback.append("Lower chest more to complete the rep")
                        form_score -= 12
                    elif avg_elbow < 90:
                        feedback.append("Good range")
            except Exception:
                pass

        elif ex_key == 'lunges':
            # basic checks similar to squats
            try:
                left_hip = landmarks[23]; left_knee = landmarks[25]; left_ankle = landmarks[27]
                lk = self.calculate_angle_from_points(left_hip, left_knee, left_ankle)
                if lk is not None and lk > 120:
                    feedback.append("Bend the front knee more")
                    form_score -= 10
            except Exception:
                pass

        elif ex_key == 'bicep_curls':
            try:
                left_shoulder = landmarks[11]; left_elbow = landmarks[13]; left_wrist = landmarks[15]
                le = self.calculate_angle_from_points(left_shoulder, left_elbow, left_wrist)
                if le is not None and le > 120:
                    feedback.append("Curl more to complete the rep")
                    form_score -= 8
            except Exception:
                pass

        # movement_quality fallback
        mq = self.analyze_movement_quality(landmarks)
        if mq.get('smoothness', 50) < 45:
            feedback.append("Move more smoothly")
            form_score -= 8
        if mq.get('stability', 50) < 40:
            feedback.append("Improve stability")
            form_score -= 10

        form_score = max(0, min(100, form_score))
        self.current_rep_scores.append(form_score)
        self.form_scores.append(form_score)

        return {
            'feedback': feedback[:3],
            'form_score': form_score,
            'movement_quality': mq,
            'exercise_phase': self.detect_exercise_phase(landmarks, ex_key)
        }

    # ------------------------
    # Movement quality helpers (simple)
    # ------------------------
    def extract_pose_features(self, landmarks):
        try:
            flat = []
            for lm in landmarks:
                flat.extend([lm['x'], lm['y']])
            return np.array(flat)
        except Exception:
            return None

    def analyze_movement_quality(self, landmarks):
        features = self.extract_pose_features(landmarks)
        if features is None:
            return {'quality_score': 0, 'smoothness': 50, 'stability': 50}
        self.pose_buffer.append(features)
        if len(self.pose_buffer) < 8:
            return {'quality_score': 50, 'smoothness': 60, 'stability': 60}
        # compute trivial smoothness/stability proxies
        poses = np.array(list(self.pose_buffer))
        vel = np.mean(np.abs(np.diff(poses, axis=0)))
        smoothness = max(0, 100 - vel * 2000)
        stability = max(0, 100 - np.var(poses) * 2000)
        return {'quality_score': (smoothness + stability) / 2, 'smoothness': smoothness, 'stability': stability}

    # ------------------------
    # Utility: normalize exercise name
    # ------------------------
    def _normalize_exercise_name(self, exercise_name):
        if not exercise_name:
            return 'squats'
        s = exercise_name.strip().lower()
        # map common variants
        mapping = {
            'squat': 'squats',
            'squats': 'squats',
            'pushup': 'pushups',
            'push-ups': 'pushups',
            'push up': 'pushups',
            'pushups': 'pushups',
            'lunge': 'lunges',
            'lunges': 'lunges',
            'bicep_curl': 'bicep_curls',
            'bicep curl': 'bicep_curls',
            'bicep_curls': 'bicep_curls',
            'bicep curls': 'bicep_curls'
        }
        return mapping.get(s, s)
