import os
from flask import Flask, render_template, request, g, redirect, url_for, session
from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from jinja2 import Environment # Import Environment

# Load environment variables from .env file
load_dotenv()

# Import core utilities
from core.db_utils import get_db_connection, execute_query, init_db_from_schema

# Import configuration
from config import Config

# Import blueprints
from platform_management.routes import platform_bp
from blog_instance.routes import blog_bp

# Flask-Login User class
class User(UserMixin):
    def __init__(self, user_id, instance_db_path=None):
        self.id = user_id # Store user_id as self.id for Flask-Login
        self.instance_db_path = instance_db_path
        self.username = None
        self.email = None
        self.blog_title = None
        # Attempt to load user data upon initialization if db_path is provided
        if self.instance_db_path:
            self.load_data_from_db()

    def load_data_from_db(self):
        """Loads user attributes from the instance database."""
        if not self.instance_db_path:
            print(f"Warning: Attempted to load user data for ID {self.id} without instance_db_path.")
            return False
        
        user_data = execute_query(
            self.instance_db_path,
            "SELECT username, email, blog_title FROM users WHERE id = ?",
            (self.id,),
            one=True
        )
        if user_data:
            self.username = user_data['username']
            self.email = user_data['email']
            self.blog_title = user_data['blog_title']
            return True
        else:
            print(f"Warning: No user data found for ID {self.id} in DB {self.instance_db_path}.")
            return False

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'blog.login' # The view function for the login route in blog_bp
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    instance_db_path = session.get('instance_db_path')
    if not instance_db_path:
        # This can happen if the session is cleared or user_id is from an old session
        # without instance_db_path.
        return None
        
    user = User(user_id, instance_db_path) # User data is loaded in __init__ if db_path is present
    if user.username: # Check if data was successfully loaded
        return user
    return None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    login_manager.init_app(app)

    # Ensure instance_dbs and main_db_directory exist
    # These paths are now relative to the app's root_path if not absolute
    instance_db_dir = app.config['INSTANCE_DB_DIR_PATH']
    main_db_dir = app.config['MAIN_DB_DIRECTORY']

    if not os.path.isabs(instance_db_dir):
        instance_db_dir = os.path.join(app.root_path, instance_db_dir)
    if not os.path.isabs(main_db_dir):
        main_db_dir = os.path.join(app.root_path, main_db_dir)

    os.makedirs(instance_db_dir, exist_ok=True)
    os.makedirs(main_db_dir, exist_ok=True)

    # Initialize main database if it doesn't exist
    main_db_path = os.path.join(main_db_dir, 'main.db')
    main_schema_path = os.path.join(app.root_path, 'platform_management', 'schemas', 'main_db_schema.sql')
    init_db_from_schema(main_db_path, main_schema_path)

    @app.before_request
    def load_blog_instance_context():
        g.is_blog_instance = False
        g.subdomain = None
        g.instance_db_path = None

        host_no_port = request.host.split(':')[0]  # e.g., "test.localhost" or "localhost"
        
        # Use SERVER_NAME (no port) for subdomain detection if set, otherwise BASE_DOMAIN (no port)
        # This is important for flexibility in different environments.
        # For local dev, SERVER_NAME is 'localhost:5000', so cfg_comparison_domain_no_port is 'localhost'.
        cfg_server_name_no_port = app.config.get('SERVER_NAME', '').split(':')[0]
        cfg_base_domain_no_port = app.config.get('BASE_DOMAIN', '').split(':')[0]
        
        comparison_domain_no_port = cfg_server_name_no_port or cfg_base_domain_no_port
        
        if not comparison_domain_no_port: # Should not happen if config is sane
            return

        if host_no_port != comparison_domain_no_port and host_no_port.endswith("." + comparison_domain_no_port):
            subdomain_candidate = host_no_port[:-len("." + comparison_domain_no_port)]
            
            # A valid subdomain should not contain further dots (e.g., 'www' or 'user1')
            # and should not be 'www' if 'www.domain.com' should be treated as main domain.
            if subdomain_candidate and '.' not in subdomain_candidate and subdomain_candidate.lower() != 'www':
                g.is_blog_instance = True
                g.subdomain = subdomain_candidate

                instance_db_dir_path = app.config['INSTANCE_DB_DIR_PATH']
                if not os.path.isabs(instance_db_dir_path):
                    instance_db_dir_path = os.path.join(app.root_path, instance_db_dir_path)
                g.instance_db_path = os.path.join(instance_db_dir_path, f'{subdomain}.db')

                # Check if the blog instance actually exists in main.db
                current_main_db_dir = app.config['MAIN_DB_DIRECTORY']
                if not os.path.isabs(current_main_db_dir):
                    current_main_db_dir = os.path.join(app.root_path, current_main_db_dir)
                current_main_db_path = os.path.join(current_main_db_dir, 'main.db')

                blog_exists = execute_query(
                    current_main_db_path,
                    "SELECT 1 FROM blogs WHERE subdomain_name = ?",
                    (subdomain,),
                    one=True
                )
                if not blog_exists or not os.path.exists(g.instance_db_path):
                    g.is_blog_instance = False
                    g.subdomain = None
                    g.instance_db_path = None
                    # Optionally redirect to a "blog not found" page or main platform
            else: # Not a recognized subdomain format
                g.is_blog_instance = False
                g.subdomain = None
                g.instance_db_path = None
        else: # Not a subdomain, treat as main platform
             g.is_blog_instance = False
             g.subdomain = None
             g.instance_db_path = None


        # Load 10 random posts from other blogs for the sidebar (for all pages)
        g.random_posts = []
        # Only load random posts if not on a blog instance (to avoid extra DB calls)
        # or if you want random posts on blog instances too, remove the condition
        if not g.is_blog_instance:
            current_main_db_dir = app.config['MAIN_DB_DIRECTORY']
            if not os.path.isabs(current_main_db_dir):
                current_main_db_dir = os.path.join(app.root_path, current_main_db_dir)
            current_main_db_path = os.path.join(current_main_db_dir, 'main.db')

            try:
                one_month_ago = datetime.now() - timedelta(days=30)
                g.random_posts = execute_query(
                    current_main_db_path,
                    """
                    SELECT post_title, post_link, blog_instance_subdomain
                    FROM shared_posts_index
                    WHERE post_creation_date >= ?
                    ORDER BY RANDOM()
                    LIMIT 10
                    """,
                    (one_month_ago.strftime('%Y-%m-%d %H:%M:%S'),),
                    many=True
                )
            except Exception as e:
                print(f"Error loading random posts: {e}")
                g.random_posts = []

    app.register_blueprint(platform_bp)
    app.register_blueprint(blog_bp, url_prefix='/<subdomain>') # Add subdomain to blog_bp routes

    # Add moment to the Jinja2 environment globals
    # This requires the 'moment' library to be installed and available
    # If you are using a Python library for moment.js integration (like Flask-Moment),
    # you would initialize it here. Assuming a simple case where 'moment' is a function
    # or object you want to expose to templates.
    # If you are using client-side Moment.js, you might not need this,
    # but the template is trying to use it server-side.
    # Let's assume you intend to use a Python library like 'arrow' or 'pendulum'
    # and expose a formatting function, or you have a custom 'moment' object.
    # For now, let's pass the current time and assume a 'moment' filter or global
    # will be added later if a specific library is used.
    # A common pattern is to use Flask-Moment, which requires initialization.
    # If Flask-Moment is intended, it needs to be installed and initialized.
    # Let's assume for now that 'moment' is expected to be a global function
    # or filter provided by a library like Flask-Moment.
    # If Flask-Moment is not used, the template logic needs to be adjusted.
    # Given the error, it's likely Flask-Moment is intended but not initialized.
    # Let's add a placeholder for Flask-Moment initialization and pass current_time.

    # from flask_moment import Moment # Assuming Flask-Moment is intended
    # moment = Moment(app) # Initialize Flask-Moment

    # If Flask-Moment is not used, you might need a custom filter or global
    # def format_datetime(value, format='%Y-%m-%d'):
    #     return value.strftime(format)
    # app.jinja_env.filters['datetime'] = format_datetime

    # For the 'moment' object specifically, it strongly suggests Flask-Moment.
    # Let's add Flask-Moment initialization. First, ensure it's in requirements.txt.
    # (We already checked requirements.txt, Flask-Moment is not there, but Flask-Login is)
    # This means the template is likely using a client-side Moment.js but the Jinja
    # syntax is trying to call a server-side 'moment' object.
    # The template line `{{ moment(current_time).format('YYYY') }}` looks like
    # Flask-Moment syntax. Let's add Flask-Moment to requirements and initialize it.

    # Initialize Flask-Moment
    from flask_moment import Moment
    moment_instance = Moment(app)

    @app.context_processor
    def inject_current_time():
        """Injects the current time into all templates."""
        return {'current_time': datetime.utcnow()}

    @app.route('/')
    def main_index_route():
        # This route will only be hit if no subdomain matches or if it's the base domain
        if g.is_blog_instance and g.subdomain:
            # This case should ideally be handled by the blog_bp's index route
            # but as a fallback or if blog_bp isn't matched directly for root of subdomain:
            return redirect(url_for('blog.index', subdomain=g.subdomain))
        else:
            # current_time is now available globally via context processor
            return render_template('platform/index.html', random_posts=g.random_posts)

    return app

if __name__ == '__main__':
    app = create_app()
    # For local testing with subdomains (e.g., test.localhost),
    # you need to set SERVER_NAME in your .env or config.py
    # and add entries to your hosts file:
    # 127.0.0.1 localhost
    # 127.0.0.1 test.localhost
    # 127.0.0.1 another.localhost
    # app.config['SERVER_NAME'] = 'localhost:5000' # Example for development
    app.run(debug=True, host='0.0.0.0') # host='0.0.0.0' to be accessible on network
