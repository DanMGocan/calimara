import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_replace_me') # Replace with a strong, random key
    BASE_DOMAIN = os.environ.get('BASE_DOMAIN', 'calimara.ro') # Replace with your actual base domain

    # MySQL Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'dangocan')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'QuietUptown1801__')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'calimara_db')

    # Email Configuration (for Gmail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your_gmail_address@gmail.com') # Replace with your Gmail address
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your_gmail_password') # Replace with your Gmail password or app password
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'Calimara Platform <noreply@calimara.ro>') # Replace with your desired sender name and email

    # Server Name for subdomain handling (important for development)
    # In production, this is usually handled by the web server (Nginx)
    # For local testing with subdomains, you might need to set this and
    # add entries to your hosts file (e.g., 127.0.0.1 test.calimara.ro)
    SERVER_NAME = os.environ.get('SERVER_NAME', None) # Set this in your .env for local testing, e.g., 'localhost:5000'
