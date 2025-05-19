import sqlite3
import os
from core.db_utils import execute_query, get_db_connection
from config import Config

MAIN_DB_PATH = os.path.join(Config.MAIN_DB_DIRECTORY, 'main.db')

def add_blog_instance_record(subdomain_name, blog_title, owner_user_id, owner_email, stripe_customer_id=None, stripe_subscription_id=None, trial_ends_at=None):
    """Adds a new blog instance record to the main database."""
    query = """
    INSERT INTO blogs (subdomain_name, blog_title, owner_user_id, owner_email, stripe_customer_id, stripe_subscription_id, trial_ends_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    args = (subdomain_name, blog_title, owner_user_id, owner_email, stripe_customer_id, stripe_subscription_id, trial_ends_at)
    execute_query(MAIN_DB_PATH, query, args, commit=True)

def get_blog_by_subdomain(subdomain_name):
    """Retrieves a blog record from the main database by subdomain."""
    query = "SELECT * FROM blogs WHERE subdomain_name = ?"
    args = (subdomain_name,)
    return execute_query(MAIN_DB_PATH, query, args, one=True)

def update_subscription_status(subdomain_name, status, stripe_subscription_id=None, last_payment_date=None):
    """Updates the subscription status of a blog instance."""
    query = """
    UPDATE blogs
    SET subscription_status = ?, stripe_subscription_id = ?, last_payment_date = ?
    WHERE subdomain_name = ?
    """
    args = (status, stripe_subscription_id, last_payment_date, subdomain_name)
    execute_query(MAIN_DB_PATH, query, args, commit=True)

def add_post_to_shared_index(original_post_id_on_instance, blog_instance_subdomain, post_title, post_creation_date, post_link):
    """Adds a post entry to the shared posts index."""
    query = """
    INSERT INTO shared_posts_index (original_post_id_on_instance, blog_instance_subdomain, post_title, post_creation_date, post_link)
    VALUES (?, ?, ?, ?, ?)
    """
    args = (original_post_id_on_instance, blog_instance_subdomain, post_title, post_creation_date, post_link)
    execute_query(MAIN_DB_PATH, query, args, commit=True)

def get_random_posts_from_shared_index(limit=10, time_frame_days=30):
    """Retrieves random posts from the shared index within a time frame."""
    one_month_ago = datetime.now() - timedelta(days=time_frame_days)
    query = """
    SELECT post_title, post_link, blog_instance_subdomain
    FROM shared_posts_index
    WHERE post_creation_date >= ?
    ORDER BY RANDOM()
    LIMIT ?
    """
    args = (one_month_ago.strftime('%Y-%m-%d %H:%M:%S'), limit)
    return execute_query(MAIN_DB_PATH, query, args, many=True)

# Add other main database interaction functions as needed
