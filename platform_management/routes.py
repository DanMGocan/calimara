from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app, session
from .forms import BlogRegistrationForm, PlatformLoginForm # Removed SubdomainPromptForm
from .services import create_new_blog_instance 
from .db import get_blog_by_subdomain, get_blog_by_owner_id 
from blog_instance.services import authenticate_user # For global login
from models import User # For login_user
from flask_login import login_user, logout_user, current_user, login_required # Added login_required

platform_bp = Blueprint('platform', __name__)

@platform_bp.route('/')
def index():
    """Main platform homepage."""
    # If the user is authenticated and on the main platform, check if they own a blog.
    if current_user.is_authenticated:
        # It's important that g.is_blog_instance is False here,
        # meaning this is a request to the main platform, not a subdomain.
        # This check should ideally be implicitly handled by routing,
        # but an explicit check of g.is_blog_instance could be added for safety if needed.
        # For now, we assume this route is only hit for the main platform.
        
        user_blog = get_blog_by_owner_id(current_user.id)
        if user_blog:
            # User owns a blog, redirect to their blog's admin dashboard.
            subdomain = user_blog['subdomain_name']
            base_domain_parts = current_app.config.get('BASE_DOMAIN', 'localhost:5000').split(':')
            base_host = base_domain_parts[0]
            port_str = f":{base_domain_parts[1]}" if len(base_domain_parts) > 1 else ""
            # Redirect to the admin dashboard of their blog
            target_url = f"http://{subdomain}.{base_host}{port_str}/admin/dashboard"
            return redirect(target_url)
        # If authenticated user does not own a blog, they see the main platform page.

    # The random_posts and random_blogs_list are loaded in app.py's before_request and available in g
    return render_template('platform/index.html', 
                           random_posts=g.get('random_posts', []), 
                           random_blogs_list=g.get('random_blogs_list', [])) # Added random_blogs_list

@platform_bp.route('/register-blog', methods=['GET', 'POST'])
def register_blog():
    """Blog registration page."""
    form = BlogRegistrationForm() # Initialize form
    if form.validate_on_submit():
        try:
            # Call service to create new blog instance
            result = create_new_blog_instance(
                subdomain=form.subdomain.data,
                blog_title=form.blog_title.data,
                owner_username=form.owner_username.data,
                owner_email=form.owner_email.data,
                password=form.password.data
            )
            if result.get('success'):
                flash('Your blog has been created! Please check your email for details. You are now being logged in.', 'success')
                
                # Log in the new user
                user = User(result['owner_user_id'])
                login_user(user)
                
                # Redirect to the new blog's admin dashboard
                subdomain = result['subdomain']
                base_domain_parts = current_app.config.get('BASE_DOMAIN', 'localhost:5000').split(':')
                base_host = base_domain_parts[0]
                port_str = f":{base_domain_parts[1]}" if len(base_domain_parts) > 1 else ""
                # Redirect to the subdomain URL
                target_url = f"http://{subdomain}.{base_host}{port_str}/"
                return redirect(target_url)
            else:
                flash(f'Registration failed: {result.get("error", "Unknown error")}', 'danger')
        except ValueError as e: # This might be caught by service if it raises ValueError directly
             flash(f'Registration failed: {e}', 'danger')
        except Exception as e:
            # Handle other potential errors during the process
            flash(f'An unexpected error occurred during registration: {e}', 'danger')

    # Render the registration template, passing the form
    return render_template('platform/register_blog.html', form=form, random_posts=g.get('random_posts', []), random_blogs_list=g.get('random_blogs_list', []))

@platform_bp.route('/login', methods=['GET', 'POST'])
def login(): # Renamed from platform_login_prompt
    """Platform-wide login page."""
    if current_user.is_authenticated:
        # If already logged in, try to find their blog and redirect to its dashboard
        user_blog = get_blog_by_owner_id(current_user.id)
        if user_blog:
            subdomain = user_blog['subdomain_name']
            base_domain_parts = current_app.config.get('BASE_DOMAIN', 'localhost:5000').split(':')
            base_host = base_domain_parts[0]
            port_str = f":{base_domain_parts[1]}" if len(base_domain_parts) > 1 else ""
            # Redirect to the subdomain URL
            return redirect(f"http://{subdomain}.{base_host}{port_str}/")
        return redirect(url_for('platform.index')) # Or a generic user dashboard if no blog

    form = PlatformLoginForm()
    if form.validate_on_submit():
        user_id = authenticate_user(g.db_name, form.email.data, form.password.data)
        if user_id:
            user = User(user_id)
            login_user(user)
            flash('Logged in successfully.', 'success')
            
            # Find user's blog
            user_blog = get_blog_by_owner_id(user_id) # New DB function needed
            if user_blog:
                # Construct subdomain URL carefully
                subdomain = user_blog['subdomain_name']
                base_domain_parts = current_app.config.get('BASE_DOMAIN', 'localhost:5000').split(':')
                base_host = base_domain_parts[0]
                port_str = f":{base_domain_parts[1]}" if len(base_domain_parts) > 1 else ""
                
                # Redirect to the blog's admin dashboard
                return redirect(url_for('blog.admin_dashboard', blog_subdomain_part=subdomain)) # <-- CHANGE IS HERE
            else:
                # User authenticated but has no blog, redirect to main page or a "create blog" prompt
                flash('You do not have a blog yet. Why not create one?', 'info')
                return redirect(url_for('platform.register_blog'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('platform/login.html', form=form, random_posts=g.get('random_posts', []), random_blogs_list=g.get('random_blogs_list', []))

@platform_bp.route('/logout')
@login_required
def logout():
    """Platform-wide logout."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('platform.index'))

# Add other platform routes here as needed
