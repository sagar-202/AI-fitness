from flask import Blueprint, request, jsonify, session, current_app
from database import get_db_connection
from datetime import datetime, timedelta
import os
import requests
from functools import wraps

api_bp = Blueprint('api', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        require_auth = os.environ.get('REQUIRE_AUTH', '1')
        if require_auth == '0':
            return f(*args, **kwargs)
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated

@api_bp.route('/api/reset_session', methods=['POST'])
def reset_session():
    analyzer = current_app.config.get('ANALYZER')
    if analyzer:
        analyzer.rep_count = 0
        analyzer.form_scores = []
        analyzer.current_rep_scores = []
        analyzer.session_state = {'current_phase': 'neutral', 'frames_in_phase': 0, 'last_confirmed_phase': 'neutral', 'phase_history': []}
        analyzer.last_rep_time = None
    return jsonify({'ok': True}), 200

@api_bp.route('/api/analyze_pose', methods=['POST'])
def analyze_pose():
    analyzer = current_app.config.get('ANALYZER')
    if not analyzer:
         return jsonify({'error': 'Analyzer not initialized'}), 500

    data = request.get_json(force=True)
    if not data:
        return jsonify({'error': 'no data'}), 400

    exercise = data.get('exercise', 'squats')
    landmarks = data.get('landmarks', [])

    if not isinstance(landmarks, list) or len(landmarks) < 5:
        return jsonify({'error': 'invalid landmarks'}), 400

    normalized = []
    for lm in landmarks:
        if isinstance(lm, dict):
            normalized.append({'x': float(lm.get('x', 0)), 'y': float(lm.get('y', 0)), 'z': float(lm.get('z', 0)) if 'z' in lm else 0.0, 'visibility': float(lm.get('visibility', 0)) if 'visibility' in lm else 1.0})
        else:
            try:
                normalized.append({'x': float(getattr(lm, 'x', 0)), 'y': float(getattr(lm, 'y', 0)), 'z': float(getattr(lm, 'z', 0)), 'visibility': float(getattr(lm, 'visibility', 0))})
            except Exception:
                normalized.append({'x': 0.0, 'y': 0.0, 'z': 0.0, 'visibility': 0.0})

    analyzer.current_exercise = exercise

    try:
        feedback_info = analyzer.generate_detailed_feedback(normalized, exercise)
    except Exception as e:
        feedback_info = {'feedback': [], 'form_score': (analyzer.form_scores[-1] if analyzer.form_scores else 50), 'movement_quality': {}, 'exercise_phase': analyzer.session_state.get('last_confirmed_phase', 'neutral')}

    try:
        rep_completed = analyzer.process_repetition_counting(normalized, exercise)
    except Exception as e:
        rep_completed = False

    response = {
        'reps': analyzer.rep_count,
        'rep_completed': bool(rep_completed),
        'form_score': feedback_info.get('form_score', 0),
        'feedback': feedback_info.get('feedback', []),
        'movement_quality': feedback_info.get('movement_quality', {}),
        'exercise_phase': feedback_info.get('exercise_phase', analyzer.session_state.get('last_confirmed_phase', 'neutral'))
    }

    return jsonify(response), 200

@api_bp.route('/api/save_workout', methods=['POST'])
@login_required
def save_workout():
    analyzer = current_app.config.get('ANALYZER')
    data = request.get_json(force=True) or {}
    user_id = session.get('user_id')
    
    exercise = data.get('exercise', 'unknown')
    reps = int(data.get('reps', 0))

    duration_seconds = data.get('duration_seconds', None)
    form_score = data.get('form_score', None)
    calories_burned = data.get('calories_burned', None)

    try:
        if duration_seconds is None:
            duration_seconds = int(getattr(analyzer, 'session_duration', 0) or 0)
    except Exception:
        duration_seconds = 0

    try:
        if form_score is None:
            form_score = float(analyzer.form_scores[-1]) if analyzer and analyzer.form_scores else 0.0
        else:
            form_score = float(form_score)
    except Exception:
        form_score = 0.0

    try:
        if calories_burned is None:
            calories_per_rep = {'squats':0.32,'pushups':0.29,'lunges':0.35,'bicep_curls':0.20}
            base = reps * calories_per_rep.get(exercise, 0.25)
            form_mult = 0.8 + (float(form_score) / 500.0)
            calories_burned = round(base * form_mult, 1)
    except Exception:
        calories_burned = 0.0

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO workout_sessions (user_id, session_date, exercise_name, total_reps, avg_form_score, duration_seconds, calories_burned, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, datetime.now().isoformat(), exercise, reps, float(form_score), int(duration_seconds), float(calories_burned), data.get('notes','')))
    conn.commit()
    conn.close()

    return jsonify({'ok': True, 'reps': reps, 'form_score': float(form_score), 'duration_seconds': int(duration_seconds), 'calories_burned': float(calories_burned)}), 200

@api_bp.route('/api/workout_history', methods=['GET'])
@login_required
def api_workout_history():
    user_id = session.get('user_id')
    limit = request.args.get('limit', 10, type=int)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, session_date, exercise_name, total_reps, avg_form_score, duration_seconds, calories_burned, notes
        FROM workout_sessions
        WHERE user_id = ?
        ORDER BY session_date DESC
        LIMIT ?
    """, (user_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({'history': rows}), 200

@api_bp.route('/api/workout/<int:workout_id>', methods=['DELETE'])
@login_required
def delete_workout(workout_id):
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if workout exists and belongs to user
    cur.execute("SELECT id FROM workout_sessions WHERE id = ? AND user_id = ?", (workout_id, user_id))
    if not cur.fetchone():
        conn.close()
        return jsonify({'error': 'Workout not found or unauthorized'}), 404
        
    cur.execute("DELETE FROM workout_sessions WHERE id = ?", (workout_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True}), 200

@api_bp.route('/api/reports/summary', methods=['GET'])
@login_required
def report_summary():
    user_id = session.get('user_id')
    days = request.args.get('days', 30, type=int)
    start_date = (datetime.now() - timedelta(days=days)).isoformat()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) as total_workouts,
            SUM(total_reps) as total_reps,
            AVG(avg_form_score) as avg_form_score,
            SUM(calories_burned) as total_calories
        FROM workout_sessions
        WHERE user_id = ? AND session_date >= ?
    """, (user_id, start_date))
    row = cur.fetchone()
    conn.close()
    return jsonify({
        'total_workouts': row['total_workouts'] or 0,
        'total_reps': row['total_reps'] or 0,
        'avg_form_score': round(row['avg_form_score'] or 0, 1),
        'total_calories': round(row['total_calories'] or 0, 1)
    }), 200

@api_bp.route('/api/reports/exercise_breakdown', methods=['GET'])
@login_required
def report_exercise_breakdown():
    user_id = session.get('user_id')
    days = request.args.get('days', 30, type=int)
    start_date = (datetime.now() - timedelta(days=days)).isoformat()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT exercise_name, SUM(total_reps) as total_reps
        FROM workout_sessions
        WHERE user_id = ? AND session_date >= ?
        GROUP BY exercise_name
        ORDER BY total_reps DESC
    """, (user_id, start_date))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows), 200

@api_bp.route('/api/reports/progress_timeline', methods=['GET'])
@login_required
def report_progress_timeline():
    user_id = session.get('user_id')
    days = request.args.get('days', 30, type=int)
    start_date = (datetime.now() - timedelta(days=days)).isoformat()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            substr(session_date, 1, 10) as date,
            SUM(total_reps) as total_reps,
            AVG(avg_form_score) as avg_form_score
        FROM workout_sessions
        WHERE user_id = ? AND session_date >= ?
        GROUP BY date
        ORDER BY date ASC
    """, (user_id, start_date))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows), 200

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

@api_bp.route('/api/generate_report', methods=['POST'])
@login_required
def generate_report():
    try:
        data = request.get_json() or {}
        prompt = data.get('prompt', 'Provide a comprehensive analysis of my workout history.')
        user_id = session.get('user_id')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT session_date, exercise_name, total_reps, avg_form_score, duration_seconds, calories_burned
            FROM workout_sessions
            WHERE user_id = ?
            ORDER BY session_date DESC
            LIMIT 30
        """, (user_id,))
        sessions = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not sessions:
            return jsonify({'report': 'No workout history found. Do a few sessions and try again.'}), 200

        history_lines = []
        for s in sessions:
            d = s.get('session_date') or ''
            try:
                d = datetime.fromisoformat(d).strftime('%Y-%m-%d')
            except Exception:
                pass
            history_lines.append(f"{d}: {s.get('exercise_name','')}: {s.get('total_reps',0)} reps, Form {s.get('avg_form_score',0):.1f}%, {s.get('duration_seconds',0)}s, {s.get('calories_burned',0):.1f} cal")
        history_str = "\n".join(history_lines)
        full_prompt = (
            f"You are an expert fitness coach analyzing a user's workout history. {prompt}\n\n"
            f"User history (last 30 sessions):\n{history_str}\n\n"
            "Please provide a structured response with:\n"
            "1. **Summary**: A brief overview of their recent activity levels and consistency.\n"
            "2. **Strengths**: What are they doing well? (e.g., high form score in squats, consistent schedule).\n"
            "3. **Areas for Improvement**: Specific advice on exercises with lower form scores or low volume.\n"
            "4. **Actionable Plan**: 3 concrete steps they can take next week to improve.\n\n"
            "Keep the tone encouraging but professional and data-driven."
        )

        if GEMINI_API_KEY:
            try:
                headers = {'Authorization': f'Bearer {GEMINI_API_KEY}', 'Content-Type': 'application/json'}
                payload = {'prompt': full_prompt}
                resp = requests.post(os.environ.get('GEMINI_API_URL', "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"), json=payload, headers=headers, timeout=20)
                resp.raise_for_status()
                report_text = resp.json().get('report') or resp.text or str(resp.json())
                return jsonify({'report': report_text}), 200
            except Exception as e:
                current_app.logger.warning("Remote AI call failed, using local summary: %s", e)

        total_sessions = len(sessions)
        total_reps = sum(int(s.get('total_reps',0)) for s in sessions)
        avg_form = (sum(float(s.get('avg_form_score',0)) for s in sessions) / total_sessions) if total_sessions else 0.0
        by_ex = {}
        for s in sessions:
            name = s.get('exercise_name','unknown')
            by_ex[name] = by_ex.get(name,0) + int(s.get('total_reps',0))
        top_ex = max(by_ex.items(), key=lambda x: x[1])[0] if by_ex else 'N/A'

        summary = (
            f"Local Analysis ({total_sessions} sessions):\n"
            f"- Total reps: {total_reps}\n"
            f"- Average form score: {avg_form:.1f}%\n"
            f"- Most performed exercise: {top_ex}\n\n"
            "Recommendations:\n"
            "1) Keep consistent tempo and full range of motion.\n"
            "2) Improve form for exercises with lower form %.\n"
            "3) Add progressive overload gradually.\n"
        )
        return jsonify({'report': summary}), 200

    except Exception as e:
        current_app.logger.exception("generate_report error")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/chat_insights', methods=['POST'])
@login_required
def chat_insights():
    try:
        payload = request.get_json() or {}
        question = (payload.get('question') or '').strip()
        if not question:
            return jsonify({'answer': "Please ask a question about your workouts."}), 200

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT session_date, exercise_name, total_reps, avg_form_score, duration_seconds, calories_burned
            FROM workout_sessions
            WHERE user_id = ?
            ORDER BY session_date DESC
            LIMIT 30
        """, (session.get('user_id'),))
        sessions = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not sessions:
            local_answer = ("I don't have any workout history for you yet. "
                            "Start a session and then ask me for tailored advice. "
                            "Meanwhile, a general tip: focus on full range of motion and controlled tempo.")
            return jsonify({'answer': local_answer}), 200

        history_lines = []
        for s in sessions:
            d = s.get('session_date') or ''
            try:
                d = datetime.fromisoformat(d).strftime('%Y-%m-%d')
            except Exception:
                pass
            history_lines.append(f"{d}: {s.get('exercise_name','')}: {s.get('total_reps',0)} reps, Form {s.get('avg_form_score',0):.1f}%, {s.get('duration_seconds',0)}s")

        context = "\n".join(history_lines)
        full_prompt = (
            f"You are a helpful fitness coach. The user asks: \"{question}\".\n\n"
            f"User recent sessions (most recent first):\n{context}\n\n"
            "Provide a concise, actionable answer (3-5 bullet points) tailored to the user's history."
        )

        gemini_key = os.environ.get('GEMINI_API_KEY', 'AIzaSyCv_s1oVIZR8DXpNTnTBL376XlP-WOp-z0')
        if gemini_key:
            try:
                headers = {'Content-Type': 'application/json'}
                # Use the correct Gemini 1.5 Flash endpoint
                api_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}'
                
                ai_payload = {
                    "contents": [{
                        "parts": [{"text": full_prompt}]
                    }]
                }
                
                resp = requests.post(api_url, json=ai_payload, headers=headers, timeout=20)
                resp.raise_for_status()
                
                j = resp.json()
                # Extract text from Gemini response structure
                answer = j.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                if not answer:
                    answer = "I couldn't generate a response. Please try again."
                    
                return jsonify({'answer': answer}), 200
            except Exception as e:
                current_app.logger.warning("chat_insights: remote AI call failed: %s", e)
                # Fallback to local answer if API fails


        total_reps = sum(int(s.get('total_reps', 0)) for s in sessions)
        avg_form = (sum(float(s.get('avg_form_score', 0)) for s in sessions) / len(sessions)) if sessions else 0.0
        by_ex = {}
        for s in sessions:
            name = s.get('exercise_name', 'unknown')
            by_ex[name] = by_ex.get(name, 0) + int(s.get('total_reps', 0))
        top_ex = max(by_ex.items(), key=lambda x: x[1])[0] if by_ex else 'N/A'

        local_answer = (
            f"Local insight based on your recent {len(sessions)} session(s):\n"
            f"- Total reps recorded: {total_reps}\n"
            f"- Avg form score: {avg_form:.1f}%\n"
            f"- Most practiced: {top_ex}\n\n"
            f"Regarding your question \"{question}\":\n"
            "1) Focus on consistent tempo and full range of motion for each rep.\n"
            "2) If your form score is low, slow down and prioritize form over speed/quantity.\n"
            "3) Try adding small progressive overload (e.g., +1 rep per session) for the primary exercise.\n"
            "If you want, ask me to 'recommend a 2-week plan' or 'compare my last two sessions'."
        )
        return jsonify({'answer': local_answer}), 200

    except Exception as exc:
        current_app.logger.exception("chat_insights unexpected error")
        return jsonify({'answer': 'Internal error: ' + str(exc)}), 500
