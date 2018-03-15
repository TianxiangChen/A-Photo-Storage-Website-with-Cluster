"""User table for MySQL.
Schema is described as:

| uid | username    | email        | passwd_hash  |
---------------------------------------------------
| int | varchar(80) | varchar(120) | varchar(120) |
| key |             |              |              |

All fields are NOT NULL.

This relation (with photo table) satisfies Boyce Codd Normal Form.
"""
from app import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "User"
    uid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    passwd_hash = db.Column(db.String(120))

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.passwd_hash = self.set_password(password)

    def __repr__(self):
        return '<User %r>' % self.username

    def __str__(self):
        return self.__repr__()

    def add_to_db(self):
        """ Add self to database.

        Add self to the database
        :return: true if successful
        :raise: TODO
        """
        return db.session.add(self)

    def set_password(self, password):
        return generate_password_hash(password, salt_length=8)

    def check_password(self, password):
        return check_password_hash(self.passwd_hash, password)

#db.create_all() # In case user table doesn't exists already. Else remove it.
