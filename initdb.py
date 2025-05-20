import mysql.connector
from mysql.connector import errorcode
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
        # The MySQL connector's execute method can handle a string containing multiple statements
        # if the 'multi' parameter is True. It returns an iterator of cursors for each statement.
        results = cursor.execute(sql_script_content, multi=True)
        
        for i, res in enumerate(results):
            print(f"Executed statement {i+1}: {res.statement}")
            if res.rowcount > 0:
                print(f"  {res.rowcount} rows affected.")
        
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
