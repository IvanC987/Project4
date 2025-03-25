from app import app, db
from models import *
from sqlalchemy import text

drop = True
create = True


confirmation = input(f"Confirm:\ndrop={drop}, create={create}: [Y/N]: ")
if confirmation.lower() != "y":
    exit()


with app.app_context():
    if drop:
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.drop_all()
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

    if create:
        db.create_all()

    print("Tables modified successfully!")
