"""
Email utility functions for sending emails
"""

import os
import smtplib
import secrets
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import url_for, current_app

# Email configuration - these would be set in environment variables in production
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@binghamtonhousing.com')
VERIFICATION_EXPIRY_HOURS = 24

def generate_verification_token():
    """Generate a random token for email verification"""
    return secrets.token_urlsafe(32)

def get_verification_expiry():
    """Get the timestamp for token expiry"""
    return datetime.datetime.now() + datetime.timedelta(hours=VERIFICATION_EXPIRY_HOURS)

def send_verification_email(email, token, is_resend=False):
    """
    Send a verification email to the user
    
    Args:
        email: The recipient's email address
        token: The verification token
        is_resend: Whether this is a resend of the verification email
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        
        # Create the verification URL
        verification_url = url_for('student.verify_email', token=token, _external=True)
        
        if is_resend:
            msg['Subject'] = "Binghamton Housing Portal - Email Verification Reminder"
            body = f"""
            <html>
            <body>
                <h2>Email Verification Reminder</h2>
                <p>You requested another verification email for your Binghamton Housing Portal account.</p>
                <p>Please verify your Binghamton University email address by clicking the link below:</p>
                <p><a href="{verification_url}">Verify My Email</a></p>
                <p>This link will expire in {VERIFICATION_EXPIRY_HOURS} hours.</p>
                <p>If you did not register for the Binghamton Housing Portal, please ignore this email.</p>
            </body>
            </html>
            """
        else:
            msg['Subject'] = "Binghamton Housing Portal - Verify Your Email"
            body = f"""
            <html>
            <body>
                <h2>Welcome to the Binghamton Housing Portal!</h2>
                <p>Thank you for registering. Please verify your Binghamton University email address by clicking the link below:</p>
                <p><a href="{verification_url}">Verify My Email</a></p>
                <p>This link will expire in {VERIFICATION_EXPIRY_HOURS} hours.</p>
                <p>If you did not register for the Binghamton Housing Portal, please ignore this email.</p>
            </body>
            </html>
            """
        
        msg.attach(MIMEText(body, 'html'))
        
        # For development/testing, just print the verification URL instead of sending email
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            print(f"[DEV MODE] Verification URL for {email}: {verification_url}")
            return True
            
        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending verification email: {str(e)}")
        return False 