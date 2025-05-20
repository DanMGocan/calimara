import os
from flask import Flask, render_template, request, g, redirect, url_for, session
from dotenv import load_dotenv
import mysql.connector
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from jinja2 import Environment # Import Environment

# Load environment variables from .env file
load_dotenv()

# Import core utilities
from core.db_utils import get_db_connection, execute_query, init_db_from_schema

# Import configuration
from config import Config
from flask_wtf.csrf import CSRFProtect # Import CSRFProtect

# Import blueprints
from platform_management.routes import platform_bp
from platform_management.db import get_random_blogs # Import for random blogs list
from blog_instance.routes import blog_bp
from models import User # Import User from models.py

# Initialize Flask-Login
login_manager = LoginManager()
csrf = CSRFProtect() # Create CSRFProtect instance
login_manager.login_view = 'platform.login' # Updated to global platform login
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    # instance_db_path is no longer stored in session or needed here
    # User data is always loaded from the main database.
    user = User(user_id) 
    if user.username: # Check if data was successfully loaded (username is a required field)
        return user
    return None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    login_manager.init_app(app)
    csrf.init_app(app) # Initialize CSRFProtect with the app

    # Database initialization is now handled by manually running initdb.py
    # The following block has been removed:
    # # Initialize main database if it doesn't exist using the comprehensive mysql_schema.sql
    # comprehensive_schema_path = os.path.join(app.root_path, 'mysql_schema.sql') # Points to the root schema file
    # if os.path.exists(comprehensive_schema_path):
    #     init_db_from_schema(os.getenv('MYSQL_DATABASE', 'calimara_db'), comprehensive_schema_path)
    # else:
    #     print(f"WARNING: Comprehensive schema file not found at {comprehensive_schema_path}. Database might not be fully initialized by the app.")

    @app.before_request
    def load_blog_instance_context():
        print(f"[DEBUG] app.py - load_blog_instance_context: Request host: {request.host}")
        g.is_blog_instance = False
        g.subdomain = None
        g.blog_id = None # Will store the ID of the current blog instance
        g.db_name = os.getenv('MYSQL_DATABASE', 'calimara_db') # Main database for all operations

        host_no_port = request.host.split(':')[0]  # e.g., "test.localhost" or "localhost"
        print(f"[DEBUG] app.py - load_blog_instance_context: host_no_port: {host_no_port}")
        
        # Use SERVER_NAME (no port) for subdomain detection if set, otherwise BASE_DOMAIN (no port)
        # This is important for flexibility in different environments.
        # For local dev, SERVER_NAME is 'localhost:5000', so cfg_comparison_domain_no_port is 'localhost'.
        cfg_server_name_no_port = (app.config.get('SERVER_NAME') or '').split(':')[0]
        cfg_base_domain_no_port = (app.config.get('BASE_DOMAIN') or '').split(':')[0]
        print(f"[DEBUG] app.py - load_blog_instance_context: cfg_server_name_no_port: {cfg_server_name_no_port}, cfg_base_domain_no_port: {cfg_base_domain_no_port}")
        
        comparison_domain_no_port = cfg_server_name_no_port or cfg_base_domain_no_port
        print(f"[DEBUG] app.py - load_blog_instance_context: comparison_domain_no_port: {comparison_domain_no_port}")
        
        if not comparison_domain_no_port: # Should not happen if config is sane
            print("[DEBUG] app.py - load_blog_instance_context: No comparison_domain_no_port, returning.")
            return

        if host_no_port != comparison_domain_no_port and host_no_port.endswith("." + comparison_domain_no_port):
            subdomain_candidate = host_no_port[:-len("." + comparison_domain_no_port)]
            print(f"[DEBUG] app.py - load_blog_instance_context: subdomain_candidate: {subdomain_candidate}")
            
            # A valid subdomain should not contain further dots (e.g., 'www' or 'user1')
            # and should not be 'www' if 'www.domain.com' should be treated as main domain.
            if subdomain_candidate and '.' not in subdomain_candidate and subdomain_candidate.lower() != 'www':
                
                # Check if the blog instance actually exists in main database
                print(f"[DEBUG] app.py - load_blog_instance_context: Checking existence for subdomain: {subdomain_candidate}")
                # Fetch the blog record to get its ID and owner_user_id
                blog_record = execute_query(
                    g.db_name, # Use the main database name
                    "SELECT id, subdomain_name, owner_user_id FROM blogs WHERE subdomain_name = %s", # Added owner_user_id
                    (subdomain_candidate,),
                    one=True
                )
                print(f"[DEBUG] app.py - load_blog_instance_context: blog_record query result: {blog_record}")
                
                if blog_record:
                    g.is_blog_instance = True
                    g.subdomain = blog_record['subdomain_name']
                    g.blog_id = blog_record['id'] 
                    g.blog_owner_id = blog_record['owner_user_id'] # Store the blog owner's ID
                    print(f"[DEBUG] app.py - load_blog_instance_context: Blog instance FOUND. g.subdomain: {g.subdomain}, g.blog_id: {g.blog_id}, g.blog_owner_id: {g.blog_owner_id}")
                else:
                    # Blog does not exist
                    print(f"[DEBUG] app.py - load_blog_instance_context: Blog instance NOT FOUND for {subdomain_candidate}.")
                    g.is_blog_instance = False
                    g.subdomain = None
                    g.blog_id = None 
                    g.blog_owner_id = None
            else: # Not a recognized subdomain format or 'www'
                print(f"[DEBUG] app.py - load_blog_instance_context: Invalid subdomain format or 'www': {subdomain_candidate}")
                g.is_blog_instance = False
                g.subdomain = None
                g.blog_id = None
                g.blog_owner_id = None
        else: # Not a subdomain, treat as main platform
             print(f"[DEBUG] app.py - load_blog_instance_context: Not a subdomain or host matches comparison domain. host_no_port: {host_no_port}")
             g.is_blog_instance = False
             g.subdomain = None
             g.blog_id = None
             g.blog_owner_id = None


        # Load 10 random posts from other blogs for the sidebar (for all pages)
        g.random_posts = []
        # Load 10 random posts for the sidebar (for all pages, including blog instances)
        try:
            one_month_ago = datetime.now() - timedelta(days=30)
            g.random_posts = execute_query(
                os.getenv('MYSQL_DATABASE', 'calimara_db'),
                """
                SELECT post_title, post_link, blog_instance_subdomain
                FROM shared_posts_index
                WHERE post_creation_date >= %s
                ORDER BY RAND()
                LIMIT 10
                """,
                (one_month_ago.strftime('%Y-%m-%d %H:%M:%S'),),
                many=True
            )
            print(f"[DEBUG] app.py - load_blog_instance_context: Loaded {len(g.random_posts)} random posts.")
        except Exception as e:
            print(f"Error loading random posts: {e}")
            g.random_posts = []
        
        # Load 10 random blogs for the sidebar
        g.random_blogs_list = []
        try:
            g.random_blogs_list = get_random_blogs(limit=10)
            print(f"[DEBUG] app.py - load_blog_instance_context: Loaded {len(g.random_blogs_list)} random blogs.")
        except Exception as e:
            print(f"Error loading random blogs: {e}")
            g.random_blogs_list = []

        print(f"[DEBUG] app.py - load_blog_instance_context END: g.is_blog_instance: {g.is_blog_instance}, g.subdomain: {g.subdomain}, g.blog_id: {g.blog_id}, g.blog_owner_id: {g.blog_owner_id}, g.db_name: {g.db_name}")

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
        print(f"[DEBUG] app.py - main_index_route: g.is_blog_instance: {g.is_blog_instance}, g.subdomain: {g.subdomain}, current_user.is_authenticated: {current_user.is_authenticated}")

        # If the user is authenticated and on the main domain (not a blog instance)
        if not g.is_blog_instance and current_user.is_authenticated:
            # Check if this user owns any blog
            user_blog = execute_query(
                g.db_name,
                "SELECT subdomain_name FROM blogs WHERE owner_user_id = %s LIMIT 1",
                (current_user.id,),
                one=True
            )
            if user_blog:
                print(f"[DEBUG] app.py - main_index_route: Logged-in user owns blog '{user_blog['subdomain_name']}'. Redirecting to their admin dashboard.")
                # Redirect to their blog's admin dashboard
                # Note: The blog_bp is mounted at /<subdomain>, so url_for needs the subdomain.
                return redirect(url_for('blog.admin_dashboard', subdomain=user_blog['subdomain_name']))
            else:
                print("[DEBUG] app.py - main_index_route: Logged-in user does not own a blog. Showing platform index.")
                # Fall through to platform index if they don't own a blog (e.g., admin user or new user)

        # If it's a blog instance URL (e.g., dangocan.localhost:5000)
        if g.is_blog_instance and g.subdomain:
            print(f"[DEBUG] app.py - main_index_route: It's a blog instance. Fetching posts for subdomain {g.subdomain}")
            # Instead of redirecting, directly render the blog index template
            posts = execute_query(
                g.db_name,
                "SELECT * FROM posts WHERE blog_id = %s ORDER BY creation_timestamp DESC",
                (g.blog_id,),
                many=True
            )
            return render_template('blog/index.html', posts=posts, subdomain=g.subdomain, 
                                  random_posts=g.get('random_posts', []), 
                                  random_blogs_list=g.get('random_blogs_list', []))
        
        # Default: show platform index for non-blog instance URLs or if user doesn't own a blog
        print("[DEBUG] app.py - main_index_route: Rendering platform/index.html")
        return render_template('platform/index.html', random_posts=g.random_posts, random_blogs_list=g.random_blogs_list)

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
