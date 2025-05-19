from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from .forms import PostForm, CommentForm, LoginForm # Import when forms are defined
from .services import create_post, get_post_by_slug, add_comment, approve_comment, add_like # Import when services are defined
# from werkzeug.security import check_password_hash # Import when implementing login
# from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user # Import when implementing login
from . import db # Import local db module

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
def index():
    """Blog instance homepage - displays a list of posts."""
    if not g.is_blog_instance or not g.instance_db_path:
        # This route should only be accessed via a subdomain
        return redirect(url_for('platform.index')) # Redirect to main platform if accessed directly

    # Fetch posts from the current instance database
    posts = db.get_all_posts(g.instance_db_path)

    return render_template('blog/index.html', posts=posts, subdomain=g.subdomain, random_posts=g.get('random_posts', []))

@blog_bp.route('/posts/<slug>', methods=['GET', 'POST'])
def post_detail(slug):
    """Displays a single post and handles comment submission."""
    if not g.is_blog_instance or not g.instance_db_path:
        return redirect(url_for('platform.index'))

    # Fetch post from the current instance database
    post = db.get_post_by_slug(g.instance_db_path, slug)

    if post is None:
        # TODO: Render a 404 page
        return "Post not found", 404 # Placeholder

    # Increment view count
    db.increment_post_view_count(g.instance_db_path, post['id'])

    # Fetch approved comments for the post
    comments = db.get_approved_comments_for_post(g.instance_db_path, post['id'])

    # Initialize comment form
    comment_form = CommentForm()

    # Handle comment form submission
    if comment_form.validate_on_submit():
        try:
            # Add comment (initially unapproved)
            db.add_comment(
                g.instance_db_path,
                post['id'],
                comment_form.commenter_name.data,
                comment_form.commenter_email.data,
                comment_form.content.data
            )
            flash('Your comment has been submitted and is awaiting moderation.', 'success')
            # Redirect to the same post detail page to clear the form
            return redirect(url_for('blog.post_detail', subdomain=g.subdomain, slug=slug))
        except Exception as e:
            flash(f'Error submitting comment: {e}', 'danger')

    # Pass like count to the template
    post = dict(post) # Convert Row object to dict to add new keys
    post['like_count'] = db.get_like_count_for_post(g.instance_db_path, post['id'])
    # Pass tags to the template
    post['tags'] = db.get_tags_for_post(g.instance_db_path, post['id'])


    return render_template('blog/post_detail.html', post=post, comments=comments, comment_form=comment_form, subdomain=g.subdomain, random_posts=g.get('random_posts', []))

# Route for handling likes (AJAX endpoint)
@blog_bp.route('/posts/<int:post_id>/like', methods=['POST'])
def add_like_route(post_id):
    """Handles AJAX request to add a like to a post."""
    if not g.is_blog_instance or not g.instance_db_path:
        return jsonify(success=False, message="Invalid request"), 400

    # Get a unique identifier for the liker (e.g., IP address + User-Agent hash)
    # For simplicity, using request.remote_addr for now.
    # A more robust approach might involve hashing IP + User-Agent or using session IDs.
    liker_identifier = request.remote_addr # Basic identifier

    try:
        db.add_like(g.instance_db_path, post_id, liker_identifier)
        # Get updated like count
        like_count = db.get_like_count_for_post(g.instance_db_path, post_id)
        return jsonify(success=True, like_count=like_count)
    except sqlite3.IntegrityError:
        # This means the liker_identifier already liked this post (due to UNIQUE constraint)
        return jsonify(success=False, message="Already liked this post"), 409 # Conflict
    except Exception as e:
        print(f"Error adding like: {e}")
        return jsonify(success=False, message="Failed to add like"), 500

# Admin Routes (require login)
from flask_login import login_required # Import login_required

@blog_bp.route('/admin/dashboard')
@login_required # Require login
def admin_dashboard():
    """Blog owner's admin dashboard."""
    if not g.is_blog_instance or not g.instance_db_path:
        return redirect(url_for('platform.index'))

    # Fetch data for the dashboard
    pending_comments = db.get_pending_comments(g.instance_db_path)
    posts_with_stats = db.get_posts_with_stats(g.instance_db_path)

    return render_template('blog/admin_dashboard.html',
                           pending_comments=pending_comments,
                           posts_with_stats=posts_with_stats,
                           subdomain=g.subdomain,
                           random_posts=g.get('random_posts', []))

from flask_login import login_required, current_user # Import current_user

@blog_bp.route('/admin/posts/new', methods=['GET', 'POST'])
@login_required
def create_new_post():
    """Page to create a new post."""
    if not g.is_blog_instance or not g.instance_db_path:
        return redirect(url_for('platform.index'))

    form = PostForm() # Initialize form
    if form.validate_on_submit():
        try:
            # Create post
            # Need to pass subdomain and base_domain to service for shared index link
            create_post(
                g.instance_db_path,
                current_user.id, # Get user ID from Flask-Login's current_user
                form.title.data,
                form.content.data,
                form.tags.data,
                g.subdomain, # Pass subdomain
                current_app.config['BASE_DOMAIN'] # Pass base domain
            )
            flash('Post created successfully!', 'success')
            return redirect(url_for('blog.admin_dashboard', subdomain=g.subdomain)) # Redirect to admin dashboard
        except Exception as e:
            flash(f'Error creating post: {e}', 'danger')

    return render_template('blog/create_edit_post.html', form=form, action='create', subdomain=g.subdomain, random_posts=g.get('random_posts', []))

@blog_bp.route('/admin/posts/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """Page to edit an existing post."""
    if not g.is_blog_instance or not g.instance_db_path:
        return redirect(url_for('platform.index'))

    # Fetch the post to be edited
    post = db.get_post_by_id(g.instance_db_path, post_id)

    # Check if post exists and belongs to the current user
    if post is None or post['user_id'] != current_user.id:
        flash('Post not found or you do not have permission to edit it.', 'danger')
        return redirect(url_for('blog.admin_dashboard', subdomain=g.subdomain)) # Redirect to admin dashboard

    form = PostForm() # Initialize form

    if form.validate_on_submit():
        try:
            # Update post
            update_post(
                g.instance_db_path,
                post_id,
                form.title.data,
                form.content.data,
                form.tags.data
            )
            flash('Post updated successfully!', 'success')
            # Redirect to the post detail page or admin dashboard
            return redirect(url_for('blog.post_detail', subdomain=g.subdomain, slug=form.generate_slug())) # Redirect using the potentially new slug
        except Exception as e:
            flash(f'Error updating post: {e}', 'danger')
    elif request.method == 'GET':
        # Pre-populate the form with existing post data on GET request
        form.title.data = post['title']
        form.content.data = post['content']
        # Fetch and populate tags
        tags = db.get_tags_for_post(g.instance_db_path, post_id)
        form.tags.data = ', '.join([tag['name'] for tag in tags])


    return render_template('blog/create_edit_post.html', form=form, action='edit', post=post, subdomain=g.subdomain, random_posts=g.get('random_posts', []))

@blog_bp.route('/admin/posts/delete/<int:post_id>', methods=['POST']) # Use POST for deletion
@login_required
def delete_post_route(post_id):
    """Handles deleting a post."""
    if not g.is_blog_instance or not g.instance_db_path:
        return redirect(url_for('platform.index'))

    # Fetch the post to be deleted
    post = db.get_post_by_id(g.instance_db_path, post_id)

    # Check if post exists and belongs to the current user
    if post is None or post['user_id'] != current_user.id:
        flash('Post not found or you do not have permission to delete it.', 'danger')
        return redirect(url_for('blog.admin_dashboard', subdomain=g.subdomain)) # Redirect to admin dashboard

    try:
        # Delete post
        delete_post(g.instance_db_path, post_id)
        flash('Post deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting post: {e}', 'danger')

    return redirect(url_for('blog.admin_dashboard', subdomain=g.subdomain)) # Redirect back to admin dashboard


@blog_bp.route('/admin/comments/approve/<int:comment_id>')
@login_required
def approve_comment(comment_id):
    """Approves a pending comment."""
    if not g.is_blog_instance or not g.instance_db_path:
        return redirect(url_for('platform.index'))

    try:
        # Approve comment
        approve_comment(g.instance_db_path, comment_id, current_user.id)
        flash('Comment approved.', 'success')
    except Exception as e:
        flash(f'Error approving comment: {e}', 'danger')

    return redirect(url_for('blog.admin_dashboard', subdomain=g.subdomain)) # Redirect back to admin dashboard

# Login/Logout Routes
from werkzeug.security import check_password_hash # Import check_password_hash
from flask_login import login_user, logout_user, current_user # Import login_user, logout_user, current_user

@blog_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Blog owner login page."""
    if not g.is_blog_instance or not g.instance_db_path:
        return redirect(url_for('platform.index'))

    # If user is already logged in for this instance, redirect to admin dashboard
    # This requires a working user_loader that can identify the user for the current instance
    # For now, a basic check:
    if current_user.is_authenticated and hasattr(current_user, 'instance_db_path') and current_user.instance_db_path == g.instance_db_path:
         return redirect(url_for('blog.admin_dashboard', subdomain=g.subdomain))


    form = LoginForm() # Initialize form
    if form.validate_on_submit():
        # Authenticate user against instance DB
        user_id = authenticate_user(g.instance_db_path, form.email.data, form.password.data)

        if user_id:
            # Store the instance database path in the session for the user_loader
            session['instance_db_path'] = g.instance_db_path

            # Create a User object for Flask-Login
            user = User(user_id, g.instance_db_path) # Pass instance_db_path to User constructor

            login_user(user) # Log the user in

            # Redirect to the page they were trying to access or admin dashboard
            next_page = request.args.get('next')
            return redirect(next_page or url_for('blog.admin_dashboard', subdomain=g.subdomain))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('blog/login.html', form=form, subdomain=g.subdomain, random_posts=g.get('random_posts', []))

from flask_login import login_required, logout_user # Ensure logout_user is imported

@blog_bp.route('/logout')
@login_required
def logout():
    """Logs out the blog owner."""
    if not g.is_blog_instance or not g.instance_db_path:
        return redirect(url_for('platform.index'))

    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('blog.index', subdomain=g.subdomain)) # Redirect to blog homepage

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
