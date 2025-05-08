"""
# Student Controller
# This file handles:
# - Logic for student operations
# - Auth and validation for student actions
"""

from flask import request, session, jsonify, make_response, current_app
from server_ui.students.models.student_model import Student
from server_ui.utils.email_utils import generate_verification_token, get_verification_expiry, send_verification_email

class StudentController:
    def __init__(self, db_connection):
        self.student_model = Student(db_connection)
    
    def register_student(self):
        """Register a new student"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['name', 'email', 'password', 'year', 'major', 'student_id']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Validate Binghamton email
            if not data['email'].endswith('@binghamton.edu'):
                return jsonify({'error': 'Please use a valid Binghamton email address (@binghamton.edu)'}), 400
            
            # Check if email already exists
            existing_student = self.student_model.get_student_by_email(data['email'])
            if existing_student:
                return jsonify({'error': 'Email already registered'}), 409
            
            # Generate verification token
            verification_token = generate_verification_token()
            verification_token_expires = get_verification_expiry()
            
            # Create new student
            student_id = self.student_model.create_student(
                data['name'],
                data['email'],
                data['password'],
                data['year'],
                data['major'],
                data['student_id'],
                verification_token,
                verification_token_expires
            )
            
            # Send verification email
            email_sent = send_verification_email(data['email'], verification_token)
            
            if not email_sent:
                current_app.logger.warning(f"Failed to send verification email to {data['email']}")
            
            return jsonify({
                'message': 'Student registered successfully. Please check your email to verify your account.',
                'student_id': student_id,
                'email_verification_sent': email_sent
            }), 201
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def login_student(self):
        """Login a student"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if 'email' not in data or 'password' not in data:
                return jsonify({'error': 'Email and password required'}), 400
            
            # Validate Binghamton email
            if not data['email'].endswith('@binghamton.edu'):
                return jsonify({'error': 'Please use a valid Binghamton email address (@binghamton.edu)'}), 400
            
            # Verify credentials
            is_valid = self.student_model.verify_password(data['email'], data['password'])
            if not is_valid:
                return jsonify({'error': 'Invalid email or password'}), 401
            
            # Get student details
            student = self.student_model.get_student_by_email(data['email'])
            
            # Check if email is verified
            if not student['is_verified']:
                return jsonify({
                    'error': 'Email not verified',
                    'requires_verification': True,
                    'student_id': student['id']
                }), 403
            
            # Set session data
            session['student_id'] = student['id']
            session['student_email'] = student['email']
            
            # Return success without sensitive data
            if 'password_hash' in student:
                del student['password_hash']
                
            return jsonify({
                'message': 'Login successful',
                'student': student
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def logout_student(self):
        """Logout a student"""
        try:
            # Clear session
            session.pop('student_id', None)
            session.pop('student_email', None)
            
            return jsonify({'message': 'Logout successful'})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def verify_email(self, token):
        """Verify student email using token"""
        try:
            success, message = self.student_model.verify_email(token)
            
            if success:
                # Redirect to success page
                return make_response(jsonify({'message': message}), 200)
            else:
                # Redirect to error page with the error message
                return make_response(jsonify({'error': message}), 400)
                
        except Exception as e:
            return make_response(jsonify({'error': str(e)}), 500)
    
    def resend_verification_email(self):
        """Resend verification email"""
        try:
            data = request.get_json()
            
            if 'email' not in data:
                return jsonify({'error': 'Email is required'}), 400
                
            # Validate Binghamton email
            if not data['email'].endswith('@binghamton.edu'):
                return jsonify({'error': 'Please use a valid Binghamton email address (@binghamton.edu)'}), 400
            
            # Get student by email
            student = self.student_model.get_student_by_email(data['email'])
            
            if not student:
                # Don't reveal if email exists or not for security
                return jsonify({'message': 'If the email exists, a verification link has been sent.'}), 200
            
            # Check if already verified
            if student['is_verified']:
                return jsonify({'message': 'Email is already verified. You can log in.'}), 200
            
            # Generate new verification token
            verification_token = generate_verification_token()
            verification_token_expires = get_verification_expiry()
            
            # Update token in database
            self.student_model.update_verification_token(
                data['email'], 
                verification_token, 
                verification_token_expires
            )
            
            # Send verification email
            email_sent = send_verification_email(data['email'], verification_token, is_resend=True)
            
            return jsonify({
                'message': 'Verification email has been sent. Please check your inbox.',
                'email_sent': email_sent
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def get_student_profile(self, student_id):
        """Get student profile by ID"""
        try:
            # Authorization check
            if 'student_id' not in session or session['student_id'] != student_id:
                return jsonify({'error': 'Unauthorized'}), 401
            
            student = self.student_model.get_student_by_id(student_id)
            if not student:
                return jsonify({'error': 'Student not found'}), 404
            
            # Remove sensitive data
            if 'password_hash' in student:
                del student['password_hash']
            
            return jsonify({'student': student})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def get_all_students(self):
        """Get all students with optional filters"""
        try:
            # Get filter parameters
            filters = {}
            if 'year' in request.args:
                filters['year'] = request.args.get('year')
            if 'major' in request.args:
                filters['major'] = request.args.get('major')
            
            students = self.student_model.get_all_students(filters)
            return jsonify({'students': students})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500 