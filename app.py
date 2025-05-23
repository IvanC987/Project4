import hashlib
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from config import Config
from admin import admin_bp
from driver import driver_bp
from models import User, MenuItem, OrderHistory, db, OrderItem
from collections import defaultdict, Counter


app = Flask(__name__)  # Create flask app instance
app.config.from_object(Config)  # Configures the instance based on the Config class in config.py

db.init_app(app)

app.register_blueprint(admin_bp)  # Connects to admin routes
app.register_blueprint(driver_bp)  # Connects to driver routes


@app.route("/")  # Main "home" route
def home():
    return render_template("customer/index.html")


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        address = request.form.get('address')


        # A simple check for dedup of whether a user already exist with that email/username
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash("User already exists with that email or username.", "error")
            return redirect(url_for('signup'))

        # Else, add this new user to DB after hashing password (64 hexidecimal chars)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        new_user = User(username=username, email=email, password=hashed_password, first_name=first_name,
                        last_name=last_name, phone=phone, address=address, role="customer")
        db.session.add(new_user)
        db.session.commit()

        # Bug: Forgot to set session info before
        session['user_id'] = new_user.id
        session['username'] = new_user.username

        # redirects to menu
        return redirect(url_for('menu'))
        

    # If GET request, just load signup html
    return render_template("customer/signup.html")


@app.route("/login", methods=['GET', 'POST'])
def login():  # Very similar to signup
    if request.method == 'POST':
        identifier = request.form.get('username_or_email').strip()
        password = request.form.get('password').strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()

        if user and user.password == hashed_password and user.role == "customer":
            if not user.is_active:
                flash("Account is inactive. Contact admin.", "error")
                return redirect(url_for('login'))

            session['user_id'] = user.id
            session['username'] = user.username

            return redirect(url_for('menu'))

        flash("Invalid credentials, please try again.", "error")

    return render_template("customer/login.html")

@app.route('/menu')
def menu():
    available_items = MenuItem.query.filter_by(is_available=True).all()

    menu_by_category = defaultdict(list)
    for item in available_items:
        menu_by_category[item.category].append(item)

    menu_layout = ['Appetizer', 'Salad', 'Entree', 'Barbecue', 'Seafood', 'Side', 'Dessert', 'Drink']
    all_categories = set(menu_by_category.keys())
    other_categories = all_categories - set(menu_layout)
    sorted_categories = menu_layout + sorted(other_categories)

    return render_template('customer/menu.html', menu=menu_by_category, category_order=sorted_categories)

# Only available as a POST method since we're adding items to cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    print("Add to cart hit!")
    if 'cart' not in session:
        session['cart'] = []

    data = request.get_json()
    print("Data received:", data)
    item_id = data.get('item_id')

    item = MenuItem.query.get(item_id)
    if item:
        session['cart'].append(item_id)
        session.modified = True
        return jsonify({"message": f"{item.name} added to cart!"})
    else:
        return jsonify({"message": "Item not found"}), 404



@app.route("/cart")
def view_cart():
    cart_ids = session.get('cart', [])

    # Count duplicates (for quantities)
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
        session['cart'] = [id for id in session['cart'] if id != item_id]
        session.modified = True

    return jsonify({'message': 'Item removed from cart'})


@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    data = request.get_json()
    item_id = data.get('item_id')
    new_quantity = data.get('quantity')

    if 'cart' not in session:
        return jsonify({'success': False, 'message': 'Cart not found'}), 400

    # Filter out all instances of the item
    session['cart'] = [id for id in session['cart'] if id != item_id]

    # Add back the item with the new quantity
    session['cart'].extend([item_id] * new_quantity)
    session.modified = True

    return jsonify({'success': True})



@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:  # Ensure user is logged in
        return redirect(url_for('login'))


    user_id = session['user_id']  # Get the user ID from session
    if request.method == 'POST':
        # Capture the form data for checkout
        instructions = request.form.get('instructions')
        tip_percent = float(request.form.get('tip', 0))

        # Check if cart exists in session
        if 'cart' not in session:
            flash("Your cart is empty!", "error")
            return redirect(url_for('menu'))  # Redirect to menu if cart is empty

        cart_ids = session.get('cart', [])

        # Get the list of menu items based on cart item IDs
        cart_count = Counter(cart_ids)
        items = MenuItem.query.filter(MenuItem.item_id.in_(cart_count.keys())).all()

        # Calculate the total price
        subtotal = sum(item.price * cart_count[item.item_id] for item in items)
        tax = subtotal * 0.07
        tip = subtotal * tip_percent
        total_price = subtotal + tax + tip

        # Create a new order in the OrderHistory table
        new_order = OrderHistory(
            customer_id=user_id,
            total_price=round(total_price, 2),
            status='pending',
            special_instructions=instructions 
        )
        db.session.add(new_order)
        db.session.commit()

        # Add the items to the OrderItem table
        for item in items:
            quantity = cart_count[item.item_id]
            order_item = OrderItem(order_id=new_order.order_id, item_id=item.item_id, quantity=quantity)
            db.session.add(order_item)

        db.session.commit()  # Commit the order items

        # Clear the cart after placing the order
        session.pop('cart', None)

        flash("Order placed successfully!", "success")
        return redirect(url_for('order_status'))  # Redirect to the order status page


    # If GET: show form and compute total
    cart_ids = session.get('cart', [])
    cart_count = Counter(cart_ids)
    items = MenuItem.query.filter(MenuItem.item_id.in_(cart_count.keys())).all()
    total = sum(item.price * cart_count[item.item_id] for item in items)

    return render_template("customer/checkout.html", total=round(total, 2))


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

@app.route('/logout')
def logout():
    # Clear the session to log out the user
    session.clear()
    
    # Redirect the user to the homepage or login page after logging out
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
