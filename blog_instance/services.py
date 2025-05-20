import mysql.connector
import re
import os
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


def create_post(db_name, blog_id, user_id, title, content, tags_string, subdomain, base_domain_config): # Added subdomain, base_domain_config
    """Creates a new post, generates slug, and adds to shared index."""
    slug = generate_slug_from_title(title)

    # Create post in the main DB, scoped by blog_id
    post_id = db.create_post(db_name, blog_id, user_id, title, slug, content)

    if post_id:
        tag_names = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
        tag_ids = []
        for tag_name in tag_names:
            tag_slug = generate_slug_from_title(tag_name)
            tag_id = db.create_tag(db_name, tag_name, tag_slug) # Tags are global
            tag_ids.append(tag_id)

        if tag_ids:
            db.add_post_tags(db_name, post_id, tag_ids)

        # Add post to main database shared index
        post_link = f"http://{subdomain}.{base_domain_config.split(':')[0]}/posts/{slug}" # Use base_domain_config
        # add_post_to_shared_index is defined in platform_management.db and uses MAIN_DB_NAME internally
        add_post_to_shared_index(post_id, subdomain, title, datetime.now(), post_link)

    return post_id

def get_post_by_slug(db_name, blog_id, slug): # Added blog_id
    """Retrieves a post by its slug for a specific blog and increments view count."""
    post = db.get_post_by_slug(db_name, blog_id, slug)
    if post:
        db.increment_post_view_count(db_name, post['id']) # post_id is global for increment
    return post

def update_post(db_name, blog_id, post_id, title, content, tags_string): # Added blog_id
    """Updates an existing post and its tags for a specific blog."""
    slug = generate_slug_from_title(title)

    db.update_post(db_name, blog_id, post_id, title, slug, content)

    # Update tags
    main_db_name = os.getenv('MYSQL_DATABASE', 'calimara_db') # Assuming tags are global, use main_db_name
    execute_query(main_db_name, "DELETE FROM post_tags WHERE post_id = %s", (post_id,), commit=True)
    tag_names = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
    tag_ids = []
    for tag_name in tag_names:
        tag_slug = generate_slug_from_title(tag_name)
        tag_id = db.create_tag(main_db_name, tag_name, tag_slug) # Use main_db_name for global tags
        tag_ids.append(tag_id)

    if tag_ids:
        db.add_post_tags(main_db_name, post_id, tag_ids) # Use main_db_name for global post_tags

def delete_post(db_name, blog_id, post_id, subdomain): # Added blog_id
    """Deletes a post for a specific blog and removes from shared index."""
    db.delete_post(db_name, blog_id, post_id)

    # Remove from main database shared_posts_index
    # add_post_to_shared_index and related logic in platform_management.db already use main_db_name
    main_db_name_for_index = os.getenv('MYSQL_DATABASE', 'calimara_db')
    query_index = """
    DELETE FROM shared_posts_index
    WHERE original_post_id_on_instance = %s AND blog_instance_subdomain = %s
    """
    args_index = (post_id, subdomain)
    execute_query(main_db_name_for_index, query_index, args_index, commit=True)


def add_comment(db_name, post_id, commenter_name, commenter_email, content): # db_name is main DB
    """Adds a new comment (initially unapproved)."""
    return db.add_comment(db_name, post_id, commenter_name, commenter_email, content)

def approve_comment(db_name, blog_id, comment_id, approved_by_user_id): # Added blog_id for context
    """Approves a pending comment for a specific blog."""
    # Potentially add a check here: does comment_id belong to a post in blog_id?
    db.approve_comment(db_name, comment_id, approved_by_user_id)

def delete_comment(db_name, blog_id, comment_id): # Added blog_id for context
    """Deletes a comment for a specific blog."""
    # Potentially add a check here
    db.delete_comment(db_name, comment_id)

def add_like(db_name, post_id, liker_identifier): # db_name is main DB
    """Adds a like to a post."""
    db.add_like(db_name, post_id, liker_identifier)

def authenticate_user(db_name, email, password): # db_name is main DB
    """Authenticates a user from the global users table."""
    print(f"[AUTH_DEBUG] Attempting to authenticate user: {email}")
    user = db.get_user_by_email(db_name, email) # Uses global user table
    if user:
        print(f"[AUTH_DEBUG] User found: {user['id']}, Email: {user['email']}")
        print(f"[AUTH_DEBUG] DB Password Hash: {user['password_hash']}")
        print(f"[AUTH_DEBUG] Password provided for check: {password}")
        password_match = check_password_hash(user['password_hash'], password)
        print(f"[AUTH_DEBUG] Password match result: {password_match}")
        if password_match:
            print(f"[AUTH_DEBUG] Authentication successful for user ID: {user['id']}")
            return user['id']
        else:
            print(f"[AUTH_DEBUG] Password mismatch for user: {email}")
    else:
        print(f"[AUTH_DEBUG] User not found: {email}")
    return None

# Helper function for slug generation
def generate_slug_from_title(title):
    """Generates a URL-friendly slug from a string."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug) # Remove non-alphanumeric chars except space and hyphen
    slug = re.sub(r'\s+', '-', slug)       # Replace spaces with hyphens
    slug = re.sub(r'-+', '-', slug)        # Replace multiple hyphens with single
    return slug.strip('-')

def get_posts_with_stats(db_name, blog_id): # Added blog_id
    """Retrieves posts for a specific blog with view and pending comment counts."""
    return db.get_posts_with_stats(db_name, blog_id)

def get_pending_comments(db_name, blog_id): # Added blog_id
    """Retrieves pending comments for a specific blog."""
    return db.get_pending_comments(db_name, blog_id)
