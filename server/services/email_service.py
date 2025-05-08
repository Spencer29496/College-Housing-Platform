"""
Email service for sending verification emails using SendGrid
"""
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, ReplyTo, Content, To
from dotenv import load_dotenv
import re
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class EmailService:
    def __init__(self):
        """Initialize the email service with SendGrid API key from environment variables"""
        self.api_key = os.getenv('SENDGRID_API_KEY')
        if not self.api_key:
            logger.error("SENDGRID_API_KEY not found in environment variables")
        else:
            logger.info("SendGrid API key loaded successfully")
            
        # Use the email that was registered when creating the SendGrid account
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL', 'spencermines1@gmail.com')
        self.from_name = os.getenv('SENDGRID_FROM_NAME', 'Binghamton Housing Portal')
        logger.info(f"Email service initialized with from_email: {self.from_email}")

    def send_verification_email(self, to_email, verification_token):
        """
        Send a verification email to a user
        
        Args:
            to_email (str): The recipient's email
            verification_token (str): The verification token for the URL
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Additional validation for Binghamton email addresses
        if '@binghamton.edu' in to_email:
            logger.info(f"Binghamton email detected: {to_email}")
            # Check email format
            if not re.match(r'^[a-zA-Z0-9._%+-]+@binghamton\.edu$', to_email):
                logger.warning(f"Invalid Binghamton email format: {to_email}")
                return False
        
        # Generate the verification URL - ensure APP_URL ends with no trailing slash
        app_url = os.getenv('APP_URL', 'http://localhost:5000').rstrip('/')
        verification_url = f"{app_url}/api/auth/verify?token={verification_token}"
        logger.info(f"Sending verification email to {to_email} with URL: {verification_url}")
        
        # Print environment variables for debugging
        logger.info(f"Environment variables: APP_URL={os.getenv('APP_URL')}")
        
        # Add a unique message ID to help with tracking
        message_id = str(uuid.uuid4())
        
        # Create a more spam-filter-friendly email
        to_email_obj = To(to_email)
        subject = 'Verify Your Binghamton Housing Portal Account'
        
        # Plain text version first (important for academic email filters)
        plain_content = f"""
Hello from the Binghamton Housing Portal!

Please verify your email address to complete your account registration.

Verification Link: {verification_url}

If you did not create an account, please ignore this email.

Thank you,
Binghamton Housing Portal Team

--
Binghamton Housing Portal
4400 Vestal Parkway E
Binghamton, NY 13850
United States
        """
        
        # HTML version
        html_content = f'''
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Welcome to the Binghamton Housing Portal!</h2>
                    <p>Please verify your email address by clicking the link below:</p>
                    <p style="margin: 25px 0;">
                        <a href="{verification_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">Verify Email Address</a>
                    </p>
                    <p>Or copy and paste this URL into your browser:</p>
                    <p style="word-break: break-all; font-size: 14px; color: #666;">{verification_url}</p>
                    <p>If you did not create an account, please ignore this email.</p>
                    <p>Thank you,<br>Binghamton Housing Portal Team</p>
                    <hr style="border: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        Binghamton Housing Portal<br>
                        4400 Vestal Parkway E<br>
                        Binghamton, NY 13850<br>
                        United States<br>
                        Message ID: {message_id}
                    </p>
                </div>
            </body>
        </html>
        '''
        
        # Create the message with both plain text and HTML
        message = Mail(
            from_email=(self.from_email, self.from_name),
            to_emails=to_email,
            subject=subject,
            plain_text_content=plain_content,
            html_content=html_content
        )
        
        # Add custom headers to improve deliverability
        message.add_header({"X-Message-ID": message_id})
        message.add_header({"X-Entity-Ref-ID": message_id})
        
        # Specify reply-to email
        message.reply_to = ReplyTo(self.from_email, self.from_name)
        
        # Log full message details for debugging
        logger.info(f"Email message details:")
        logger.info(f"  From: {self.from_email} ({self.from_name})")
        logger.info(f"  To: {to_email}")
        logger.info(f"  Subject: {subject}")
        logger.info(f"  Message ID: {message_id}")
        
        try:
            logger.info("Attempting to send email via SendGrid API")
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            logger.info(f"Email API response: {response.status_code}")
            if hasattr(response, 'headers'):
                logger.info(f"Response headers: {response.headers}")
            if hasattr(response, 'body'):
                logger.info(f"Response body: {response.body}")
            
            if response.status_code == 202:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Email not sent. Status code: {response.status_code}")
                # Check for specific error codes
                if response.status_code == 400:
                    logger.error("Bad request - check email format and content")
                elif response.status_code == 401:
                    logger.error("Unauthorized - check API key")
                elif response.status_code == 403:
                    logger.error("Forbidden - sender may not be verified")
                return False
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}", exc_info=True)
            print(f"Error sending email: {e}")
            return False


# Example usage
if __name__ == "__main__":
    email_service = EmailService()
    recipient = input("Enter email address to test: ")
    if not recipient:
        recipient = "test@example.com"
    success = email_service.send_verification_email(recipient, "test-verification-token")
    print(f"Email sent: {success}") 