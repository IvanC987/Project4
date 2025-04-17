from flask import render_template, request, redirect, url_for, session, flash
from . import driver_bp
from models import User, OrderHistory, Delivery, db


@driver_bp.route('/')
def driver_home():
    return redirect(url_for('driver.driver_login'))


@driver_bp.route('/login', methods=['GET', 'POST'])
def driver_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, role='driver').first()

        if user and user.password == password:
            session['driver_id'] = user.id
            session['user_role'] = user.role
            return redirect(url_for('driver.dashboard'))
        else:
            flash('Invalid credentials or not a driver.')

    return render_template('driver/login.html')


@driver_bp.route('/dashboard')
def dashboard():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']

    # Get deliveries for this driver (This is the correct data source!)
    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()

    # Use only deliveries table to count stats
    total_assigned = len(deliveries)
    pending_orders = len([d for d in deliveries if d.status == 'pending'])
    out_for_delivery_orders = len([d for d in deliveries if d.status == 'in-transit'])
    completed_orders = len([d for d in deliveries if d.status == 'delivered'])

    return render_template(
        'driver/dashboard.html',
        total_assigned=total_assigned,
        pending_orders=pending_orders,
        out_for_delivery_orders=out_for_delivery_orders,
        completed_orders=completed_orders
    )




@driver_bp.route('/orders')
def view_orders():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    status_filter = request.args.get('status')
    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()
    order_ids = [d.order_id for d in deliveries]
    orders_query = OrderHistory.query.filter(OrderHistory.order_id.in_(order_ids))

    if status_filter:
        orders_query = orders_query.filter_by(status=status_filter)

    orders = orders_query.all()

    return render_template('driver/assigned_orders.html', orders=orders, status_filter=status_filter)


@driver_bp.route('/orders/update', methods=['POST'])
def update_order_status():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()
    order_ids = [d.order_id for d in deliveries]
    orders = OrderHistory.query.filter(OrderHistory.order_id.in_(order_ids)).all()
    updates = 0

    for order in orders:
        key = f"status_{order.order_id}"
        new_status = request.form.get(key)

        if new_status and new_status != order.status:
            order.status = new_status
            updates += 1

    if updates:
        db.session.commit()
        flash(f"Updated {updates} order(s).")
    else:
        flash("No changes were made.")

    return redirect(url_for('driver.view_orders'))


@driver_bp.route('/available')
def available_orders():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    assigned_order_ids = [d.order_id for d in Delivery.query.all()]
    unassigned_orders = OrderHistory.query.filter(~OrderHistory.order_id.in_(assigned_order_ids)).all()

    available_orders = []
    for order in unassigned_orders:
        customer = User.query.get(order.customer_id)
        available_orders.append({
            'order_id': order.order_id,
            'customer_name': customer.username,
            'customer_address': customer.email,
            'items': 'N/A',
            'status': order.status
        })

    return render_template('driver/available_orders.html', orders=available_orders)


@driver_bp.route('/claim/<int:order_id>', methods=['POST'])
def claim_order(order_id):
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    existing = Delivery.query.filter_by(order_id=order_id).first()
    if existing:
        flash('Order already claimed.')
        return redirect(url_for('driver.available_orders'))

    new_delivery = Delivery(driver_id=driver_id, order_id=order_id, status='pending')
    db.session.add(new_delivery)
    db.session.commit()
    flash(f"Successfully claimed order #{order_id}.")
    return redirect(url_for('driver.view_orders'))


@driver_bp.route('/logout')
def driver_logout():
    session.clear()
    return redirect(url_for('driver.driver_login'))
