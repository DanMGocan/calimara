import mysql.connector
from core.db_utils import execute_query, get_db_connection # get_db_connection might not be needed if execute_query handles it

# Note: All functions will now operate on the main database (db_name)
# and use blog_id to scope data where appropriate.

def get_user_by_email(db_name, email): # User lookup is global
    """Retrieves a user record from the main users table by email."""
    query = "SELECT * FROM users WHERE email = %s" # users table is global
    args = (email,)
    return execute_query(db_name, query, args, one=True)

def get_user_by_id(db_name, user_id): # User lookup is global
    """Retrieves a user record from the main users table by ID."""
    query = "SELECT * FROM users WHERE id = %s" # users table is global
    args = (user_id,)
    return execute_query(db_name, query, args, one=True)

# For posts, tags, comments, likes, we need blog_id to scope them.
# The 'posts' table in mysql_schema.sql already has a 'blog_id' column.

def create_post(db_name, blog_id, user_id, title, slug, content):
    """Creates a new post for a specific blog."""
    query = """
    INSERT INTO posts (blog_id, user_id, title, slug, content)
    VALUES (%s, %s, %s, %s, %s)
    """
    args = (blog_id, user_id, title, slug, content)
    return execute_query(db_name, query, args, commit=True, last_row_id=True)

def get_all_posts(db_name, blog_id):
    """Retrieves all posts for a specific blog."""
    query = "SELECT * FROM posts WHERE blog_id = %s ORDER BY creation_timestamp DESC"
    args = (blog_id,)
    return execute_query(db_name, query, args, many=True)

def get_post_by_slug(db_name, blog_id, slug):
    """Retrieves a single post for a specific blog by slug."""
    query = "SELECT * FROM posts WHERE blog_id = %s AND slug = %s"
    args = (blog_id, slug)
    return execute_query(db_name, query, args, one=True)

def get_post_by_id(db_name, blog_id, post_id): # Added for edit/delete scenarios
    """Retrieves a single post for a specific blog by its ID."""
    query = "SELECT * FROM posts WHERE blog_id = %s AND id = %s"
    args = (blog_id, post_id)
    return execute_query(db_name, query, args, one=True)

def update_post(db_name, blog_id, post_id, title, slug, content):
    """Updates an existing post for a specific blog."""
    query = """
    UPDATE posts
    SET title = %s, slug = %s, content = %s, last_modified_timestamp = CURRENT_TIMESTAMP
    WHERE id = %s AND blog_id = %s
    """
    args = (title, slug, content, post_id, blog_id)
    execute_query(db_name, query, args, commit=True)

def delete_post(db_name, blog_id, post_id):
    """Deletes a post for a specific blog."""
    # CASCADE DELETE on foreign keys in comments, likes, post_tags should handle related data
    query = "DELETE FROM posts WHERE id = %s AND blog_id = %s"
    args = (post_id, blog_id)
    execute_query(db_name, query, args, commit=True)

# Tags are global in the current mysql_schema.sql (name is UNIQUE).
# If tags should be per-blog, the schema needs adjustment. Assuming global for now.
def create_tag(db_name, name, slug):
    """Creates a new tag (globally)."""
    query = "INSERT IGNORE INTO tags (name, slug) VALUES (%s, %s)"
    args = (name, slug)
    execute_query(db_name, query, args, commit=True)
    return execute_query(db_name, "SELECT id FROM tags WHERE slug = %s", (slug,), one=True)['id']

def add_post_tags(db_name, post_id, tag_ids): # blog_id not strictly needed if post_id is globally unique
    """Adds entries to the post_tags table."""
    query = "INSERT INTO post_tags (post_id, tag_id) VALUES (%s, %s)"
    args_list = [(post_id, tag_id) for tag_id in tag_ids]
    # Using executemany for efficiency, execute_query might need adjustment or direct connection use
    conn = get_db_connection(db_name)
    cursor = None # Define cursor before try block
    try:
        cursor = conn.cursor()
        cursor.executemany(query, args_list)
        conn.commit()
    except mysql.connector.Error as e:
        print(f"Database error during add_post_tags: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_tags_for_post(db_name, post_id): # blog_id not strictly needed if post_id is globally unique
    """Retrieves tags associated with a post."""
    query = """
    SELECT t.name, t.slug
    FROM tags t
    JOIN post_tags pt ON t.id = pt.tag_id
    WHERE pt.post_id = %s
    """
    args = (post_id,)
    return execute_query(db_name, query, args, many=True)

def add_comment(db_name, post_id, commenter_name, commenter_email, content): # post_id is global
    """Adds a new comment to a post."""
    query = """
    INSERT INTO comments (post_id, commenter_name, commenter_email, content)
    VALUES (%s, %s, %s, %s)
    """
    args = (post_id, commenter_name, commenter_email, content)
    return execute_query(db_name, query, args, commit=True, last_row_id=True)

def get_comments_for_post(db_name, post_id): # post_id is global
    """Retrieves all comments for a post."""
    query = "SELECT * FROM comments WHERE post_id = %s ORDER BY submission_timestamp ASC"
    args = (post_id,)
    return execute_query(db_name, query, args, many=True)

def get_approved_comments_for_post(db_name, post_id): # post_id is global
    """Retrieves approved comments for a post."""
    query = "SELECT * FROM comments WHERE post_id = %s AND is_approved = 1 ORDER BY submission_timestamp ASC"
    args = (post_id,)
    return execute_query(db_name, query, args, many=True)

def get_pending_comments(db_name, blog_id):
    """Retrieves all pending comments for a specific blog for the admin dashboard."""
    query = """
    SELECT c.*, p.title AS post_title
    FROM comments c
    JOIN posts p ON c.post_id = p.id
    WHERE p.blog_id = %s AND c.is_approved = 0
    ORDER BY c.submission_timestamp ASC
    """
    args = (blog_id,)
    return execute_query(db_name, query, args, many=True)

def approve_comment(db_name, comment_id, approved_by_user_id): # comment_id is global
    """Approves a comment."""
    # Consider adding a check to ensure the comment belongs to a post on the admin's blog
    query = "UPDATE comments SET is_approved = 1, approved_by_user_id = %s WHERE id = %s"
    args = (approved_by_user_id, comment_id)
    execute_query(db_name, query, args, commit=True)

def delete_comment(db_name, comment_id): # comment_id is global
    """Deletes a comment."""
    # Consider adding a check to ensure the comment belongs to a post on the admin's blog
    query = "DELETE FROM comments WHERE id = %s"
    args = (comment_id,)
    execute_query(db_name, query, args, commit=True)

def add_like(db_name, post_id, liker_identifier): # post_id is global
    """Adds a like to a post."""
    query = "INSERT IGNORE INTO likes (post_id, liker_identifier) VALUES (%s, %s)"
    args = (post_id, liker_identifier)
    execute_query(db_name, query, args, commit=True)

def get_like_count_for_post(db_name, post_id): # post_id is global
    """Gets the number of likes for a post."""
    query = "SELECT COUNT(*) FROM likes WHERE post_id = %s"
    args = (post_id,)
    result = execute_query(db_name, query, args, one=True)
    return result['COUNT(*)'] if result else 0 # MySQL COUNT(*) returns as a key

def increment_post_view_count(db_name, post_id): # post_id is global
    """Increments the view count for a post."""
    query = "UPDATE posts SET view_count = view_count + 1 WHERE id = %s"
    args = (post_id,)
    execute_query(db_name, query, args, commit=True)

def get_posts_with_stats(db_name, blog_id):
    """Retrieves posts for a specific blog with their view and like counts for the admin dashboard."""
    query = """
    SELECT p.*,
           (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count,
           (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id AND c.is_approved = 0) AS pending_comment_count
    FROM posts p
    WHERE p.blog_id = %s
    ORDER BY p.creation_timestamp DESC
    """
    args = (blog_id,)
    return execute_query(db_name, query, args, many=True)

# Add other instance database interaction functions as needed
