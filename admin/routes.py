from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from . import admin_bp
from models import db, User, OrderHistory


# First page should be admin login, where calling "/" would default to login
@admin_bp.route('/')
def admin_home():
    return redirect(url_for('admin.admin_login'))


# GET requests: Display the admin login page
# POST requests: For processing info from users
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':  # If users submitted anything e.g. `login` button
        email = request.form['email']  # Get the email
        password = request.form['password']  # Get the password

        # Search DB via matching email and role and getting first match
        user = User.query.filter_by(email=email, role='admin').first()

        if user and user.password == password:  # If auth is correct, proceed
            session['admin_id'] = user.id  # Store the admin's id
            session['user_role'] = user.role  # And the role, which should be 'admin'
            return redirect(url_for('admin.dashboard'))
        else:  # Else give an error
            flash('Invalid credentials or not an admin.')

    return render_template('admin/login.html')


@admin_bp.route('/dashboard')
def dashboard():
    # Gather the 4 mains stats:
    # total orders, active orders, # of users, and total revenue
    total_orders = OrderHistory.query.count()
    active_orders = OrderHistory.query.filter(OrderHistory.status.in_(['pending', 'preparing'])).count()
    total_customers = User.query.filter_by(role='customer').count()
    revenue = db.session.query(db.func.sum(OrderHistory.total_price)).scalar() or 0.0

    return render_template(
        'admin/dashboard.html',
        total_orders=total_orders,
        active_orders=active_orders,
        total_users=total_customers,
        total_revenue=round(revenue, 2)
    )


@admin_bp.route('/create-admin')
def create_admin():
    # For creating other admin users
    return render_template('admin/create_admin.html')


@admin_bp.route('/users')
def manage_users():
    return render_template('admin/manage_users.html')


@admin_bp.route('/orders', methods=['GET', 'POST'])
def manage_orders():
    if request.method == 'POST':
        orders = OrderHistory.query.all()
        updates = 0

        for order in orders:
            key = f"status_{order.order_id}"
            new_status = request.form.get(key)
            if new_status and new_status != order.status:
                order.status = new_status
                updates += 1

        if updates:
            db.session.commit()
            flash(f"✅ Updated {updates} order(s).")
        else:
            flash("No changes were made.")

        return redirect(url_for('admin.manage_orders'))


    orders = OrderHistory.query.all()
    users = User.query.with_entities(User.id, User.username).all()
    user_map = {user.id: user.username for user in users}

    return render_template("admin/manage_orders.html", orders=orders, user_map=user_map)



@admin_bp.route('/menu')
def manage_menu():
    return render_template('admin/manage_menu.html')


@admin_bp.route('/logout')
def admin_logout():
    # Clear the session info (like id) and redirect to the main login page
    session.clear()
    return redirect(url_for('admin.admin_login'))


