from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()



class User(db.Model):
    """
    This would be the main table in the MariaDB that holds all user infos

    Each user would have:
    id- The primary key for this table
    username- This would be the username of the user when they need to login
    email- Their email
    password- User's password
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)


class MenuItem(db.Model):
    """
    Thinking about using name is PK, but considering item name might change, it would be a pain to update

    id- The primary key for this table
    name- Name of menu it
    price- Price of a certain menu item
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)


class OrderHistory(db.Model):
    """
    This table stores all the orders placed by everyone

    id- Unique order id, PK
    customer_id- FK, references user ids
    """

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class OrderItem(db.Model):
    """
    Stores info about orders more specifically.

    order_id- FK of OrderHistory.id
    menu_item_id- FK of MenuItem.id
    quantity- How many items were order for a particular menu item for an order
    """

    order_id = db.Column(db.Integer, db.ForeignKey('order_history.id'), primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)


class Staff(db.Model):
    """
    Stores staff info

    staff_id- ID of the staff member
    """

    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)


class Delivery(db.Model):
    """
    Tracks the delivery orders

    order_id- ID of the particular order
    driver_id- ID of the driver, FK linked to Staff.staff_id
    """

    order_id = db.Column(db.Integer, db.ForeignKey('order_history.id'), primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('staff.staff_id'), nullable=False)
