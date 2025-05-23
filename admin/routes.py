import hashlib
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from . import admin_bp
from models import db, User, OrderHistory, MenuItem


# First page should be admin login, where calling "/" would default to login
@admin_bp.route('/')
def admin_home():
    return redirect(url_for('admin.admin_login'))  # <- redirects us to the admin_login function below


# GET requests: Display the admin login page
# POST requests: For processing info from users
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':  # If users submitted anything e.g. `login` button
        email = request.form['email']  # Get the email
        password = request.form['password']  # Get the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Search DB via matching email and role and getting first match
        user = User.query.filter_by(email=email, role='admin').first()

        if user and user.password == hashed_password:  # If auth is correct, proceed
            if not user.is_active:
                flash("Account is inactive. Contact super-admin.", "error")
                return redirect(url_for('login'))

            session['admin_id'] = user.id  # Store the admin's id
            session['user_role'] = user.role  # And the role, which should be 'admin'
            return redirect(url_for('admin.dashboard'))
        else:  # Else give an error
            flash('Invalid credentials or not an admin.', 'error')

    return render_template('admin/login.html')


# ----------------------------------


@admin_bp.route('/dashboard')  # Main page for admins after auth
def dashboard():
    # Gather the 4 mains stats:
    # total orders, active orders, # of users, and total revenue
    total_orders = OrderHistory.query.count()
    active_orders = OrderHistory.query.filter(OrderHistory.status.in_(['pending', 'preparing'])).count()
    total_customers = User.query.filter_by(role='customer').count()
    revenue = db.session.query(db.func.sum(OrderHistory.total_price)).scalar() or 0.0  # Returns 0.0 if nothing is in order hist

    # Pass result to HTML
    return render_template(
        'admin/dashboard.html',
        total_orders=total_orders,
        active_orders=active_orders,
        total_customers=total_customers,
        total_revenue=round(revenue, 2)
    )


# ----------------------------------


@admin_bp.route('/orders', methods=['GET', 'POST'])
def manage_orders():
    if request.method == 'POST':  # Via confirm updates
        orders = OrderHistory.query.all()  # Gather all orders from order_history table
        updates = 0

        for order in orders:
            key = f"status_{order.order_id}"
            new_status = request.form.get(key)  # Gather the current status, if updated, from the `<select name="status_{{ order.order_id }}">` tag
            if new_status and new_status != order.status:
                order.status = new_status
                updates += 1

        if updates:
            db.session.commit()
            flash(f"Updated {updates} order(s).", "success")
        else:
            flash("No changes were made.", "error")

        return redirect(url_for('admin.manage_orders'))

    # query grabs the values for order_id, username, firstname and lastname. Defaults to '' if not provided, which grabs all
    query = request.args.get('q', '').strip()

    # Status is if user specified an order status, defaults to '' if none is provided (returns all orders, unless query)
    status_filter = request.args.get('status', '').strip()

    # Joins the two tables based on user_id fk and orders them by time (Oldest order first, having higher priority)
    orders = OrderHistory.query.join(User).order_by(OrderHistory.timestamp.asc())

    # Filter by order status
    if status_filter:
        orders = orders.filter(OrderHistory.status == status_filter)

    # Perform text search, though it can be ambiguous at the moment since they're all added together...hmmm...
    # Though it's exact values. Should be fine (?)
    if query:
        orders = orders.filter(
            db.or_(
                db.cast(OrderHistory.order_id, db.String) == query,
                User.username == query,
                User.first_name == query,
                User.last_name == query
            )
        )

    # Grab all orders and return that along with a user_map. Basically a dict, user_id being key, username as value
    orders = orders.all()
    users = User.query.with_entities(User.id, User.username).all()
    user_map = {user.id: user.username for user in users}

    return render_template("admin/manage_orders.html", orders=orders, user_map=user_map)


# ----------------------------------


@admin_bp.route('/menu', methods=['GET', 'POST'])
def manage_menu():
    if request.method == 'POST':  # This is where admins add items to the `menu_item` table in db
        # Gather all the fields in the submitted form
        name = request.form.get('name')
        description = request.form.get('description')
        ingredient = request.form.get('ingredient')
        category = request.form.get('category')
        price = request.form.get('price')

        if not (name and price):  # Name of menu item and price is required
            flash("Name and price are required.")
        else:  # Create the MenuItem object and add it to table
            new_item = MenuItem(
                name=name,
                description=description,
                ingredient=ingredient,
                category=category,
                price=float(price),
                is_available=True
            )
            db.session.add(new_item)
            db.session.commit()
            flash(f"Menu item '{name}' added successfully!", "success")

        return redirect(url_for('admin.manage_menu'))

    # Gather all menu items and pass to manage_menu.html to display it
    menu_items = MenuItem.query.all()
    return render_template("admin/manage_menu.html", menu_items=menu_items)


@admin_bp.route('/menu/update/<int:item_id>', methods=['POST'])  # Only for POST, i.e. user submitted a form
def update_menu_item(item_id):
    item = MenuItem.query.get(item_id)  # Retrieve the item based on item_id
    if item:
        item.name = request.form.get('name')
        item.category = request.form.get('category')
        item.price = float(request.form.get('price'))
        item.description = request.form.get('description')
        item.ingredient = request.form.get('ingredient')
        item.is_available = bool(int(request.form.get('is_available')))

        db.session.commit()  # Update the DB
        flash(f"'{item.name}' updated successfully.", "success")
    else:
        flash("Item not found.", "warning")

    return redirect(url_for('admin.manage_menu'))


@admin_bp.route('/menu/delete/<int:item_id>')
def delete_menu_item(item_id):
    # Retrieve and delete menu item from DB
    item = MenuItem.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash(f"'{item.name}' deleted.", "success")
    else:
        flash("Menu item not found.", "warning")

    return redirect(url_for('admin.manage_menu'))


# ----------------------------------


@admin_bp.route('/users')
def manage_users():
    query = request.args.get('q', '').strip()  # Retrieves the query based on the url. E.g. /admin/users?q=alice

    if query:  # If there is a query, search for it in the users table
        users = User.query.filter(
            (User.username.ilike(f"%{query}%")) |
            (User.email.ilike(f"%{query}%"))
        ).all()
        flash(f"Showing results for '{query}'", "success")
    else:
        users = User.query.all()

    admin_id = session.get('admin_id')
    admin = User.query.get(admin_id)
    current_user_is_owner = admin.is_owner if admin else False

    # Return either queried user or everyone
    return render_template('admin/manage_users.html', users=users, current_user_is_owner=current_user_is_owner)


@admin_bp.route('/users/update_status', methods=['POST'])
def update_user_status():
    users = User.query.all()
    admin_id = session.get('admin_id')
    current_admin = User.query.get(admin_id)
    is_owner = current_admin and current_admin.is_owner

    updates = 0
    for user in users:
        key = f'is_active_{user.id}'
        value = request.form.get(key)

        if value is not None:
            # Only allow updating admins if current user is owner
            if user.role == 'admin' and not is_owner:
                continue

            new_status = (value == 'True')
            if user.is_active != new_status:
                user.is_active = new_status
                updates += 1

    if updates:
        db.session.commit()
        flash(f"{updates} user(s) updated successfully.", "success")
    else:
        flash("No changes made.", "warning")

    return redirect(url_for('admin.manage_users'))


# ----------------------------------


@admin_bp.route('/create', methods=['GET', 'POST'])
def create_users():
    if request.method == 'POST':  # Form submission, where admin created user account
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        role = request.form.get('role')

        if not all([username, email, password, first_name, last_name, phone, address, role]):  # validate all fields are filled
            flash("All fields are required.", "warning")
            return redirect(url_for('admin.create_users'))

        if role not in ['admin', 'driver', 'customer']:  # Make sure account role is one of the three
            flash("Invalid role selected.", "error")
            return redirect(url_for('admin.create_users'))

        # Check if this username or email is already in sue
        existing = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing:
            flash("Username or email already exists.", "warning")
            return redirect(url_for('admin.create_users'))

        # Create new user
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        new_user = User(username=username, email=email, password=hashed_password, first_name=first_name,
                        last_name=last_name, phone=phone, address=address, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash(f"{role} '{username}' created successfully!", "success")
        return redirect(url_for('admin.create_users'))

    admin_id = session.get('admin_id')
    admin = User.query.get(admin_id)
    is_owner = admin.is_owner if admin else False

    # If it's just a GET, then render the html
    return render_template('admin/create_users.html', is_owner=is_owner)


# ----------------------------------


@admin_bp.route('/logout')
def admin_logout():
    # Clear the session info (like id) and redirect to the main login page
    session.clear()
    return redirect(url_for('admin.admin_login'))

