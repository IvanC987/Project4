from flask import render_template, request, redirect, url_for, session, flash
from . import driver_bp
from models import User


# First page should be driver login, where calling "/" would default to login
@driver_bp.route('/')
def driver_home():
    return redirect(url_for('driver.driver_login'))  # <- redirects us to the driver_login function below



@driver_bp.route('/login', methods=['GET', 'POST'])
def driver_login():
    if request.method == 'POST':  # If users submitted anything e.g. `login` button
        email = request.form['email']  # Get the email
        password = request.form['password']  # Get the password

        # Search DB via matching email and role and getting first match
        user = User.query.filter_by(email=email, role='driver').first()

        if user and user.password == password:
            session['driver_id'] = user.id
            session['user_role'] = user.role
            return redirect(url_for('driver.dashboard'))
        else:  # Else give an error
            flash('Invalid credentials or not a driver.')

    return render_template('driver/login.html')


@driver_bp.route('/dashboard')  # Main page for drivers after auth
def dashboard():
    return render_template('driver/dashboard.html')

