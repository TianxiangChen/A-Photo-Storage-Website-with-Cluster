from flask_wtf import Form, validators
from wtforms import StringField, TextAreaField, SubmitField, PasswordField,FileField
from wtforms.validators import required, ValidationError, email
from flask_wtf.file import FileAllowed, FileRequired
from app import db, webapp
from User import User


class SignupForm(Form):
    username = StringField("Username", [required("Please enter your username.")])
    email = StringField("Email", [required("Please enter your email address."),
                                email("Please a valid email address.")])
    password = PasswordField('Password', [required("Please enter a password.")])
    conf_password = PasswordField('Confirm password', [required("Please confirm password.")])
    submit = SubmitField("Create account")

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        validate = True

        if not Form.validate(self):
            validate = False

        user = User.query.filter_by(username = self.username.data.lower()).first()
        if user:
            self.username.errors.append("That username is already taken")
            validate = False

        user = User.query.filter_by(email = self.email.data.lower()).first()
        if user:
            self.email.errors.append("That email is registered to another user")
            validate = False

        if self.conf_password.data != self.password.data:
            self.password.errors.append("Password entered not identical")
            validate = False

        return validate


class SigninForm(Form):
    username = StringField("Username", [required("Please enter your username.")])
    password = PasswordField('Password', [required("Please enter a password.")])
    submit = SubmitField("Sign In")

    def __int__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        if not Form.validate(self):
            return False

        user = User.query.filter_by(username=self.username.data).first()

        if user and user.check_password(self.password.data):
            return True
        else:
            self.username.errors.append("Invalid username or password")
            return False

class ForgotPwForm(Form):
    email = StringField("Email", [required("Please enter your email address."),
                                email("Please a valid email address.")])

    def __int__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        if not Form.validate(self):
            return False

        user = User.query.filter_by(email=self.email.data).first()

        if user:
            return True
        else:
            self.username.errors.append("User does not exist")
            return False

class EasyUploadForm(Form):
    userID = StringField("Username", [required("Please enter your username.")])
    password = PasswordField('Password', [required("Please enter a password.")])
    uploadedfile = FileField('File', validators=[FileRequired()])
    submit = SubmitField("Upload")

    def __int__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        if not Form.validate(self):
            return False

        user = User.query.filter_by(username=self.userID.data).first()

        if user and user.check_password(self.password.data):
            return True
        else:
            self.userID.errors.append("Invalid username or password")
            return False
