from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
from datetime import datetime
import sqlite3

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400
    password_hash = generate_password_hash(password)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO users (username, email, password_hash, created_at) VALUES (?,?,?,?)',
                    (username, email, password_hash, datetime.now().isoformat()))
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'username already exists'}), 409
    conn.close()
    session['user_id'] = user_id
    return jsonify({'user': {'id': user_id, 'username': username}}), 200

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, username, password_hash FROM users WHERE username=? OR email=?', (username, username))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'invalid credentials'}), 401
    user_id, uname, p_hash = row['id'], row['username'], row['password_hash']
    if not check_password_hash(p_hash, password):
        return jsonify({'error': 'invalid credentials'}), 401
    session['user_id'] = user_id
    return jsonify({'user': {'id': user_id, 'username': uname}}), 200

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True}), 200

@auth_bp.route('/api/check_session', methods=['GET'])
def check_session():
    # Note: Circular import issue if we import analyzer here directly for stats.
    # For now, we will return basic session info. 
    # Ideally, stats should be fetched from a service or database if persistent.
    # We will handle analyzer integration in the main app factory or via a shared service instance.
    logged_in = 'user_id' in session
    user = {}
    if logged_in:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, username, email FROM users WHERE id=?', (session['user_id'],))
        row = cur.fetchone()
        conn.close()
        if row:
            user = {'id': row['id'], 'username': row['username'], 'email': row['email']}
    
    # We need access to the analyzer instance to return current reps/form.
    # We'll attach it to the app config or use a singleton pattern.
    from flask import current_app
    analyzer = current_app.config.get('ANALYZER')
    
    reps = analyzer.rep_count if analyzer else 0
    form_score = (analyzer.form_scores[-1] if analyzer and analyzer.form_scores else 0)
    phase = analyzer.session_state.get('last_confirmed_phase', 'neutral') if analyzer else 'neutral'

    return jsonify({'logged_in': logged_in, 'user': user, 'reps': reps, 'form_score': form_score, 'exercise_phase': phase}), 200
