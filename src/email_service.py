# src/email_service.py
# Send captured BracketClick photo to user's email (GDG AI Committee - Project 01)
import smtplib
import os
from email.message import EmailMessage
from email.utils import formataddr

from src import config


def send_photo_email(recipient_email: str, photo_path: str) -> bool:
    """
    Send captured photo to user's email.

    Args:
        recipient_email: User's email address
        photo_path: Absolute path to the captured photo file

    Returns:
        True if sent successfully, False otherwise
    """
    if not getattr(config, 'EMAIL_ENABLED', False):
        print("[INFO] Email sending is disabled in config")
        return False

    try:
        msg = EmailMessage()
        msg['Subject'] = config.EMAIL_SUBJECT
        msg['From'] = formataddr(('GDG AI Committee', config.EMAIL_ADDRESS))
        msg['To'] = recipient_email

        html_body = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                .header {
                    background: linear-gradient(135deg, #4285F4, #34A853);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }
                .header h1 {
                    margin: 0;
                    font-size: 28px;
                }
                .content {
                    padding: 30px 20px;
                    color: #333;
                }
                .content p {
                    line-height: 1.6;
                    margin: 15px 0;
                }
                .photo-info {
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                .footer {
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                }
                .gdg-logo {
                    font-size: 48px;
                    margin-bottom: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="gdg-logo">📸</div>
                    <h1>Your BracketClick Photo!</h1>
                </div>
                <div class="content">
                    <p>Hi there!</p>
                    <p>Thank you for participating in our <strong>GDG workshop</strong>!</p>
                    <p>Your photo has been captured using the BracketClick photo booth. Find it attached to this email.</p>
                    <div class="photo-info">
                        <strong>📷 Photo Details:</strong><br>
                        Captured at: GDG Workshop 2025-2026<br>
                        Project: BracketClick by GDG AI Committee
                    </div>
                    <p>We hope you enjoyed the experience! Feel free to share your photo on social media and tag us.</p>
                    <p><strong>GDG AI Committee</strong><br>
                    <em>Capture the moment, one bracket at a time</em> 🎯</p>
                </div>
                <div class="footer">
                    <p>© 2025-2026 GDG AI Committee | BracketClick Project #01</p>
                    <p>This is an automated message from our photo booth system.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.set_content(
            "Thank you for participating in our GDG workshop! Your photo is attached."
        )
        msg.add_alternative(html_body, subtype='html')

        photo_filename = os.path.basename(photo_path)
        with open(photo_path, 'rb') as f:
            photo_data = f.read()
        msg.add_attachment(
            photo_data,
            maintype='image',
            subtype='jpeg',
            filename=photo_filename
        )

        print(f"[EMAIL] Connecting to {config.EMAIL_SERVER}:{config.EMAIL_PORT}...")
        with smtplib.SMTP(config.EMAIL_SERVER, config.EMAIL_PORT) as server:
            if config.EMAIL_USE_TLS:
                server.starttls()
            server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"[OK] Email sent successfully to {recipient_email}")
        print(f"[OK] Attachment: {photo_filename}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("[ERROR] Email authentication failed!")
        print("[ERROR] Check EMAIL_ADDRESS and EMAIL_PASSWORD (use .env or env vars)")
        print("[ERROR] For Gmail: use App Password, not regular password")
        print("[ERROR] Get it from: https://myaccount.google.com/apppasswords")
        return False
    except smtplib.SMTPException as e:
        print(f"[ERROR] SMTP error while sending email: {e}")
        return False
    except FileNotFoundError:
        print(f"[ERROR] Photo file not found: {photo_path}")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_connection() -> bool:
    """
    Test email server connection and credentials.

    Returns:
        True if connection successful
    """
    try:
        print(f"[TEST] Testing email connection to {config.EMAIL_SERVER}...")
        with smtplib.SMTP(config.EMAIL_SERVER, config.EMAIL_PORT) as server:
            if config.EMAIL_USE_TLS:
                server.starttls()
            server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        print("[OK] Email connection successful!")
        return True
    except Exception as e:
        print(f"[ERROR] Email connection failed: {e}")
        return False
