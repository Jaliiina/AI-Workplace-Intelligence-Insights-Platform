from app import app
from models import db, UserQuery

with app.app_context():
    print(UserQuery.query.order_by(UserQuery.id.desc()).limit(5).all())
