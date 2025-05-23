from datetime import datetime
from zoneinfo import ZoneInfo
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
    roll- Role of the user. Currently have "customer", "delivery", "admin" atm
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    role = db.Column(
        db.Enum('customer', 'admin', 'driver', name='user_role_enum'),
        nullable=False,
    )

    # Adding in new attributes
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_owner = db.Column(db.Boolean, default=False, nullable=False)

class MenuItem(db.Model):
    """
    Stores all items on our menu

    item_id: Unique identifier for each item.
    name: Name of the menu item.
    description: A short description for the item.
    ingredient: Comma-separated list of ingredients.
    price: Price of the item.
    category: Used to filter menu (e.g., Entree, Dessert, Drink).
    is_available: If the item is available to order or not.
    """

    item_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    ingredient = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    image_url = db.Column(db.String(255)) 


class OrderHistory(db.Model):
    """
    Stores all user orders.

    order_id: Unique identifier for each order (PK)
    customer_id: FK to User table
    total_price: Final price after order is placed
    status: Order progress (e.g., pending → preparing → completed)
    timestamp: When the order was placed
    """

    order_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    total_price = db.Column(db.Float, nullable=False)

    status = db.Column(
        # Choose only from the ones below. Seems to be braod enough, though might add more later?
        db.Enum('pending', 'preparing', 'completed', 'canceled', 'in-transit', 'delivered', name='order_status_enum'),
        default='pending',
        nullable=False
    )

    special_instructions = db.Column(db.String(255), nullable=True)  # Can be null

    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("America/Chicago")), nullable=False)

    # Adding relationship between order and user for admin info
    user = db.relationship('User', backref='orders')


class OrderItem(db.Model):
    """
    Stores info about orders more specifically.

    order_id- FK of OrderHistory.id
    item_id- FK of MenuItem.id
    quantity- How many items were order for a particular menu item for an order
    """

    order_id = db.Column(db.Integer, db.ForeignKey('order_history.order_id'), primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_item.item_id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)


class Delivery(db.Model):
    """
    Tracks delivery status of each order.

    driver_id- This is the user_id, so both fk and pk here
    order_id- fk from the OrderHistory table's order_id attribute
    status- Current status of the delivery order
    delivery_time- When the order was delivered
    """

    # Together acts as composite key
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)  # fk
    order_id = db.Column(db.Integer, db.ForeignKey('order_history.order_id'), primary_key=True)  # also fk

    # status = db.Column(
    #     db.Enum('pending', 'in-transit', 'delivered', 'canceled'),
    #     default='pending',
    #     nullable=False
    # )

    # Adjusted status to remove pending and canceled
    status = db.Column(
        db.Enum('in-transit', 'delivered', name='delivery_status_enum'),
        default='in-transit',
        nullable=False
    )

    delivery_time = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("America/Chicago")), nullable=False)
