from flask import Flask
webapp = Flask(__name__)

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pymysql

pymysql.install_as_MySQLdb()



db_config = {
    'username': 'root',
    'password': 'ece1779pass',
    'host': 'localhost',
    'database': 'ece1779a2'
}

def get_DB_URL():
    return 'mysql://%s:%s@%s/%s' % (db_config['username'], db_config['password'],
                                    db_config['host'], db_config['database'])


webapp.config['SQLALCHEMY_DATABASE_URI'] = get_DB_URL()
webapp.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
webapp.secret_key = 'ece1779assignment1webserver'
db = SQLAlchemy(webapp)

class Photo(db.Model):
    __tablename__ = 'Photo'
    pid = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, nullable=False)
    origin_pic_path = db.Column(db.String(120), nullable=False)
    thumbnail_path = db.Column(db.String(120), nullable=False)
    t1_pic_path = db.Column(db.String(120), nullable=False)
    t2_pic_path = db.Column(db.String(120), nullable=False)
    t3_pic_path = db.Column(db.String(120), nullable=False)

    def __init__(self, uid, origin_path, thumb_path, t1_path, t2_path, t3_path):
        self.uid = uid
        self.origin_pic_path = origin_path
        self.thumbnail_path = thumb_path
        self.t1_pic_path = t1_path
        self.t2_pic_path = t2_path
        self.t3_pic_path = t3_path

    def __repr__(self):
        return '<Photo id %d, path=%s>' % (self.pid, self.origin_pic_path)

    def __str__(self):
        return self.__repr__()

    def add_to_db(self):
        db.session.add(self)
        db.session.commit()


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


