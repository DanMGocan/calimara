import sqlite3
import os

def get_db_connection(db_path):
    """Establishes and returns a sqlite3.Connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

def execute_query(db_path_or_conn, query, args=(), one=False, many=False, commit=False, last_row_id=False):
    """
    A versatile helper for executing SQL queries.

    Args:
        db_path_or_conn: Path to the database file or an existing connection object.
        query: The SQL query string.
        args: A tuple of arguments to substitute into the query.
        one: If True, fetch a single row.
        many: If True, fetch all rows.
        commit: If True, commit the transaction.
        last_row_id: If True, return the last inserted row ID.

    Returns:
        The result of the query (single row, list of rows, last row ID, or None).
    """
    conn = None
    try:
        if isinstance(db_path_or_conn, str):
            conn = get_db_connection(db_path_or_conn)
            cursor = conn.cursor()
        else:
            conn = db_path_or_conn
            cursor = conn.cursor()

        cursor.execute(query, args)

        if commit:
            conn.commit()

        if last_row_id:
            return cursor.lastrowid
        elif one:
            return cursor.fetchone()
        elif many:
            return cursor.fetchall()
        else:
            return None # For INSERT, UPDATE, DELETE without last_row_id

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn and isinstance(db_path_or_conn, str): # Only rollback if we opened the connection here
             conn.rollback()
        raise # Re-raise the exception after handling

    finally:
        if conn and isinstance(db_path_or_conn, str): # Only close if we opened the connection here
            conn.close()


def init_db_from_schema(db_path, schema_file_path):
    """Creates and initializes a database from a .sql schema file."""
    if not os.path.exists(db_path):
        # Ensure the directory exists before creating the DB file
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        conn = None
        try:
            conn = get_db_connection(db_path)
            with open(schema_file_path, 'r') as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
            print(f"Database initialized at {db_path} using {schema_file_path}")
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    else:
        print(f"Database already exists at {db_path}")
