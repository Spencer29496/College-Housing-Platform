"""
# Student Routes
# This file defines:
# - API endpoints for student operations
# - Route handlers for student actions
"""

from flask import Blueprint, current_app, redirect, session, jsonify, request
from server_ui.students.controllers.student_controller import StudentController

student_bp = Blueprint('student', __name__, url_prefix='/students')

@student_bp.route('/register', methods=['POST'])
def register():
    """Register a new student"""
    conn = current_app.config['get_db_connection']()
    controller = StudentController(conn)
    response = controller.register_student()
    conn.close()
    return response

@student_bp.route('/login', methods=['POST'])
def login():
    """Login a student"""
    conn = current_app.config['get_db_connection']()
    controller = StudentController(conn)
    response = controller.login_student()
    conn.close()
    return response

@student_bp.route('/logout', methods=['POST'])
def logout():
    """Logout a student"""
    conn = current_app.config['get_db_connection']()
    controller = StudentController(conn)
    response = controller.logout_student()
    conn.close()
    return response

@student_bp.route('/verify/<token>', methods=['GET'])
def verify_email(token):
    """Verify student email"""
    conn = current_app.config['get_db_connection']()
    controller = StudentController(conn)
    response = controller.verify_email(token)
    conn.close()
    
    # Check response status
    if response.status_code == 200:
        # Redirect to success page
        return redirect('/students/verification-success')
    else:
        # Redirect to error page with error message
        error = response.json.get('error', 'Unknown error')
        return redirect(f'/students/verification-failed?error={error}')

@student_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification email"""
    conn = current_app.config['get_db_connection']()
    controller = StudentController(conn)
    response = controller.resend_verification_email()
    conn.close()
    return response

@student_bp.route('/mock-verify', methods=['POST'])
def mock_verify():
    """Mock verification for development purposes only"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({
                'error': 'Email is required'
            }), 400
            
        conn = current_app.config['get_db_connection']()
        
        # Get the student model
        from server_ui.students.models.student_model import Student
        student_model = Student(conn)
        
        # Get student by email
        student = student_model.get_student_by_email(email)
        
        if not student:
            conn.close()
            return jsonify({
                'error': 'Student not found'
            }), 404
            
        # Directly update the database to mark the user as verified
        cur = conn.cursor()
        cur.execute(
            "UPDATE students SET is_verified = TRUE, verification_token = NULL, verification_token_expires = NULL WHERE id = %s",
            (student['id'],)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        # Set session variables
        session['student_id'] = student['id']
        session['is_verified'] = True
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully'
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@student_bp.route('/profile/<int:student_id>', methods=['GET'])
def get_profile(student_id):
    """Get student profile"""
    conn = current_app.config['get_db_connection']()
    controller = StudentController(conn)
    response = controller.get_student_profile(student_id)
    conn.close()
    return response

@student_bp.route('/', methods=['GET'])
def get_all():
    """Get all students with optional filters"""
    conn = current_app.config['get_db_connection']()
    controller = StudentController(conn)
    response = controller.get_all_students()
    conn.close()
    return response

@student_bp.route('/current', methods=['GET'])
def get_current_student():
    """Get current logged in student from session"""
    student_id = session.get('student_id', None)
    return jsonify({
        'student_id': student_id
    }) 