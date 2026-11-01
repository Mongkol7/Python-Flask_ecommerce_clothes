from extensions import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    profile = db.Column(db.String(120))
    role = db.Column(db.String(80), nullable=False, server_default="user")

    def __init__(self, username, email, password, role="user", profile=None):
        self.username = username
        self.email = email
        self.password = password
        self.role = role
        self.profile = profile
