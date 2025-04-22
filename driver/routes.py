from flask import render_template, request, redirect, url_for, session, flash
from . import driver_bp
from models import User, OrderHistory, Delivery, OrderItem, MenuItem, db

# Redirect to login
@driver_bp.route('/')
def driver_home():
    return redirect(url_for('driver.driver_login'))

# ----------------------------------

# Driver login
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

# ----------------------------------

# Driver dashboard
@driver_bp.route('/dashboard')
def dashboard():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()

    total_assigned = len(deliveries)
    out_for_delivery_orders = len([d for d in deliveries if d.status == 'in-transit'])
    completed_orders = len([d for d in deliveries if d.status == 'delivered'])

    return render_template('driver/dashboard.html',
                           total_assigned=total_assigned,
                           out_for_delivery_orders=out_for_delivery_orders,
                           completed_orders=completed_orders)

# ----------------------------------

# View assigned orders
@driver_bp.route('/orders')
def view_orders():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()
    combined_orders = []

    for delivery in deliveries:
        order = OrderHistory.query.get(delivery.order_id)
        customer = User.query.get(order.customer_id)

        combined_orders.append({
            'order_id': order.order_id,
            'customer_name': customer.username,
            'customer_address': customer.address,
            'status': delivery.status,
        })

    return render_template('driver/assigned_orders.html', orders=combined_orders)

# ----------------------------------

# Update status
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

            order = OrderHistory.query.get(delivery.order_id)
            if order:
                if new_status == 'in-transit':
                    order.status = 'in-transit'
                elif new_status == 'delivered':
                    order.status = 'delivered'

    if updates:
        db.session.commit()
        flash(f"Updated {updates} order(s).")
    else:
        flash("No changes were made.")

    return redirect(url_for('driver.view_orders'))



# ----------------------------------

@driver_bp.route('/completed_orders')
def completed_orders():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']

    # Pull only completed (delivered) deliveries
    deliveries = Delivery.query.filter_by(driver_id=driver_id, status='delivered').all()
    completed_orders = []

    for delivery in deliveries:
        order = OrderHistory.query.get(delivery.order_id)
        customer = User.query.get(order.customer_id)

        completed_orders.append({
            'order_id': order.order_id,
            'customer_name': customer.username,
            'customer_address': customer.address,
            'status': delivery.status
        })

    return render_template('driver/completed_orders.html', orders=completed_orders)

#-----------------------------

@driver_bp.route('/completed_orders/update', methods=['POST'])
def update_completed_orders():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    deliveries = Delivery.query.filter_by(driver_id=driver_id, status='delivered').all()
    updates = 0

    for delivery in deliveries:
        key = f"status_{delivery.order_id}"
        new_status = request.form.get(key)

        if new_status and new_status != delivery.status:
            delivery.status = new_status
            updates += 1

            # Update the order history too
            order = OrderHistory.query.get(delivery.order_id)
            if order:
                if new_status == 'in-transit':
                    order.status = 'in-transit'
                elif new_status == 'delivered':
                    order.status = 'delivered'

    if updates:
        db.session.commit()
        flash(f"Updated {updates} completed order(s).")
    else:
        flash("No changes were made.")

    return redirect(url_for('driver.completed_orders'))

#----------------------------------------------------

# Drop assigned order
@driver_bp.route('/orders/drop/<int:order_id>', methods=['POST'])
def drop_order(order_id):
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    delivery = Delivery.query.filter_by(driver_id=driver_id, order_id=order_id).first()

    if delivery:
        db.session.delete(delivery)
        db.session.commit()
        flash(f"Order #{order_id} dropped successfully.")
    else:
        flash("No matching order found.")

    return redirect(url_for('driver.view_orders'))

# ----------------------------------

# View available orders
@driver_bp.route('/available')
def available_orders():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    assigned_order_ids = [d.order_id for d in Delivery.query.all()]

    unassigned_orders = OrderHistory.query.filter(
        ~OrderHistory.order_id.in_(assigned_order_ids),
        OrderHistory.status == 'completed'
    ).all()

    available_orders = []
    for order in unassigned_orders:
        customer = User.query.get(order.customer_id)
        available_orders.append({
            'order_id': order.order_id,
            'customer_name': customer.username,
            'customer_address': customer.address,
            'status': order.status
        })

    return render_template('driver/available_orders.html', orders=available_orders)

# ----------------------------------

# Claim an available order
@driver_bp.route('/claim/<int:order_id>', methods=['POST'])
def claim_order(order_id):
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    existing = Delivery.query.filter_by(order_id=order_id).first()
    if existing:
        flash('Order already claimed.')
        return redirect(url_for('driver.available_orders'))

    new_delivery = Delivery(driver_id=driver_id, order_id=order_id, status='in-transit')
    db.session.add(new_delivery)
    db.session.commit()
    flash(f"Successfully claimed order #{order_id}.")
    return redirect(url_for('driver.view_orders'))

# ----------------------------------

# Info page
@driver_bp.route('/orders/<int:order_id>/info')
def order_info(order_id):
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    order = OrderHistory.query.get(order_id)
    customer = User.query.get(order.customer_id)
    items = OrderItem.query.filter_by(order_id=order_id).all()

    detailed_items = []
    for item in items:
        menu_item = MenuItem.query.get(item.item_id)
        if menu_item:
            detailed_items.append({
                'name': menu_item.name,
                'quantity': item.quantity,
                'price': menu_item.price,
                'total': menu_item.price * item.quantity
            })

    return render_template('driver/order_info.html', order=order, customer=customer, items=detailed_items)

# ----------------------------------

# Logout
@driver_bp.route('/logout')
def driver_logout():
    session.clear()
    return redirect(url_for('driver.driver_login'))
