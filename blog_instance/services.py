import sqlite3
from datetime import datetime
from werkzeug.security import check_password_hash
# from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user # Import when implementing login
from flask import current_app # Import current_app to access config
from . import db # Import local db module
from core.mail_utils import send_email
from platform_management.db import add_post_to_shared_index # Import from platform management db
from core.db_utils import execute_query # Import execute_query from core
from config import Config # Import Config

# Placeholder for Flask-Login setup (will be done in app.py)
# login_manager = LoginManager()
# login_manager.login_view = 'blog.login' # The view function for the login route
# login_manager.login_message_category = 'info'

# Placeholder User class (will be properly implemented later)
# class User(UserMixin):
#     def __init__(self, id):
#         self.id = id
#         self.username = None # Load from DB
#         self.email = None # Load from DB
#         self.blog_title = None # Load from DB

#     def load_from_db(self, db_path):
#         user_data = db.get_user_by_id(db_path, self.id)
#         if user_data:
#             self.username = user_data['username']
#             self.email = user_data['email']
#             self.blog_title = user_data['blog_title']
#             return True
#         return False

# @login_manager.user_loader
# def load_user(user_id):
#     # This function needs access to the current instance DB path (g.instance_db_path)
#     # This is tricky with Flask-Login's user_loader which runs outside the request context
#     # A common pattern is to store the subdomain in the session or the user ID itself
#     # For now, returning None as a placeholder
#     return None


def create_post(db_path, user_id, title, content, tags_string):
    """Creates a new post, generates slug, and adds to shared index."""
    # Generate slug (can refine this for uniqueness if needed)
    slug = generate_slug_from_title(title) # Use a local helper or form method

    # Create post in instance DB
    post_id = db.create_post(db_path, user_id, title, slug, content)

    if post_id:
        # Handle tags
        tag_names = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
        tag_ids = []
        for tag_name in tag_names:
            tag_slug = generate_slug_from_title(tag_name) # Generate slug for tag
            tag_id = db.create_tag(db_path, tag_name, tag_slug)
            tag_ids.append(tag_id)

        if tag_ids:
            db.add_post_tags(db_path, post_id, tag_ids)

        # Add post to main database shared index
        # Need the full post link - requires knowing the subdomain and base domain
        # This info is available in g during the request context
        # For now, using placeholders, will need to pass subdomain/base_domain
        # from the route handler
        post_link = f"http://{subdomain}.{base_domain}/posts/{slug}"
        add_post_to_shared_index(post_id, subdomain, title, datetime.now(), post_link)

    return post_id

def get_post_by_slug(db_path, slug):
    """Retrieves a post by its slug and increments view count."""
    post = db.get_post_by_slug(db_path, slug)
    if post:
        db.increment_post_view_count(db_path, post['id'])
    return post

def update_post(db_path, post_id, title, content, tags_string):
    """Updates an existing post and its tags."""
    # Generate new slug (optional, could keep old one or regenerate)
    slug = generate_slug_from_title(title) # Decide if slug should change on edit

    db.update_post(db_path, post_id, title, slug, content)

    # Update tags (simple approach: remove all existing tags and add new ones)
    # More complex logic might involve comparing and adding/removing
    execute_query(db_path, "DELETE FROM post_tags WHERE post_id = ?", (post_id,), commit=True)
    tag_names = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
    tag_ids = []
    for tag_name in tag_names:
        tag_slug = generate_slug_from_title(tag_name)
        tag_id = db.create_tag(db_path, tag_name, tag_slug)
        tag_ids.append(tag_id)

    if tag_ids:
        db.add_post_tags(db_path, post_id, tag_ids)

def delete_post(db_path, post_id, subdomain):
    """Deletes a post and associated data (comments, likes, tags) and removes from shared index."""
    # Due to CASCADE DELETE in schema, deleting the post should handle comments, likes, post_tags
    db.delete_post(db_path, post_id)

    # Remove from main.db.shared_posts_index
    main_db_path = os.path.join(Config.MAIN_DB_DIRECTORY, 'main.db')
    query = """
    DELETE FROM shared_posts_index
    WHERE original_post_id_on_instance = ? AND blog_instance_subdomain = ?
    """
    args = (post_id, subdomain)
    execute_query(main_db_path, query, args, commit=True)

def add_comment(db_path, post_id, commenter_name, commenter_email, content):
    """Adds a new comment (initially unapproved)."""
    return db.add_comment(db_path, post_id, commenter_name, commenter_email, content)

def approve_comment(db_path, comment_id, approved_by_user_id):
    """Approves a pending comment."""
    db.approve_comment(db_path, comment_id, approved_by_user_id)
    # TODO: Send notification to commenter if email provided?

def delete_comment(db_path, comment_id):
    """Deletes a comment."""
    db.delete_comment(db_path, comment_id)

def add_like(db_path, post_id, liker_identifier):
    """Adds a like to a post."""
    db.add_like(db_path, post_id, liker_identifier)
    # Note: Like count is calculated via query, not stored directly on post

def authenticate_user(db_path, email, password):
    """Authenticates a blog owner user."""
    user = db.get_user_by_email(db_path, email)
    if user and check_password_hash(user['password_hash'], password):
        # Return user ID or a user object suitable for Flask-Login
        return user['id'] # Return user ID for now
    return None

# Helper function for slug generation (can be moved to a utils file if needed)
def generate_slug_from_title(title):
    """Generates a URL-friendly slug from a string."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

# Add other blog instance service functions as needed (e.g., getting posts with stats)
def get_posts_with_stats(db_path):
    """Retrieves posts with view and pending comment counts for admin dashboard."""
    return db.get_posts_with_stats(db_path)

def get_pending_comments(db_path):
    """Retrieves pending comments for the admin dashboard."""
    return db.get_pending_comments(db_path)
