import mysql.connector
from mysql.connector import errorcode
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get MySQL configuration from environment variables
DB_HOST = os.getenv('MYSQL_HOST', 'localhost')
DB_USER = os.getenv('MYSQL_USER', 'dangocan')
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', 'QuietUptown1801__')
DB_NAME = os.getenv('MYSQL_DATABASE', 'calimara_db')

def get_db_connection(database=None):
    """Establishes and returns a mysql.connector.connection.MySQLConnection.
    
    Args:
        database: Optional database name to connect to. If not provided, connects to the server only.
    
    Returns:
        A MySQL connection object.
    """
    config = {
        'host': DB_HOST,
        'user': DB_USER,
        'password': DB_PASSWORD,
    }
    
    if database:
        config['database'] = database
    
    conn = mysql.connector.connect(**config)
    return conn

def dict_cursor(conn):
    """Creates a cursor that returns rows as dictionaries."""
    cursor = conn.cursor(dictionary=True)
    return cursor

def execute_query(conn_or_db_name, query, args=(), one=False, many=False, commit=False, last_row_id=False):
    """
    A versatile helper for executing SQL queries.

    Args:
        conn_or_db_name: A MySQL connection object or a database name string.
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
    cursor = None
    close_conn = False
    
    try:
        if isinstance(conn_or_db_name, str):
            # If a string is provided, treat it as a database name
            conn = get_db_connection(conn_or_db_name)
            close_conn = True
        else:
            # Otherwise, use the provided connection
            conn = conn_or_db_name
            
        cursor = dict_cursor(conn)
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

    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        if conn and close_conn:
            conn.rollback()
        raise # Re-raise the exception after handling

    finally:
        if cursor:
            cursor.close()
        if conn and close_conn:
            conn.close()

def init_db_from_schema(db_name, schema_file_path):
    """Creates and initializes a database from a .sql schema file."""
    conn_server = None
    conn_db = None
    
    try:
        # Connect to MySQL server (without specifying a database)
        conn_server = get_db_connection()
        cursor_server = dict_cursor(conn_server)
        
        # Create the database if it doesn't exist
        cursor_server.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"Database '{db_name}' checked/created successfully.")
        
        # Close the server connection
        cursor_server.close()
        conn_server.close()
        
        # Connect to the specific database
        conn_db = get_db_connection(db_name)
        cursor_db = dict_cursor(conn_db)
        
        # Execute the schema file
        with open(schema_file_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
            
        # Split the schema into individual statements and execute them
        for statement in schema_sql.split(';'):
            if statement.strip():
                cursor_db.execute(statement)
                
        conn_db.commit()
        print(f"Schema '{schema_file_path}' executed successfully on database '{db_name}'.")
        
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Access denied. Check your MySQL username or password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"Database '{db_name}' does not exist and couldn't be created.")
        else:
            print(f"MySQL Error: {err}")
        raise
    finally:
        if 'cursor_server' in locals() and cursor_server:
            cursor_server.close()
        if conn_server and conn_server.is_connected():
            conn_server.close()
            
        if 'cursor_db' in locals() and cursor_db:
            cursor_db.close()
        if conn_db and conn_db.is_connected():
            conn_db.close()
