from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, Email, ValidationError
from flask_wtf.recaptcha import RecaptchaField
import re # For slug generation (basic)

class PostForm(FlaskForm):
    """Form for creating and editing blog posts."""
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    tags = StringField('Tags (comma-separated)', validators=[Length(max=100)]) # Optional tags
    submit = SubmitField('Save Post')

    def generate_slug(self):
        """Generates a URL-friendly slug from the post title."""
        # Basic slug generation: lowercase, replace spaces/non-alphanumeric with hyphens
        slug = self.title.data.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')


class CommentForm(FlaskForm):
    """Form for submitting comments on a post."""
    commenter_name = StringField('Name', validators=[DataRequired(), Length(min=1, max=100)])
    commenter_email = StringField('Email (Optional)', validators=[Email()]) # Email is optional
    content = TextAreaField('Comment', validators=[DataRequired()])
    recaptcha = RecaptchaField()
    submit = SubmitField('Post Comment')

class LoginForm(FlaskForm):
    """Form for blog owner login."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
