"""
Authentication routes for user signup, login, and verification
"""
from flask import Blueprint, request, jsonify, current_app
import uuid
import logging
from datetime import datetime, timedelta
import jwt
import os
from werkzeug.security import generate_password_hash, check_password_hash
from server.models import db, User
from server.services.email_service import EmailService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
email_service = EmailService()

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Register a new user and send verification email"""
    try:
        data = request.get_json()
        logger.info(f"Signup attempt for email: {data.get('email')}")
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            logger.warning(f"Email already registered: {data['email']}")
            return jsonify({'error': 'Email already registered'}), 400
        
        # Generate verification token
        verification_token = str(uuid.uuid4())
        logger.info(f"Generated verification token: {verification_token}")
        
        # Check if it's a Binghamton email
        is_binghamton_email = data['email'].endswith('@binghamton.edu')
        
        # Create a new user - auto-verify Binghamton emails
        new_user = User(
            email=data['email'],
            password=generate_password_hash(data['password']),
            verification_token=None if is_binghamton_email else verification_token,
            is_verified=is_binghamton_email,  # Auto-verify Binghamton emails
            verified_at=datetime.utcnow() if is_binghamton_email else None
        )
        
        logger.info(f"Adding new user to database: {data['email']}")
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"User saved to database with ID: {new_user.id}")
        
        response_message = "User registered successfully."
        
        # Only send verification email for non-Binghamton emails
        if is_binghamton_email:
            logger.info(f"Binghamton email detected. Auto-verifying: {data['email']}")
            email_sent = True  # Not actually sending, but set to true for response consistency
            response_message += " Your Binghamton email has been automatically verified. You can now log in."
        else:
            # Send verification email
            logger.info(f"Attempting to send verification email to: {data['email']}")
            email_sent = email_service.send_verification_email(data['email'], verification_token)
            response_message += " Please verify your email."
        
        if email_sent:
            logger.info(f"Verification email sent successfully to: {data['email']}")
        else:
            logger.error(f"Failed to send verification email to: {data['email']}")
        
        return jsonify({
            'message': response_message,
            'email_sent': email_sent,
            'is_verified': is_binghamton_email
        }), 201
    except Exception as e:
        logger.error(f"Error in signup: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred during signup: {str(e)}'}), 500


@auth_bp.route('/verify', methods=['GET'])
def verify_email():
    """Verify a user's email address using the token"""
    try:
        token = request.args.get('token')
        logger.info(f"Email verification attempt with token: {token}")
        
        if not token:
            logger.warning("Verification attempt without token")
            return jsonify({'error': 'Verification token is required'}), 400
        
        # Find user with this token
        user = User.query.filter_by(verification_token=token).first()
        
        if not user:
            logger.warning(f"Invalid verification token: {token}")
            return jsonify({'error': 'Invalid verification token'}), 400
        
        logger.info(f"Valid token for user: {user.email}")
        
        # Update user as verified
        user.is_verified = True
        user.verification_token = None  # Clear the token after use
        user.verified_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"User verified successfully: {user.email}")
        
        return jsonify({'message': 'Email verified successfully. You can now log in.'}), 200
    except Exception as e:
        logger.error(f"Error in verify_email: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred during verification: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Log in a user and return a JWT token"""
    try:
        data = request.get_json()
        logger.info(f"Login attempt for email: {data.get('email')}")
        
        user = User.query.filter_by(email=data['email']).first()
        
        # Check if user exists and password is correct
        if not user or not check_password_hash(user.password, data['password']):
            logger.warning(f"Invalid login credentials for: {data.get('email')}")
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check if user is verified - temporarily disable this check
        if not user.is_verified:
            logger.warning(f"Unverified user login attempt: {user.email}")
            
            # Auto-verify Binghamton emails on login attempt
            if user.email.endswith('@binghamton.edu'):
                logger.info(f"Auto-verifying Binghamton email on login: {user.email}")
                user.is_verified = True
                user.verified_at = datetime.utcnow()
                db.session.commit()
            else:
                # Only enforce verification for non-Binghamton emails
                return jsonify({'error': 'Please verify your email before logging in'}), 401
        
        logger.info(f"Successful login for user: {user.email}")
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=1)
        }, os.getenv('JWT_SECRET_KEY', 'development-key'))
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user_id': user.id,
            'email': user.email
        }), 200
    except Exception as e:
        logger.error(f"Error in login: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred during login: {str(e)}'}), 500


@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification email to user"""
    try:
        data = request.get_json()
        logger.info(f"Resend verification request for: {data.get('email')}")
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user:
            # Don't reveal if email exists for security
            logger.info(f"Resend request for non-existent email: {data.get('email')}")
            return jsonify({'message': 'If your email is registered, a verification link will be sent'}), 200
        
        # Auto-verify Binghamton emails
        if user.email.endswith('@binghamton.edu'):
            logger.info(f"Auto-verifying Binghamton email: {user.email}")
            user.is_verified = True
            user.verification_token = None
            user.verified_at = datetime.utcnow()
            db.session.commit()
            return jsonify({'message': 'Your Binghamton email has been automatically verified. You can now log in.'}), 200
        
        if user.is_verified:
            logger.info(f"Resend request for already verified user: {user.email}")
            return jsonify({'message': 'Your email is already verified'}), 200
        
        # Generate new verification token if needed
        if not user.verification_token:
            user.verification_token = str(uuid.uuid4())
            db.session.commit()
            logger.info(f"Generated new verification token for user: {user.email}")
        
        # Send verification email
        logger.info(f"Attempting to resend verification email to: {user.email}")
        email_sent = email_service.send_verification_email(user.email, user.verification_token)
        
        if email_sent:
            logger.info(f"Verification email resent successfully to: {user.email}")
        else:
            logger.error(f"Failed to resend verification email to: {user.email}")
        
        return jsonify({
            'message': 'Verification email sent',
            'email_sent': email_sent
        }), 200
    except Exception as e:
        logger.error(f"Error in resend_verification: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred while resending verification: {str(e)}'}), 500


# Add a manual verification endpoint for testing/debugging
@auth_bp.route('/manual-verify', methods=['POST'])
def manual_verify():
    """Manually verify a user by email (development only)"""
    if os.getenv('FLASK_ENV') != 'development':
        return jsonify({'error': 'This endpoint is only available in development mode'}), 403
        
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
            
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        user.is_verified = True
        user.verification_token = None
        user.verified_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"User manually verified: {email}")
        
        return jsonify({'message': f'User {email} has been manually verified'}), 200
    except Exception as e:
        logger.error(f"Error in manual verification: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500 