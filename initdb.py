import mysql.connector
from mysql.connector import errorcode
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# For password hashing
from werkzeug.security import generate_password_hash
# For slug generation (if needed, or use a simpler one)
import re

DB_HOST = os.getenv('MYSQL_HOST', 'localhost')
DB_USER = os.getenv('MYSQL_USER', 'dangocan')
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', 'QuietUptown1801__')
DB_NAME = os.getenv('MYSQL_DATABASE', 'calimara_db')
# Updated default path for schema file in root
SCHEMA_FILE_PATH = os.getenv('MYSQL_SCHEMA_PATH', 'mysql_schema.sql') 

def create_database_if_not_exists(cursor, db_name):
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"Database '{db_name}' checked/created successfully.")
    except mysql.connector.Error as err:
        print(f"Failed creating database '{db_name}': {err}")
        exit(1)

def execute_schema_from_file(cnx, cursor, schema_file_path):
    try:
        with open(schema_file_path, 'r', encoding='utf-8') as f:
            sql_script_content = f.read()
        
        print(f"Executing schema from '{schema_file_path}'...")
        # Split the SQL script into individual statements and execute them one by one
        statements = sql_script_content.split(';')
        
        for i, statement in enumerate(statements):
            if statement.strip():
                cursor.execute(statement)
                print(f"Executed statement {i+1}")
                if cursor.rowcount > 0:
                    print(f"  {cursor.rowcount} rows affected.")
        
        cnx.commit() # Commit after all statements are executed
        print(f"Schema '{schema_file_path}' executed successfully on database '{DB_NAME}'.")

    except FileNotFoundError:
        print(f"Error: Schema file not found at '{schema_file_path}'.")
        exit(1)
    except mysql.connector.Error as err:
        print(f"Failed to execute schema: {err}")
        if cnx and cnx.is_connected():
            try:
                cnx.rollback()
                print("Transaction rolled back due to schema execution error.")
            except Exception as rb_err:
                print(f"Error during rollback: {rb_err}")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during schema execution: {e}")
        if cnx and cnx.is_connected():
            cnx.rollback()
        exit(1)

def main():
    cnx_server = None
    cnx_db = None
    try:
        print(f"Connecting to MySQL server at {DB_HOST}...")
        cnx_server = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=True 
        )
        cursor_server = cnx_server.cursor()
        print("Connected to MySQL server.")

        create_database_if_not_exists(cursor_server, DB_NAME)
        cursor_server.close()
        cnx_server.close()
        print("Server connection closed after database check/creation.")

        print(f"Connecting to database '{DB_NAME}' at {DB_HOST}...")
        cnx_db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME, # Connect directly to the target DB
            autocommit=False 
        )
        cursor_db = cnx_db.cursor()
        print(f"Connected to database '{DB_NAME}'.")

        execute_schema_from_file(cnx_db, cursor_db, SCHEMA_FILE_PATH)
        
        # --- Add default data ---
        print("Adding default data...")
        try:
            # 1. Create default user
            default_username = 'dan'
            default_email = 'dan@dan.dan'
            default_password = '123'
            hashed_password = generate_password_hash(default_password)
            
            sql_insert_user = "INSERT INTO users (username, email, password_hash, account_activated) VALUES (%s, %s, %s, %s)"
            user_values = (default_username, default_email, hashed_password, True)
            cursor_db.execute(sql_insert_user, user_values)
            default_user_id = cursor_db.lastrowid
            print(f"Default user '{default_username}' created with ID: {default_user_id}")

            # 2. Create default blog
            default_blog_subdomain = 'dangocan'
            default_blog_title = 'Blogul lui Dănuț'
            
            sql_insert_blog = "INSERT INTO blogs (subdomain_name, blog_title, owner_user_id, owner_email) VALUES (%s, %s, %s, %s)"
            blog_values = (default_blog_subdomain, default_blog_title, default_user_id, default_email)
            cursor_db.execute(sql_insert_blog, blog_values)
            default_blog_id = cursor_db.lastrowid
            print(f"Default blog '{default_blog_subdomain}' created with ID: {default_blog_id}")

            # 3. Create default post
            default_post_title = 'Lorem Ipsum Dolor Sit Amet'
            # Basic slug generation for the default post
            default_post_slug = default_post_title.lower()
            default_post_slug = re.sub(r'[^a-z0-9\s-]', '', default_post_slug)
            default_post_slug = re.sub(r'\s+', '-', default_post_slug)
            default_post_slug = re.sub(r'-+', '-', default_post_slug)
            default_post_slug = default_post_slug.strip('-')
            
            default_post_content = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'
            
            sql_insert_post = "INSERT INTO posts (blog_id, user_id, title, slug, content, is_published) VALUES (%s, %s, %s, %s, %s, %s)"
            post_values = (default_blog_id, default_user_id, default_post_title, default_post_slug, default_post_content, True)
            cursor_db.execute(sql_insert_post, post_values)
            default_post_id = cursor_db.lastrowid
            print(f"Default post '{default_post_title}' created with ID: {default_post_id} for blog ID: {default_blog_id}")

            cnx_db.commit()
            print("Default data added and committed successfully.")

        except mysql.connector.Error as err:
            print(f"Failed to add default data: {err}")
            if cnx_db and cnx_db.is_connected():
                try:
                    cnx_db.rollback()
                    print("Transaction rolled back due to default data insertion error.")
                except Exception as rb_err:
                    print(f"Error during rollback: {rb_err}")
            exit(1)
        except Exception as e:
            print(f"An unexpected error occurred while adding default data: {e}")
            if cnx_db and cnx_db.is_connected():
                cnx_db.rollback()
            exit(1)
        # --- End of adding default data ---

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Access denied. Check your MySQL username or password in .env file.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"Database '{DB_NAME}' does not exist and couldn't be created or accessed.")
        elif err.errno == errorcode.CR_CONN_HOST_ERROR:
            print(f"Failed to connect to MySQL host '{DB_HOST}'. Ensure MySQL server is running and accessible.")
        else:
            print(f"MySQL Error: {err}")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}")
        exit(1)
    finally:
        if 'cursor_server' in locals() and cursor_server:
            try:
                cursor_server.close()
            except Exception as e:
                print(f"Error closing server cursor: {e}")
        if cnx_server and cnx_server.is_connected():
            cnx_server.close()
            # print("MySQL server connection (for DB creation check) closed.")
        
        if 'cursor_db' in locals() and cursor_db:
            try:
                cursor_db.close()
            except Exception as e:
                print(f"Error closing database cursor: {e}")
        if cnx_db and cnx_db.is_connected():
            cnx_db.close()
            print(f"MySQL connection to database '{DB_NAME}' closed.")

if __name__ == '__main__':
    main()
