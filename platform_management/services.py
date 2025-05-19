import os
import sqlite3
from datetime import datetime, timedelta
import stripe
from werkzeug.security import generate_password_hash
from config import Config
from core.db_utils import init_db_from_schema, execute_query
from core.mail_utils import send_email
from .db import add_blog_instance_record, get_blog_by_subdomain # Import from local db module
import shutil # Import shutil for directory removal

# Configure Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

def create_new_blog_instance(subdomain, blog_title, owner_username, owner_email, password, recaptcha_response):
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
    # reCAPTCHA verification is handled by Flask-WTF form validation

    # 1. Check if subdomain is already taken (already done in form validation, but good to double-check)
    if get_blog_by_subdomain(subdomain):
         raise ValueError(f"Subdomain '{subdomain}' is already taken.")

    stripe_customer_id = None
    stripe_subscription_id = None
    instance_db_path = None
    owner_user_id = None

    try:
        # 2. Create Stripe Customer and Subscription (Trial)
        customer = stripe.Customer.create(
            email=owner_email,
            description=f"Customer for blog: {subdomain}.{Config.BASE_DOMAIN}"
        )
        stripe_customer_id = customer.id

        # Assuming you have a Stripe Product and Price set up for the 2 euro/month plan
        # Replace 'price_12345' with your actual Stripe Price ID
        subscription = stripe.Subscription.create(
            customer=stripe_customer_id,
            items=[{"price": "price_12345"}], # Replace with your Stripe Price ID
            trial_period_days=30, # 1 month trial
            expand=["latest_invoice.payment_intent"]
        )
        stripe_subscription_id = subscription.id
        trial_ends_at = datetime.fromtimestamp(subscription.trial_end)


        # 3. Create the instance database file and initialize schema
        instance_db_path = os.path.join(Config.INSTANCE_DB_DIR_PATH, f'{subdomain}.db')
        instance_schema_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'blog_instance', 'schemas', 'instance_db_schema.sql')

        init_db_from_schema(instance_db_path, instance_schema_path)


        # 4. Add the blog owner user to the instance database
        hashed_password = generate_password_hash(password)
        # Use the instance database path to execute the query
        owner_user_id = execute_query(
            instance_db_path,
            "INSERT INTO users (username, email, password_hash, blog_title) VALUES (?, ?, ?, ?)",
            (owner_username, owner_email, hashed_password, blog_title),
            commit=True,
            last_row_id=True
        )
        if owner_user_id is None:
             raise Exception("Could not get the last inserted user ID after creating user.")


        # 5. Add record to the main database
        add_blog_instance_record(
            subdomain_name=subdomain,
            blog_title=blog_title,
            owner_user_id=owner_user_id, # Store the user ID from the instance DB
            owner_email=owner_email,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            trial_ends_at=trial_ends_at
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
            <p>Your trial period is active until {trial_ends_at.strftime('%Y-%m-%d')}.</p>
            <p>Happy writing!</p>
            """
            send_email(owner_email, subject, html_content)
        except Exception as e:
            print(f"Warning: Failed to send confirmation email to {owner_email}: {e}")
            # This is a non-critical failure, the blog is created, just log the warning.


        print(f"Blog instance '{subdomain}' created successfully.")
        return True # Indicate success

    except Exception as e:
        print(f"Error during blog instance creation for {subdomain}: {e}")

        # --- Cleanup on Failure ---
        # Attempt to delete the Stripe subscription if it was created
        if stripe_subscription_id:
            try:
                stripe.Subscription.delete(stripe_subscription_id)
                print(f"Rolled back Stripe subscription {stripe_subscription_id}.")
            except stripe.error.StripeError as rollback_e:
                print(f"Failed to rollback Stripe subscription {stripe_subscription_id}: {rollback_e}")
            except Exception as rollback_e:
                 print(f"Failed to rollback Stripe subscription {stripe_subscription_id}: {rollback_e}")

        # Attempt to delete the Stripe customer if it was created
        if stripe_customer_id:
            try:
                stripe.Customer.delete(stripe_customer_id)
                print(f"Rolled back Stripe customer {stripe_customer_id}.")
            except stripe.error.StripeError as rollback_e:
                print(f"Failed to rollback Stripe customer {stripe_customer_id}: {rollback_e}")
            except Exception as rollback_e:
                 print(f"Failed to rollback Stripe customer {stripe_customer_id}: {rollback_e}")


        # Attempt to delete the instance database file if it was created
        if instance_db_path and os.path.exists(instance_db_path):
            try:
                os.remove(instance_db_path)
                print(f"Cleaned up instance database file: {instance_db_path}")
            except OSError as cleanup_e:
                print(f"Failed to clean up instance database file {instance_db_path}: {cleanup_e}")

        # Note: If the record was added to main.db, it will remain there.
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
