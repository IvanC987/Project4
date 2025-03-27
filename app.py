from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from config import Config
from admin import admin_bp


app = Flask(__name__)
app.config.from_object(Config)

# Importing here to avoid the circular import err
from models import db, User

db.init_app(app)

app.register_blueprint(admin_bp)





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

            return redirect(url_for('home'))

        flash("Invalid credentials, please try again.")

    return render_template("customer/login.html")


@app.route("/menu")
def menu():
    menu_items = [
        {"id": 1, "item": "Cheese Burger", "price": 5.99},
        {"id": 2, "item": "Chocolate Cake", "price": 3.99}
        # And add more later on, this is just a test
    ]
    return render_template("customer/menu.html", menu=menu_items)


@app.route("/cart")
def view_cart():
    total_price = sum([item["price"] for item in cart_items])  # Total price would be dependent on the items in the cart, which would be retrieved from the DB
    return render_template("customer/cart.html", cart=cart_items, total=total_price)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        order_data = request.form  # Capture form input
        # Store order in database (to be implemented)
        return "Order placed successfully!"
    return render_template("customer/checkout.html")


if __name__ == '__main__':
    cart_items = [{"id": 1, "item": "Cheese Burger", "price": 5.99}]

    app.run(debug=True)
