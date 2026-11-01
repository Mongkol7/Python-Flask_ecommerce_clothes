import sys
from app import app
from extensions import db
from models.users import User
from werkzeug.security import generate_password_hash

def set_admin(username="admin", password="123", email="admin@gmail.com"):
    with app.app_context():
        db.create_all()
        user = User.query.filter((User.username == username) | (User.email == email)).first()
        if user:
            user.password = generate_password_hash(password)
            user.role = "admin"
            db.session.commit()
            print(f"SUCCESS: Updated admin user '{user.username}' with new password '{password}'.")
        else:
            user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                role="admin"
            )
            db.session.add(user)
            db.session.commit()
            print(f"SUCCESS: Created new admin user '{username}' with password '{password}' and role 'admin'.")

        print("\n--- All Users Currently in Database ---")
        for u in User.query.all():
            print(f" • ID: {u.id} | Username: {u.username} | Email: {u.email} | Role: {u.role}")
        print("---------------------------------------")

if __name__ == "__main__":
    u = sys.argv[1] if len(sys.argv) > 1 else "admin"
    p = sys.argv[2] if len(sys.argv) > 2 else "123456"
    e = sys.argv[3] if len(sys.argv) > 3 else f"{u}@gmail.com"
    set_admin(u, p, e)
