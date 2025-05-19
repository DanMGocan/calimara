from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from .forms import BlogRegistrationForm # Import when form is defined
from .services import create_new_blog_instance # Import when service is defined

platform_bp = Blueprint('platform', __name__)

@platform_bp.route('/')
def index():
    """Main platform homepage."""
    # The random_posts are loaded in app.py's before_request and available in g
    return render_template('platform/index.html', random_posts=g.get('random_posts', []))

@platform_bp.route('/register-blog', methods=['GET', 'POST'])
def register_blog():
    """Blog registration page."""
    form = BlogRegistrationForm() # Initialize form
    if form.validate_on_submit():
        try:
            # Call service to create new blog instance
            create_new_blog_instance(
                subdomain=form.subdomain.data,
                blog_title=form.blog_title.data,
                owner_username=form.owner_username.data,
                owner_email=form.owner_email.data,
                password=form.password.data,
                recaptcha_response=request.form.get('g-recaptcha-response') # Get reCAPTCHA response
            )
            flash('Your blog has been created! Please check your email for details.', 'success')
            # Redirect to the new blog's login page or homepage
            # Need to dynamically generate the URL for the new blog
            # For now, redirect to the main platform index
            return redirect(url_for('platform.index'))
        except ValueError as e:
             # Handle specific validation errors from the service (e.g., subdomain taken)
             flash(f'Registration failed: {e}', 'danger')
        except Exception as e:
            # Handle other potential errors during the process
            flash(f'An unexpected error occurred during registration: {e}', 'danger')

    # Render the registration template, passing the form
    return render_template('platform/register_blog.html', form=form, random_posts=g.get('random_posts', []))

# Add other platform routes here (e.g., /pricing, /stripe-webhook)
# @platform_bp.route('/pricing')
# def pricing():
#     return render_template('platform/pricing.html', random_posts=g.get('random_posts', []))

# @platform_bp.route('/stripe-webhook', methods=['POST'])
# def stripe_webhook():
#     # Handle Stripe webhook events here
#     pass
