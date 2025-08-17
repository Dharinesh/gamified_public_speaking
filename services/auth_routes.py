from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import logging

logger = logging.getLogger(__name__)

def create_auth_routes(app, auth_manager):
    auth_bp = Blueprint('auth', __name__)
    
    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Please enter both username and password', 'error')
                return render_template('login.html')
            
            user, error = auth_manager.authenticate_user(username, password)
            if error:
                flash(error, 'error')
                return render_template('login.html')
            
            login_user(user, remember=True)
            flash(f'Welcome back, {user.username}!', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        
        return render_template('login.html')
    
    @auth_bp.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not all([username, email, password, confirm_password]):
                flash('All fields are required', 'error')
                return render_template('register.html')
            
            if len(username) < 3:
                flash('Username must be at least 3 characters long', 'error')
                return render_template('register.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return render_template('register.html')
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('register.html')
            
            # Create user
            user_id, error = auth_manager.create_user(username, email, password)
            if error:
                flash(error, 'error')
                return render_template('register.html')
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        
        return render_template('register.html')
    
    @auth_bp.route('/logout')
    @login_required
    def logout():
        username = current_user.username
        logout_user()
        flash(f'Goodbye, {username}!', 'success')
        return redirect(url_for('auth.login'))
    
    app.register_blueprint(auth_bp, url_prefix='/auth')