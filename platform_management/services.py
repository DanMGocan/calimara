import os
import mysql.connector
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from config import Config
from core.db_utils import init_db_from_schema, execute_query
from core.mail_utils import send_email
from .db import add_blog_instance_record, get_blog_by_subdomain # Import from local db module
import shutil # Import shutil for directory removal

def create_new_blog_instance(subdomain, blog_title, owner_username, owner_email, password):
    """
    Orchestrates the creation of a new blog instance.

    Args:
        subdomain: The chosen subdomain name.
        blog_title: The title of the blog.
        owner_username: The username for the blog owner.
        owner_email: The email for the blog owner.
        password: The password for the blog owner.
        recaptcha_response: The response from the Google reCAPTCHA widget.

    Raises:
        ValueError: If subdomain is already taken.
        Exception: For other errors during the process.
    """

    # 1. Check if subdomain is already taken (already done in form validation, but good to double-check)
    if get_blog_by_subdomain(subdomain):
         raise ValueError(f"Subdomain '{subdomain}' is already taken.")

    instance_db_name = None
    owner_user_id = None

    try:
        # The main database (calimara_db) is already initialized by app.py
        # No need to create a separate instance database or schema.
        
        main_db_name = os.getenv('MYSQL_DATABASE', 'calimara_db')

        # 2. Create or get the owner user in the main 'users' table
        # Check if user already exists by email
        existing_user = execute_query(
            main_db_name,
            "SELECT id FROM users WHERE email = %s",
            (owner_email,),
            one=True
        )
        
        if existing_user:
            # For simplicity, we'll prevent creating a new blog if the email is already registered as a user.
            # A more complex system might allow a user to own multiple blogs or link to an existing user.
            # Current schema has UNIQUE constraint on owner_email in blogs table, which also helps.
            # And users.email is UNIQUE.
            # If we want one user to own multiple blogs, the blogs.owner_email unique constraint needs to be removed.
            # For now, let's assume one email = one user = potentially one blog (as per current blogs.owner_email UNIQUE)
            # This part of the logic might need refinement based on exact multi-tenancy rules for users.
            # Let's assume for now that if a user with this email exists, we use that user's ID.
            # However, the registration form implies creating a new user.
            # A simpler approach for now: if email exists in users table, raise error or link.
            # For now, let's proceed with creating a new user, assuming users.email is unique.
            # The platform_management.forms.validate_owner_email already checks if email is in blogs table.
            # We should also check if email is in users table and handle appropriately.
            # For now, let's assume the form validation handles new user email uniqueness.
            pass # User creation will happen below if not existing, or fail on unique email if it does.

        hashed_password = generate_password_hash(password)
        # Add the blog owner user to the main 'users' table
        # The 'users' table in mysql_schema.sql does not have 'blog_title'
        owner_user_id = execute_query(
            main_db_name,
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (owner_username, owner_email, hashed_password),
            commit=True,
            last_row_id=True
        )
        if owner_user_id is None:
             # This could happen if the email/username already exists due to UNIQUE constraints
             # Try to fetch the user ID if insert failed due to existing user
             existing_user_by_email = execute_query(main_db_name, "SELECT id FROM users WHERE email = %s", (owner_email,), one=True)
             if existing_user_by_email:
                 owner_user_id = existing_user_by_email['id']
                 print(f"User with email {owner_email} already exists, using ID: {owner_user_id}")
             else:
                raise Exception("Could not create or find user, and failed to get user ID.")

        # 3. Add record to the main 'blogs' database
        add_blog_instance_record(
            subdomain_name=subdomain,
            blog_title=blog_title,
            owner_user_id=owner_user_id, # Store the user ID from the instance DB
            owner_email=owner_email
        )

        # 6. Send confirmation email
        try:
            subject = f"Welcome to your new blog: {blog_title}!"
            # Basic HTML content, can be improved with templates later
            html_content = f"""
            <p>Hello {owner_username},</p>
            <p>Your new blog, "{blog_title}", has been successfully created at:</p>
            <p><a href="http://{subdomain}.{Config.BASE_DOMAIN}">http://{subdomain}.{Config.BASE_DOMAIN}</a></p>
            <p>You can log in to your admin dashboard at:</p>
            <p><a href="http://{subdomain}.{Config.BASE_DOMAIN}/admin/dashboard">http://{subdomain}.{Config.BASE_DOMAIN}/admin/dashboard</a></p>
            <p>Happy writing!</p>
            """
            send_email(owner_email, subject, html_content)
        except Exception as e:
            print(f"Warning: Failed to send confirmation email to {owner_email}: {e}")
            # This is a non-critical failure, the blog is created, just log the warning.


        print(f"Blog instance '{subdomain}' created successfully.")
        return {'success': True, 'owner_user_id': owner_user_id, 'subdomain': subdomain}

    except Exception as e:
        print(f"Error during blog instance creation for {subdomain}: {e}")
        return {'success': False, 'error': str(e)} # Return error information

        # --- Cleanup on Failure ---
        # No separate instance database to clean up.
        # If user was created, it remains. If blog record was created, it remains.
        # More sophisticated cleanup could remove them if partial creation occurred.
        # For now, rely on DB constraints for consistency.

        # Note: If the record was added to main.db blogs table, it will remain there.
        # A more complex cleanup could involve removing it, but for simplicity
        # and given the subdomain uniqueness check, this might be acceptable
        # depending on how critical perfect cleanup is.

        raise Exception(f"Blog creation failed: {e}") # Re-raise the original exception

# Add other platform-level service functions here (e.g., webhook handlers)

# Helper function to verify reCAPTCHA (if not using Flask-WTF's built-in validation)
# import requests
# def verify_recaptcha(response):
#     """Verifies the Google reCAPTCHA response."""
#     payload = {
#         'secret': Config.RECAPTCHA_PRIVATE_KEY,
#         'response': response
#     }
#     try:
#         r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
#         result = r.json()
#         return result.get('success', False)
#     except Exception as e:
#         print(f"reCAPTCHA verification request failed: {e}")
#         return False
