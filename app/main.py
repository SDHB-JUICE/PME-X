"""
Main Flask Application
Initializes the Flask app and defines basic routes
"""
from flask import Blueprint, redirect, url_for, render_template
from flask_login import current_user, login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Main route
    If user is logged in, redirect to dashboard
    Otherwise, redirect to login page
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    else:
        return redirect(url_for('auth.login'))

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html', title='About')

@main_bp.route('/documentation')
@login_required
def documentation():
    """Documentation page"""
    return render_template('documentation.html', title='Documentation')

@main_bp.errorhandler(404)
def page_not_found(e):
    """404 error handler"""
    return render_template('errors/404.html'), 404

@main_bp.errorhandler(500)
def internal_server_error(e):
    """500 error handler"""
    return render_template('errors/500.html'), 500