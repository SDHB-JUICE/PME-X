"""
Authentication Routes
Flask Blueprint for authentication-related routes
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.user import User

# Create blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        # Validate input
        if not username or not password:
            flash('Please enter all fields', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if user exists
        user = User.query.filter_by(username=username).first()
        
        # Check username and password
        if not user or not user.verify_password(password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        # Login user
        login_user(user, remember=remember)
        flash('Login successful', 'success')
        
        # Redirect to requested page or dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        else:
            return redirect(url_for('dashboard.index'))
    
    return render_template('auth/login.html', title='Login')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register route"""
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        # Validate input
        if not username or not email or not password or not password_confirm:
            flash('Please enter all fields', 'danger')
            return redirect(url_for('auth.register'))
        
        if password != password_confirm:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if username or email already exists
        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()
        
        if user_exists:
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
        
        if email_exists:
            flash('Email already exists', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password=password
        )
        
        # Add user to database
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout route"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile route"""
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        # Update email if changed
        if email != current_user.email:
            # Check if email already exists
            email_exists = User.query.filter_by(email=email).first()
            
            if email_exists:
                flash('Email already exists', 'danger')
                return redirect(url_for('auth.profile'))
            
            # Update email
            current_user.email = email
            flash('Email updated successfully', 'success')
        
        # Update password if provided
        if current_password and new_password:
            # Verify current password
            if not current_user.verify_password(current_password):
                flash('Current password is incorrect', 'danger')
                return redirect(url_for('auth.profile'))
            
            # Update password
            current_user.password = new_password
            flash('Password updated successfully', 'success')
        
        # Update telegram settings
        current_user.telegram_enabled = True if request.form.get('telegram_enabled') else False
        
        # Update max gas price
        max_gas_price = request.form.get('max_gas_price')
        if max_gas_price:
            current_user.max_gas_price = float(max_gas_price)
        
        # Update auto reinvest
        current_user.auto_reinvest = True if request.form.get('auto_reinvest') else False
        
        # Update risk level
        risk_level = request.form.get('risk_level')
        if risk_level in ['low', 'medium', 'high']:
            current_user.risk_level = risk_level
        
        # Save changes
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', title='Profile')