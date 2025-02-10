from flask import render_template, request
from . import admin_bp


@admin_bp.route('/')
def dashboard():
    return render_template('admin/dashboard.html')


@admin_bp.route('/users')
def manage_users():
    return render_template('admin/manage_users.html')


@admin_bp.route('/orders')
def manage_orders():
    return render_template('admin/manage_orders.html')


@admin_bp.route('/menu')
def manage_menu():
    return render_template('admin/manage_menu.html')

