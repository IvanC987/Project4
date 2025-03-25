from flask import Blueprint
from flask import Blueprint, redirect, url_for, session, request


# Adds the /admin prefix to the web's route (So no collision with users side)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
def restrict_to_admins():
    # Only allow through only if visiting login. Otherwise it will cause infinite recursion
    # (e.g. login_page -> checks this requirement -> redirectly to login page -> back to checking this, etc.
    if request.endpoint == 'admin.admin_login':
        return

    # Only allow access if logged in AND role is 'admin'
    if session.get('user_role') != 'admin':
        return redirect(url_for('admin.admin_login'))



from . import routes

