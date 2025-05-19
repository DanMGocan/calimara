import sqlite3
from core.db_utils import execute_query

def get_user_by_email(db_path, email):
    """Retrieves a user record from the instance database by email."""
    query = "SELECT * FROM users WHERE email = ?"
    args = (email,)
    return execute_query(db_path, query, args, one=True)

def get_user_by_id(db_path, user_id):
    """Retrieves a user record from the instance database by ID."""
    query = "SELECT * FROM users WHERE id = ?"
    args = (user_id,)
    return execute_query(db_path, query, args, one=True)

def create_post(db_path, user_id, title, slug, content):
    """Creates a new post in the instance database."""
    query = """
    INSERT INTO posts (user_id, title, slug, content)
    VALUES (?, ?, ?, ?)
    """
    args = (user_id, title, slug, content)
    return execute_query(db_path, query, args, commit=True, last_row_id=True)

def get_all_posts(db_path):
    """Retrieves all posts from the instance database."""
    query = "SELECT * FROM posts ORDER BY creation_timestamp DESC"
    return execute_query(db_path, query, many=True)

def get_post_by_slug(db_path, slug):
    """Retrieves a single post from the instance database by slug."""
    query = "SELECT * FROM posts WHERE slug = ?"
    args = (slug,)
    return execute_query(db_path, query, args, one=True)

def update_post(db_path, post_id, title, slug, content):
    """Updates an existing post in the instance database."""
    query = """
    UPDATE posts
    SET title = ?, slug = ?, content = ?, last_modified_timestamp = CURRENT_TIMESTAMP
    WHERE id = ?
    """
    args = (title, slug, content, post_id)
    execute_query(db_path, query, args, commit=True)

def delete_post(db_path, post_id):
    """Deletes a post from the instance database."""
    query = "DELETE FROM posts WHERE id = ?"
    args = (post_id,)
    execute_query(db_path, query, args, commit=True)

def create_tag(db_path, name, slug):
    """Creates a new tag in the instance database."""
    query = "INSERT OR IGNORE INTO tags (name, slug) VALUES (?, ?)"
    args = (name, slug)
    execute_query(db_path, query, args, commit=True)
    # Need to get the ID of the tag, whether inserted or ignored
    return execute_query(db_path, "SELECT id FROM tags WHERE slug = ?", (slug,), one=True)['id']


def add_post_tags(db_path, post_id, tag_ids):
    """Adds entries to the post_tags table."""
    query = "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)"
    args_list = [(post_id, tag_id) for tag_id in tag_ids]
    # Using executemany for efficiency
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.executemany(query, args_list)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error during add_post_tags: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_tags_for_post(db_path, post_id):
    """Retrieves tags associated with a post."""
    query = """
    SELECT t.name, t.slug
    FROM tags t
    JOIN post_tags pt ON t.id = pt.tag_id
    WHERE pt.post_id = ?
    """
    args = (post_id,)
    return execute_query(db_path, query, args, many=True)

def add_comment(db_path, post_id, commenter_name, commenter_email, content):
    """Adds a new comment to the instance database."""
    query = """
    INSERT INTO comments (post_id, commenter_name, commenter_email, content)
    VALUES (?, ?, ?, ?)
    """
    args = (post_id, commenter_name, commenter_email, content)
    return execute_query(db_path, query, args, commit=True, last_row_id=True)

def get_comments_for_post(db_path, post_id):
    """Retrieves all comments for a post."""
    query = "SELECT * FROM comments WHERE post_id = ? ORDER BY submission_timestamp ASC"
    args = (post_id,)
    return execute_query(db_path, query, args, many=True)

def get_approved_comments_for_post(db_path, post_id):
    """Retrieves approved comments for a post."""
    query = "SELECT * FROM comments WHERE post_id = ? AND is_approved = 1 ORDER BY submission_timestamp ASC"
    args = (post_id,)
    return execute_query(db_path, query, args, many=True)

def get_pending_comments(db_path):
    """Retrieves all pending comments for the admin dashboard."""
    query = """
    SELECT c.*, p.title AS post_title
    FROM comments c
    JOIN posts p ON c.post_id = p.id
    WHERE c.is_approved = 0
    ORDER BY c.submission_timestamp ASC
    """
    return execute_query(db_path, query, many=True)

def approve_comment(db_path, comment_id, approved_by_user_id):
    """Approves a comment."""
    query = "UPDATE comments SET is_approved = 1, approved_by_user_id = ? WHERE id = ?"
    args = (approved_by_user_id, comment_id)
    execute_query(db_path, query, args, commit=True)

def delete_comment(db_path, comment_id):
    """Deletes a comment."""
    query = "DELETE FROM comments WHERE id = ?"
    args = (comment_id,)
    execute_query(db_path, query, args, commit=True)

def add_like(db_path, post_id, liker_identifier):
    """Adds a like to a post."""
    query = "INSERT OR IGNORE INTO likes (post_id, liker_identifier) VALUES (?, ?)"
    args = (post_id, liker_identifier)
    execute_query(db_path, query, args, commit=True)

def get_like_count_for_post(db_path, post_id):
    """Gets the number of likes for a post."""
    query = "SELECT COUNT(*) FROM likes WHERE post_id = ?"
    args = (post_id,)
    result = execute_query(db_path, query, args, one=True)
    return result[0] if result else 0

def increment_post_view_count(db_path, post_id):
    """Increments the view count for a post."""
    query = "UPDATE posts SET view_count = view_count + 1 WHERE id = ?"
    args = (post_id,)
    execute_query(db_path, query, args, commit=True)

def get_posts_with_stats(db_path):
    """Retrieves posts with their view and like counts for the admin dashboard."""
    query = """
    SELECT p.*,
           (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count,
           (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id AND c.is_approved = 0) AS pending_comment_count
    FROM posts p
    ORDER BY p.creation_timestamp DESC
    """
    return execute_query(db_path, query, many=True)

# Add other instance database interaction functions as needed
