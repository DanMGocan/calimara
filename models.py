import os
from flask_login import UserMixin
from core.db_utils import execute_query # Assuming execute_query is general enough

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id
        self.username = None
        self.email = None
        # self.blog_title = None # Blog title is specific to a blog, not directly to a global user
        self.load_data_from_db()

    def load_data_from_db(self):
        """Loads user attributes from the main users table."""
        db_name = os.getenv('MYSQL_DATABASE', 'calimara_db')
        user_data = execute_query(
            db_name, 
            "SELECT username, email FROM users WHERE id = %s",
            (self.id,),
            one=True
        )
        if user_data:
            self.username = user_data['username']
            self.email = user_data['email']
            return True
        else:
            # It's important that user_loader returns None if user doesn't exist
            # So, if load_data_from_db fails to find a user, attributes remain None
            print(f"Warning: No user data found for ID {self.id} in main DB.")
            return False
