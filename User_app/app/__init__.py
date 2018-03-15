from flask import Flask
webapp = Flask(__name__)

from flask_sqlalchemy import SQLAlchemy
from app.db_config import get_DB_URL
import os

import pymysql

pymysql.install_as_MySQLdb()

webapp.config['SQLALCHEMY_DATABASE_URI'] = get_DB_URL()
webapp.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
webapp.secret_key = 'ece1779assignment1webserver'

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE_STORE = "ece1779fall2017a2"
TMP_FOLDER = os.path.join(APP_ROOT, 'user_data', 'images')

print(IMAGE_STORE)
if not os.path.isdir(IMAGE_STORE):
    os.makedirs(IMAGE_STORE, exist_ok=True)
S3_ADDR = "https://s3.amazonaws.com/" + IMAGE_STORE + '/'

db = SQLAlchemy(webapp)

import Lab2

webapp.secret_key = 'ECE1779Winter2017BestTeam'

