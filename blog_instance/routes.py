from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app, session, jsonify
from .forms import PostForm, CommentForm, LoginForm
from . import services # Import the services module
from . import db
from models import User # Import User from models.py
import mysql # For mysql.connector.errors.IntegrityError
from flask_login import login_user # Import login_user

blog_bp = Blueprint('blog', __name__)

# Placeholder User class for Flask-Login (will be properly implemented later)
# class User(UserMixin):
#     def __init__(self, id):
#         self.id = id
#         # In a real app, you'd load user data from the instance DB here

# @login_manager.user_loader
# def load_user(user_id):
#     # Load user from the current instance DB based on g.instance_db_path
#     # This requires careful implementation to get the correct DB path
#     # For now, return None
#     return None


@blog_bp.route('/')
def index(blog_subdomain_part): # Added blog_subdomain_part
    print(f"[CRITICAL DEBUG] blog_bp.index called! subdomain_part: {blog_subdomain_part}")
    """Blog instance homepage - displays a list of posts."""
    print(f"[DEBUG] blog_instance/routes.py - index: g.is_blog_instance: {g.is_blog_instance}, g.subdomain: {g.subdomain}, g.blog_id: {g.blog_id}")
    # Check if this is a blog instance
    if not g.is_blog_instance or not g.blog_id: # Check g.blog_id
        # This route should only be accessed via a valid subdomain context
        return redirect(url_for('platform.index')) # Redirect to main platform

    # If user is authenticated, redirect to their admin dashboard
    # The admin_dashboard route itself is protected by @login_required
    if current_user.is_authenticated:
        return redirect(url_for('blog.admin_dashboard', blog_subdomain_part=g.subdomain))

    # Fetch posts from the main database, scoped by blog_id
    posts = db.get_all_posts(g.db_name, g.blog_id)

    return render_template('blog/index.html', posts=posts, subdomain=g.subdomain, random_posts=g.get('random_posts', []), random_blogs_list=g.get('random_blogs_list', []))

@blog_bp.route('/posts/<slug>', methods=['GET', 'POST'])
def post_detail(blog_subdomain_part, slug): # Added blog_subdomain_part
    """Displays a single post and handles comment submission."""
    # subdomain parameter is now passed by Flask
    if not g.is_blog_instance or not g.blog_id: # Check g.blog_id
        return redirect(url_for('platform.index'))

    # Fetch post from the main database, scoped by blog_id
    post = services.get_post_by_slug(g.db_name, g.blog_id, slug) # Use service layer

    if post is None:
        # TODO: Render a 404 page
        return "Post not found", 404 # Placeholder

    # view count is incremented within get_post_by_slug service if post found

    # Fetch approved comments for the post
    comments = db.get_approved_comments_for_post(g.db_name, post['id'])

    # Initialize comment form
    comment_form = CommentForm()

    # Handle comment form submission
    if comment_form.validate_on_submit():
        try:
            # Add comment (initially unapproved)
            services.add_comment( # Use service layer
                g.db_name,
                post['id'],
                comment_form.commenter_name.data,
                comment_form.commenter_email.data,
                comment_form.content.data
            )
            flash('Your comment has been submitted and is awaiting moderation.', 'success')
            # Redirect to the same post detail page to clear the form
            return redirect(url_for('blog.post_detail', slug=slug))
        except Exception as e:
            flash(f'Error submitting comment: {e}', 'danger')

    # Pass like count to the template
    if post: # Ensure post is not None before trying to make it a dict
        post = dict(post) # Convert Row object to dict to add new keys
        post['like_count'] = db.get_like_count_for_post(g.db_name, post['id'])
        # Pass tags to the template
        post['tags'] = db.get_tags_for_post(g.db_name, post['id'])


    return render_template('blog/post_detail.html', post=post, comments=comments, comment_form=comment_form, subdomain=g.subdomain, random_posts=g.get('random_posts', []), random_blogs_list=g.get('random_blogs_list', []))

# Route for handling likes (AJAX endpoint)
@blog_bp.route('/posts/<int:post_id>/like', methods=['POST'])
def add_like_route(blog_subdomain_part, post_id): # Added blog_subdomain_part
    """Handles AJAX request to add a like to a post."""
    # subdomain parameter is now passed by Flask
    if not g.is_blog_instance or not g.blog_id: # Check g.blog_id
        return jsonify(success=False, message="Invalid request"), 400

    # Get a unique identifier for the liker (e.g., IP address + User-Agent hash)
    # For simplicity, using request.remote_addr for now.
    # A more robust approach might involve hashing IP + User-Agent or using session IDs.
    liker_identifier = request.remote_addr # Basic identifier

    try:
        services.add_like(g.db_name, post_id, liker_identifier) # Use service layer
        # Get updated like count
        like_count = db.get_like_count_for_post(g.db_name, post_id)
        return jsonify(success=True, like_count=like_count)
    except mysql.connector.errors.IntegrityError: # Updated for MySQL
        # This means the liker_identifier already liked this post (due to UNIQUE constraint)
        return jsonify(success=False, message="Already liked this post"), 409 # Conflict
    except Exception as e:
        print(f"Error adding like: {e}")
        return jsonify(success=False, message="Failed to add like"), 500

# Admin Routes (require login)
from flask_login import login_required # Import login_required

@blog_bp.route('/admin/dashboard')
@login_required # Require login
def admin_dashboard(blog_subdomain_part): # Added blog_subdomain_part
    """Blog owner's admin dashboard."""
    # subdomain parameter is now passed by Flask
    if not g.is_blog_instance or not g.blog_id: # Check g.blog_id
        return redirect(url_for('platform.index'))

    # Fetch data for the dashboard
    pending_comments = services.get_pending_comments(g.db_name, g.blog_id) # Use service
    posts_with_stats = services.get_posts_with_stats(g.db_name, g.blog_id) # Use service

    return render_template('blog/admin_dashboard.html',
                           pending_comments=pending_comments,
                           posts_with_stats=posts_with_stats,
                           subdomain=g.subdomain,
                           random_posts=g.get('random_posts', []), random_blogs_list=g.get('random_blogs_list', []))

from flask_login import login_required, current_user # Import current_user

@blog_bp.route('/admin/posts/new', methods=['GET', 'POST'])
@login_required
def create_new_post(blog_subdomain_part): # Added blog_subdomain_part
    """Page to create a new post."""
    # subdomain parameter is now passed by Flask
    if not g.is_blog_instance or not g.blog_id: # Check g.blog_id
        return redirect(url_for('platform.index'))

    form = PostForm() # Initialize form
    if form.validate_on_submit():
        try:
            # Create post
            services.create_post( # Use service layer
                g.db_name,
                g.blog_id,
                current_user.id, 
                form.title.data,
                form.content.data,
                form.tags.data,
                g.subdomain, 
                current_app.config['BASE_DOMAIN']
            )
            flash('Post created successfully!', 'success')
            return redirect(url_for('blog.admin_dashboard')) # Redirect to admin dashboard
        except Exception as e:
            flash(f'Error creating post: {e}', 'danger')

    return render_template('blog/create_edit_post.html', form=form, action='create', subdomain=g.subdomain, random_posts=g.get('random_posts', []), random_blogs_list=g.get('random_blogs_list', []))

@blog_bp.route('/admin/posts/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(blog_subdomain_part, post_id): # Added blog_subdomain_part
    """Page to edit an existing post."""
    # subdomain parameter is now passed by Flask
    if not g.is_blog_instance or not g.blog_id: # Check g.blog_id
        return redirect(url_for('platform.index'))

    # Fetch the post to be edited
    post = db.get_post_by_id(g.db_name, g.blog_id, post_id)

    # Check if post exists and belongs to the current user
    if post is None or post['user_id'] != current_user.id:
        flash('Post not found or you do not have permission to edit it.', 'danger')
        return redirect(url_for('blog.admin_dashboard')) # Redirect to admin dashboard

    form = PostForm() # Initialize form

    if form.validate_on_submit():
        try:
            # Update post
            services.update_post( # Use service layer
                g.db_name,
                g.blog_id,
                post_id,
                form.title.data,
                form.content.data,
                form.tags.data
            )
            flash('Post updated successfully!', 'success')
            # Redirect to the post detail page or admin dashboard
            return redirect(url_for('blog.post_detail', slug=form.generate_slug())) # Redirect using the potentially new slug
        except Exception as e:
            flash(f'Error updating post: {e}', 'danger')
    elif request.method == 'GET':
        # Pre-populate the form with existing post data on GET request
        form.title.data = post['title']
        form.content.data = post['content']
        # Fetch and populate tags
        tags = db.get_tags_for_post(g.db_name, post_id)
        form.tags.data = ', '.join([tag['name'] for tag in tags])


    return render_template('blog/create_edit_post.html', form=form, action='edit', post=post, subdomain=g.subdomain, random_posts=g.get('random_posts', []), random_blogs_list=g.get('random_blogs_list', []))

@blog_bp.route('/admin/posts/delete/<int:post_id>', methods=['POST']) # Use POST for deletion
@login_required
def delete_post_route(blog_subdomain_part, post_id): # Added blog_subdomain_part
    """Handles deleting a post."""
    # subdomain parameter is now passed by Flask
    if not g.is_blog_instance or not g.blog_id: # Check g.blog_id
        return redirect(url_for('platform.index'))

    # Fetch the post to be deleted
    post = db.get_post_by_id(g.db_name, g.blog_id, post_id)

    # Check if post exists and belongs to the current user
    if post is None or post['user_id'] != current_user.id:
        flash('Post not found or you do not have permission to delete it.', 'danger')
        return redirect(url_for('blog.admin_dashboard')) # Redirect to admin dashboard

    try:
        # Delete post
        services.delete_post(g.db_name, g.blog_id, post_id, g.subdomain) # Use service
        flash('Post deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting post: {e}', 'danger')

    return redirect(url_for('blog.admin_dashboard')) # Redirect back to admin dashboard


@blog_bp.route('/admin/comments/approve/<int:comment_id>')
@login_required
def approve_comment(blog_subdomain_part, comment_id): # Added blog_subdomain_part
    """Approves a pending comment."""
    # subdomain parameter is now passed by Flask
    if not g.is_blog_instance or not g.blog_id: # Check g.blog_id
        return redirect(url_for('platform.index'))

    try:
        # Approve comment
        services.approve_comment(g.db_name, g.blog_id, comment_id, current_user.id) # Use service
        flash('Comment approved.', 'success')
    except Exception as e:
        flash(f'Error approving comment: {e}', 'danger')

    return redirect(url_for('blog.admin_dashboard')) # Redirect back to admin dashboard

# Login/Logout Routes are now handled by the platform blueprint for global login.
# The per-subdomain login is removed.
# Logout for a blog instance context can remain if it has specific logic,
# otherwise, a global logout is also fine.
# For now, let's keep the blog-specific logout as it redirects to blog.index.
from flask_login import login_required, logout_user # Ensure logout_user is imported

@blog_bp.route('/logout')
@login_required
def logout(blog_subdomain_part): # Added blog_subdomain_part
    """Logs out the blog owner."""
    # subdomain parameter is now passed by Flask
    if not g.is_blog_instance or not g.blog_id: # Check g.blog_id
        return redirect(url_for('platform.index'))

    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('blog.index')) # Redirect to blog homepage

@blog_bp.route('/login', methods=['GET', 'POST'])
def login(blog_subdomain_part):
    if current_user.is_authenticated:
        return redirect(url_for('blog.admin_dashboard', blog_subdomain_part=g.subdomain))

    form = LoginForm()
    error = None
    if form.validate_on_submit():
        user_id = services.authenticate_user(g.db_name, form.email.data, form.password.data)
        if user_id:
            user = User(user_id)
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('blog.admin_dashboard', blog_subdomain_part=g.subdomain))
        else:
            error = 'Invalid email or password.'
            flash(error, 'danger')
    return render_template('blog/login.html', form=form, subdomain=g.subdomain, error=error, random_posts=g.get('random_posts', []), random_blogs_list=g.get('random_blogs_list', []))

@blog_bp.route('/login', methods=['POST'])
def login_ajax(blog_subdomain_part):
    if current_user.is_authenticated:
        return jsonify(success=True, redirect_url=url_for('blog.admin_dashboard', blog_subdomain_part=g.subdomain))

    form = LoginForm()
    if form.validate_on_submit():
        user_id = services.authenticate_user(g.db_name, form.email.data, form.password.data)
        if user_id:
            user = User(user_id)
            login_user(user)
            return jsonify(success=True, redirect_url=url_for('blog.admin_dashboard', blog_subdomain_part=g.subdomain))
        else:
            return jsonify(success=False, error='Invalid email or password.')
    # If form is not valid
    errors = {field: errors for field, errors in form.errors.items()}
    return jsonify(success=False, error='Validation failed.', form_errors=errors)

# Admin Routes (require login)
# @blog_bp.route('/admin/dashboard')
# @login_required # Require login
# def admin_dashboard():
#     """Blog owner's admin dashboard."""
#     if not g.is_blog_instance or not g.instance_db_path:
#         return redirect(url_for('platform.index'))

#     # Fetch data for the dashboard (will use db.py and services.py later)
#     # pending_comments = get_pending_comments(g.instance_db_path)
#     # posts_with_stats = get_posts_with_stats(g.instance_db_path)
#     pending_comments = [] # Placeholder
#     posts_with_stats = [] # Placeholder

#     return render_template('blog/admin_dashboard.html',
#                            pending_comments=pending_comments,
#                            posts_with_stats=posts_with_stats,
#                            subdomain=g.subdomain,
#                            random_posts=g.get('random_posts', []))

# @blog_bp.route('/admin/posts/new', methods=['GET', 'POST'])
# @login_required
# def create_new_post():
#     """Page to create a new post."""
#     if not g.is_blog_instance or not g.instance_db_path:
#         return redirect(url_for('platform.index'))

#     # form = PostForm() # Initialize when form is defined
#     # if form.validate_on_submit():
#     #     try:
#     #         # Create post (will use services.py later)
#     #         create_post(g.instance_db_path, form.title.data, form.content.data, current_user.id, form.tags.data)
#     #         flash('Post created successfully!', 'success')
#     #         return redirect(url_for('blog.admin_dashboard', subdomain=g.subdomain)) # Redirect to admin dashboard
#     #     except Exception as e:
#     #         flash(f'Error creating post: {e}', 'danger')

#     # return render_template('blog/create_edit_post.html', form=form, action='create', subdomain=g.subdomain, random_posts=g.get('random_posts', []))

#     # Placeholder
#     return "Create New Post Page (Admin)", 200


# @blog_bp.route('/admin/comments/approve/<int:comment_id>')
# @login_required
# def approve_comment(comment_id):
#     """Approves a pending comment."""
#     if not g.is_blog_instance or not g.instance_db_path:
#         return redirect(url_for('platform.index'))

#     # Approve comment (will use services.py later)
#     # try:
#     #     approve_comment(g.instance_db_path, comment_id, current_user.id)
#     #     flash('Comment approved.', 'success')
#     # except Exception as e:
#     #     flash(f'Error approving comment: {e}', 'danger')

#     # return redirect(url_for('blog.admin_dashboard', subdomain=g.subdomain)) # Redirect back to admin dashboard

#     # Placeholder
#     return f"Approve Comment {comment_id} (Admin)", 200

# Login/Logout Routes
# @blog_bp.route('/login', methods=['GET', 'POST'])
# def login():
#     if current_user.is_authenticated:
#         return redirect(url_for('blog.admin_dashboard', subdomain=g.subdomain))

#     # form = LoginForm() # Initialize when form is defined
#     # if form.validate_on_submit():
#     #     # Authenticate user against instance DB (will use db.py later)
#     #     user_record = get_user_by_email(g.instance_db_path, form.email.data)
#     #     if user_record and check_password_hash(user_record['password_hash'], form.password.data):
#     #         user = User(user_record['id']) # Create Flask-Login User object
#     #         login_user(user)
#     #         # Redirect to the admin dashboard or the page they were trying to access
#     #         next_page = request.args.get('next')
#     #         return redirect(next_page or url_for('blog.admin_dashboard', subdomain=g.subdomain))
#     #     else:
#     #         flash('Invalid email or password', 'danger')

#     # return render_template('blog/login.html', form=form, subdomain=g.subdomain, random_posts=g.get('random_posts', []))

#     # Placeholder
#     return "Blog Login Page", 200

# @blog_bp.route('/logout')
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for('blog.index', subdomain=g.subdomain)) # Redirect to blog homepage
