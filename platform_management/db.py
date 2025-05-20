import mysql.connector
import os
from datetime import datetime, timedelta
from core.db_utils import execute_query, get_db_connection
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get MySQL database name from environment variables
MAIN_DB_NAME = os.getenv('MYSQL_DATABASE', 'calimara_db')

def add_blog_instance_record(subdomain_name, blog_title, owner_user_id, owner_email):
    """Adds a new blog instance record to the main database."""
    query = """
    INSERT INTO blogs (subdomain_name, blog_title, owner_user_id, owner_email)
    VALUES (%s, %s, %s, %s)
    """
    args = (subdomain_name, blog_title, owner_user_id, owner_email)
    execute_query(MAIN_DB_NAME, query, args, commit=True)

def get_blog_by_subdomain(subdomain_name):
    """Retrieves a blog record from the main database by subdomain."""
    query = "SELECT * FROM blogs WHERE subdomain_name = %s"
    args = (subdomain_name,)
    return execute_query(MAIN_DB_NAME, query, args, one=True)

def add_post_to_shared_index(original_post_id_on_instance, blog_instance_subdomain, post_title, post_creation_date, post_link):
    """Adds a post entry to the shared posts index."""
    query = """
    INSERT INTO shared_posts_index (original_post_id_on_instance, blog_instance_subdomain, post_title, post_creation_date, post_link)
    VALUES (%s, %s, %s, %s, %s)
    """
    args = (original_post_id_on_instance, blog_instance_subdomain, post_title, post_creation_date, post_link)
    execute_query(MAIN_DB_NAME, query, args, commit=True)

def get_random_posts_from_shared_index(limit=10, time_frame_days=30):
    """Retrieves random posts from the shared index within a time frame."""
    one_month_ago = datetime.now() - timedelta(days=time_frame_days)
    query = """
    SELECT post_title, post_link, blog_instance_subdomain
    FROM shared_posts_index
    WHERE post_creation_date >= %s
    ORDER BY RAND()
    LIMIT %s
    """
    args = (one_month_ago.strftime('%Y-%m-%d %H:%M:%S'), limit)
    return execute_query(MAIN_DB_NAME, query, args, many=True)

def get_random_blogs(limit=10):
    """Retrieves a list of random blogs."""
    query = """
    SELECT subdomain_name, blog_title
    FROM blogs
    ORDER BY RAND()
    LIMIT %s
    """
    args = (limit,)
    return execute_query(MAIN_DB_NAME, query, args, many=True)

def get_blog_by_owner_id(owner_user_id):
    """Retrieves a blog record from the main database by owner_user_id."""
    query = "SELECT id, subdomain_name, blog_title FROM blogs WHERE owner_user_id = %s LIMIT 1" # Assuming one blog per user for now
    args = (owner_user_id,)
    return execute_query(MAIN_DB_NAME, query, args, one=True)

# Add other main database interaction functions as needed
