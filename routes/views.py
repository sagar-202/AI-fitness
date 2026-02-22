from flask import Blueprint, render_template, send_from_directory
import os

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    return render_template('index.html')

@views_bp.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)
