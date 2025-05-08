"""
# Student Page Routes
# This file defines:
# - Routes for student HTML pages
# - Template rendering logic
"""

from flask import Blueprint, render_template, send_from_directory, current_app, session, redirect, url_for, request

page_bp = Blueprint('student_pages', __name__, url_prefix='/students')

@page_bp.route('/login', methods=['GET'])
def login_page():
    """Render the student login page"""
    # Check if already logged in
    if 'student_id' in session:
        return redirect('/students/dashboard')
    return render_template('students/login.html')

@page_bp.route('/register', methods=['GET'])
def register_page():
    """Render the student registration page"""
    # Check if already logged in
    if 'student_id' in session:
        return redirect('/students/dashboard')
    return render_template('students/register.html')

@page_bp.route('/dashboard', methods=['GET'])
def dashboard_page():
    """Render the student dashboard page"""
    # Check if logged in
    if 'student_id' not in session:
        return redirect('/students/login')
    return render_template('students/dashboard.html')

@page_bp.route('/verify-email', methods=['GET'])
def verify_email_page():
    """Render the email verification page"""
    token = request.args.get('token')
    if token:
        # If a token is provided, redirect to the API endpoint
        return redirect(url_for('student.verify_email', token=token))
    
    # Show verification needed page
    return render_template('students/verify_email.html')

@page_bp.route('/verification-success', methods=['GET'])
def verification_success_page():
    """Render the verification success page"""
    return render_template('students/verification_success.html')

@page_bp.route('/verification-failed', methods=['GET'])
def verification_failed_page():
    """Render the verification failed page"""
    error = request.args.get('error', 'Unknown error')
    return render_template('students/verification_failed.html', error=error)

@page_bp.route('/list', methods=['GET'])
def list_page():
    """Render the student list page (admin only)"""
    # Check if admin
    if 'is_admin' not in session or not session['is_admin']:
        return redirect('/students/login')
    return render_template('students/list.html') 