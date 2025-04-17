from flask import render_template, request, redirect, url_for, session, flash
from . import driver_bp
from models import User, OrderHistory, Delivery, db


# First page should be driver login, where calling "/" would default to login
@driver_bp.route('/')
def driver_home():
    return redirect(url_for('driver.driver_login'))  # <- redirects us to the driver_login function below

# LOGIN
@driver_bp.route('/login', methods=['GET', 'POST'])
def driver_login():
    if request.method == 'POST':  # If users submitted anything e.g. `login` button
        email = request.form['email']  # Get the email
        password = request.form['password']  # Get password

         # Search DB via matching email and role and getting first match
        user = User.query.filter_by(email=email, role='driver').first()

        if user and user.password == password:
            session['driver_id'] = user.id
            session['user_role'] = user.role
            return redirect(url_for('driver.dashboard'))
        else: #else get an error
            flash('Invalid credentials or not a driver.')

    return render_template('driver/login.html')

#------------------------------------


# DASHBOARD
@driver_bp.route('/dashboard')  # Main page for drivers after auth
def dashboard():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']

    # Get deliveries assigned to this driver
    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()
    order_ids = [delivery.order_id for delivery in deliveries]

    # Get matching order records
    orders = OrderHistory.query.filter(OrderHistory.order_id.in_(order_ids)).all()

    total_assigned = len(orders)
    pending_orders = len([o for o in orders if o.status == 'pending'])
    out_for_delivery_orders = len([d for d in deliveries if d.status == 'in-transit'])
    completed_orders = len([d for d in deliveries if d.status == 'delivered'])

    return render_template(
        'driver/dashboard.html',
        total_assigned=total_assigned,
        pending_orders=pending_orders,
        out_for_delivery_orders=out_for_delivery_orders,
        completed_orders=completed_orders
    )


#----------------------------------------


# VIEW ORDERS
@driver_bp.route('/orders')
def view_orders():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    status_filter = request.args.get('status')

    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()
    order_ids = [d.order_id for d in deliveries]

    orders = OrderHistory.query.filter(OrderHistory.order_id.in_(order_ids)).all()

    combined_orders = []
    for order in orders:
        delivery = next((d for d in deliveries if d.order_id == order.order_id), None)
        customer = User.query.get(order.customer_id)

        if status_filter and delivery.status != status_filter:
            continue

        combined_orders.append({
            'order_id': order.order_id,
            'customer_name': customer.username if customer else 'Unknown',
            'customer_address': customer.email if customer else 'Unknown',
            'items': 'N/A (for now)',
            'status': delivery.status
        })

    return render_template('driver/order.html', orders=combined_orders, status_filter=status_filter)
#----------------------------------------


# UPDATE ORDER STATUS
@driver_bp.route('/orders/update', methods=['POST'])
def update_order_status():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()
    updates = 0

    for delivery in deliveries:
        key = f"status_{delivery.order_id}"
        new_status = request.form.get(key)

        if new_status and new_status != delivery.status:
            delivery.status = new_status
            updates += 1

    if updates:
        db.session.commit()
        flash(f"Updated {updates} order(s).")
    else:
        flash("No changes were made.")

    return redirect(url_for('driver.view_orders'))


# ----------------------------------------


# LOGOUT: Clear session and redirect
@driver_bp.route('/logout')
def driver_logout():
    session.clear()
    return redirect(url_for('driver.driver_login'))
