from flask import render_template, request, redirect, url_for, session, flash
from . import driver_bp
from models import User, OrderHistory, db  # Ensure these are correctly imported


#Driver login
@driver_bp.route('/')
def driver_home():
    return redirect(url_for('driver.driver_login'))



# GET requests: Display the admin login page
# POST requests: For processing info from users
@driver_bp.route('/login', methods=['GET', 'POST'])
def driver_login():
    if request.method == 'POST': # If users submitted anything e.g. `login` button
        email = request.form['email'] # Get the email
        password = request.form['password'] #Get password
        
         # Search DB via matching email and role and getting first match

        user = User.query.filter_by(email=email, role='driver').first()

        if user and user.password == password:
            session['driver_id'] = user.id
            session['user_role'] = user.role
            return redirect(url_for('driver.dashboard'))
        else: # Else give an erro
            flash('Invalid credentials or not a driver.')

    return render_template('driver/login.html')



# DASHBOARD

@driver_bp.route('/dashboard')
def dashboard():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    assigned_orders = OrderHistory.query.filter_by(driver_id=driver_id).all()

    # Count orders by status
    total_assigned = len(assigned_orders)
    pending_orders = len([o for o in assigned_orders if o.status == 'pending'])
    out_for_delivery_orders = len([o for o in assigned_orders if o.status == 'out for delivery'])
    completed_orders = len([o for o in assigned_orders if o.status == 'completed'])

    return render_template(
        'driver/dashboard.html',
        total_assigned=total_assigned,
        pending_orders=pending_orders,
        out_for_delivery_orders=out_for_delivery_orders,
        completed_orders=completed_orders
    )


#view order status
@driver_bp.route('/orders')
def view_orders():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    status_filter = request.args.get('status')

    query = OrderHistory.query.filter_by(driver_id=driver_id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    orders = query.all()

    return render_template('driver/orders.html', orders=orders, status_filter=status_filter)


#Order Status
@driver_bp.route('/orders/update', methods=['POST'])
def update_order_status():
    if 'driver_id' not in session:
        return redirect(url_for('driver.driver_login'))

    driver_id = session['driver_id']
    orders = OrderHistory.query.filter_by(driver_id=driver_id).all()
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



# LOGOUT: Clear session and return to login
@driver_bp.route('/logout')
def driver_logout():
    session.clear()
    return redirect(url_for('driver.driver_login'))
