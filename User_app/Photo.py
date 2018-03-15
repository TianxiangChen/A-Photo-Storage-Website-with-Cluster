"""Photo table for MySQL.
Schema is described as:

| pid | uid | origin_pic_path | thumbnail_path | t1_pic_path | t2_pic_path | t3_pic_path |
------------------------------------------------------------------------------------------
| int | int | varchar(120)    | varchar(120)   | varchar(120)| varchar(120)| varchar(120)|
| key |     |                 |                |             |             |             |

All fields are NOT NULL.

This relation (with user table) satisfies Boyce Codd Normal Form.
"""
from app import db


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


