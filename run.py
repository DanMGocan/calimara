# ABANDONED PROJECT #

from app import create_app
from config import Config
import os

app = create_app(Config)

if __name__ == '__main__':
    # For local testing with subdomains (e.g., test.localhost),
    # you need to set SERVER_NAME in your .env or config.py
    # and add entries to your hosts file:
    # Example for hosts file:
    # 127.0.0.1 localhost
    # 127.0.0.1 calimara.ro # Your base domain
    # 127.0.0.1 test.calimara.ro
    # 127.0.0.1 another.calimara.ro
    
    # For local development, don't set SERVER_NAME to avoid routing issues
    # app.config['SERVER_NAME'] = os.environ.get('SERVER_NAME', 'localhost:5000')
    
    # Use 0.0.0.0 to make the app accessible on your local network
    # Use a specific port, e.g., 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
