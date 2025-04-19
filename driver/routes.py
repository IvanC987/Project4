from flask import render_template, request, redirect, url_for, session, flash
from . import driver_bp
from models import User, OrderHistory, Delivery, OrderItem, MenuItem, db

# Redirect "/" to login page
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

    # Get all deliveries assigned to this driver
    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()

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

# ----------------------------------

# View all assigned orders
@driver_bp.route('/orders')
def view_orders():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    status_filter = request.args.get('status')

    # Get all deliveries assigned to this driver
    deliveries = Delivery.query.filter_by(driver_id=driver_id).all()
    order_ids = [d.order_id for d in deliveries]

    # Get all orders for those IDs
    orders = OrderHistory.query.filter(OrderHistory.order_id.in_(order_ids)).all()

    combined_orders = []
    for order in orders:
        delivery = next((d for d in deliveries if d.order_id == order.order_id), None)
        customer = User.query.get(order.customer_id)

        if not customer:
            continue

        # Get all items for the order
        order_items = OrderItem.query.filter_by(order_id=order.order_id).all()
        item_lines = []
        for item in order_items:
            menu_item = MenuItem.query.get(item.item_id)
            if menu_item:
                item_lines.append(f"{menu_item.name} x{item.quantity}")
        item_description = ", ".join(item_lines) if item_lines else "No Items"

        # Filter for the deliver status
        if status_filter and delivery and delivery.status != status_filter:
            continue

        combined_orders.append({
            'order_id': order.order_id,
            'customer_name': customer.username,
            'customer_address': '', #address not found?
            'items': item_description,  
            'status': delivery.status if delivery else 'pending'
        })

    return render_template('driver/assigned_orders.html', orders=combined_orders, status_filter=status_filter)

# ----------------------------------

# Update status of assigned orders
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
            delivery.status = new_status  # <-- Update Delivery table status
            updates += 1

    if updates:
        db.session.commit()
        flash(f"Updated {updates} order(s).")
    else:
        flash("No changes were made.")

    return redirect(url_for('driver.view_orders'))

# ----------------------------------

# View available orders to claim
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

    new_delivery = Delivery(driver_id=driver_id, order_id=order_id, status='pending')
    db.session.add(new_delivery)
    db.session.commit()
    flash(f"Successfully claimed order #{order_id}.")
    return redirect(url_for('driver.view_orders'))

# ----------------------------------

#Logout
@driver_bp.route('/logout')
def driver_logout():
    session.clear()
    return redirect(url_for('driver.driver_login'))
