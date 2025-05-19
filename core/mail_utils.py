import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Load email configuration from environment variables or config file
# For now, using placeholders, will integrate with config.py later
SMTP_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your_gmail_address@gmail.com') # Replace with actual config
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your_gmail_password') # Replace with actual config
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'Calimara Platform <noreply@calimara.ro>') # Replace with actual config

def send_email(to_address, subject, html_content):
    """
    Sends an email using the configured SMTP server.

    Args:
        to_address: The recipient's email address.
        subject: The subject of the email.
        html_content: The HTML content of the email body.
    """
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("Email sending is not configured. Skipping email.")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = MAIL_DEFAULT_SENDER
    message["To"] = to_address

    # Create the HTML part of the email
    part_html = MIMEText(html_content, "html")
    message.attach(part_html)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_DEFAULT_SENDER, to_address, message.as_string())
        server.quit()
        print(f"Email sent successfully to {to_address}")
    except Exception as e:
        print(f"Failed to send email to {to_address}: {e}")
