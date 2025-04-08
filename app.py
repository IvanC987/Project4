from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from config import Config
from admin import admin_bp
from driver import driver_bp
from models import User, MenuItem, OrderHistory, db, OrderItem
from flask import render_template
from flask import jsonify


app = Flask(__name__)
app.config.from_object(Config)

# Importing here to avoid the circular import err
from models import db, User

db.init_app(app)

app.register_blueprint(admin_bp)
app.register_blueprint(driver_bp)




@app.route("/")
def home():
    return render_template("customer/index.html")


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # A simple check for dedup of whether a user already exist with that email/username
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash("User already exists with that email or username.")
            return redirect(url_for('signup'))

        new_user = User(username=username, email=email, password=password, role="customer")
        db.session.add(new_user)
        db.session.commit()

        return "Signup successful!"

    return render_template("customer/signup.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session['user_id'] = user.id
            session['username'] = user.username

            return redirect(url_for('menu'))

        flash("Invalid credentials, please try again.")

    return render_template("customer/login.html")


@app.route('/menu')
def menu():
    # Get only available items
    available_items = MenuItem.query.filter_by(is_available=True).all()
    return render_template('customer/menu.html', menu=available_items)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'cart' not in session:
        session['cart'] = []

    data = request.get_json()
    item_id = data.get('item_id')

    # Optional: check if item exists in database before adding
    item = MenuItem.query.get(item_id)
    if item:
        session['cart'].append(item_id)
        session.modified = True  # needed to track changes to session list
        return jsonify({"message": f"{item.name} added to cart!"})
    else:
        return jsonify({"message": "Item not found"}), 404



@app.route("/cart")
def view_cart():
    cart_ids = session.get('cart', [])
    
    # If you're storing duplicates for quantity, count them
    from collections import Counter
    cart_count = Counter(cart_ids)

    # Get all unique item objects
    items = MenuItem.query.filter(MenuItem.item_id.in_(cart_count.keys())).all()

    # Build cart items with quantities
    cart = []
    total_price = 0
    for item in items:
        quantity = cart_count[item.item_id]
        item_total = item.price * quantity
        total_price += item_total
        cart.append({
            "id": item.item_id,
            "name": item.name,
            "price": item.price,
            "quantity": quantity,
            "total": item_total
        })

    return render_template("customer/cart.html", cart=cart, total=round(total_price, 2))

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    data = request.get_json()
    item_id = data.get('item_id')

    if 'cart' in session:
        try:
            session['cart'].remove(item_id)
            session.modified = True
        except ValueError:
            pass  # item not in cart

    return jsonify({'message': 'Item removed from cart'})



@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:  # Ensure user is logged in
        return redirect(url_for('login'))

    user_id = session['user_id']  # Get the user ID from session
    if request.method == 'POST':
        # Capture the form data for checkout (e.g., name, address, phone)
        name = request.form.get('name')
        address = request.form.get('address')
        phone = request.form.get('phone')
        
        # Check if cart exists in session
        if 'cart' not in session:
            flash("Your cart is empty!")
            return redirect(url_for('menu'))  # Redirect to menu if cart is empty

        cart_ids = session.get('cart', [])
        
        # Get the list of menu items based on cart item IDs
        from collections import Counter
        cart_count = Counter(cart_ids)
        items = MenuItem.query.filter(MenuItem.item_id.in_(cart_count.keys())).all()

        # Calculate the total price
        total_price = sum(item.price * cart_count[item.item_id] for item in items)
        
        # Create a new order in the OrderHistory table
        new_order = OrderHistory(customer_id=user_id, total_price=total_price, status='pending')
        db.session.add(new_order)
        db.session.commit()  # Commit to get the order ID for later use

        # Add the items to the OrderItem table
        for item in items:
            quantity = cart_count[item.item_id]
            order_item = OrderItem(order_id=new_order.order_id, item_id=item.item_id, quantity=quantity)
            db.session.add(order_item)
        
        db.session.commit()  # Commit the order items
        
        # Clear the cart after placing the order
        session.pop('cart', None)
        
        flash("Order placed successfully!")
        return redirect(url_for('order_status'))  # Redirect to the order status page

    return render_template("customer/checkout.html")


@app.route("/order_status")
def order_status():
    if 'user_id' not in session:  # Ensure the user is logged in
        return redirect(url_for('login'))

    user_id = session['user_id']  # Get the user ID from the session
    orders = OrderHistory.query.filter_by(customer_id=user_id).all() or []  # Query all orders for the logged-in user

    order_details = []
    for order in orders:
        order_items = OrderItem.query.filter_by(order_id=order.order_id).all()
        items = []
        for item in order_items:
            menu_item = MenuItem.query.get(item.item_id)
            items.append({
                "name": menu_item.name,
                "quantity": item.quantity,
                "price": menu_item.price,
                "total": menu_item.price * item.quantity
            })
        order_details.append({
            "order_id": order.order_id,
            "status": order.status,
            "items": items,
            "total_price": order.total_price
        })

    return render_template("customer/order_status.html", orders=order_details)




if __name__ == '__main__':
    cart_items = [{"id": 1, "item": "Cheese Burger", "price": 5.99}]

    app.run(debug=True)
