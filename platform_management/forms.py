from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp, ValidationError
from flask_wtf.recaptcha import RecaptchaField
import sqlite3
import os
from config import Config
from core.db_utils import execute_query

# Define the path to the main database
MAIN_DB_PATH = os.path.join(Config.MAIN_DB_DIRECTORY, 'main.db')

class BlogRegistrationForm(FlaskForm):
    """Form for registering a new blog instance."""
    subdomain = StringField('Subdomain', validators=[
        DataRequired(),
        Length(min=3, max=50),
        Regexp(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', 
               message='Subdomain must be 3-50 characters long, start and end with a letter or number, and contain only lowercase letters, numbers, or hyphens. Hyphens cannot be consecutive or at the very beginning/end.')
    ])
    blog_title = StringField('Blog Title', validators=[DataRequired(), Length(min=1, max=100)])
    owner_username = StringField('Owner Username', validators=[DataRequired(), Length(min=3, max=50)])
    owner_email = StringField('Owner Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    recaptcha = RecaptchaField()
    submit = SubmitField('Create Blog')

    def validate_subdomain(self, field):
        """Custom validator to check if subdomain is already taken."""
        # Check against the main database
        blog = execute_query(
            MAIN_DB_PATH,
            "SELECT 1 FROM blogs WHERE subdomain_name = ?",
            (field.data,),
            one=True
        )
        if blog:
            raise ValidationError('This subdomain is already taken. Please choose a different one.')

    def validate_owner_email(self, field):
        """Custom validator to check if email is already used for another blog owner."""
         # Check against the main database
        blog = execute_query(
            MAIN_DB_PATH,
            "SELECT 1 FROM blogs WHERE owner_email = ?",
            (field.data,),
            one=True
        )
        if blog:
            raise ValidationError('This email address is already associated with a blog.')

    # Note: We don't validate owner_username uniqueness here against all instance DBs
    # as that would be inefficient. Uniqueness will be enforced within each instance DB.
    # However, the owner_email uniqueness check in main.db prevents one person
    # from owning multiple blogs with the same email.
