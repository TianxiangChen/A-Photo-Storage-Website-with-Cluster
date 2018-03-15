from flask import Flask
from app import db_config
import os
from flask_sqlalchemy import SQLAlchemy
import pymysql

webapp = Flask(__name__)
webapp.secret_key = os.urandom(24)


from app import ec2_functions
from app import s3_examples
from app import main

