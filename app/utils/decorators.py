from functools import wraps
from flask import abort, redirect, url_for, request, jsonify
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            return redirect(url_for('auth.admin_login', next=request.path))
        
        if current_user.role not in ['admin', 'super_admin']:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Admin privileges required'}), 403
            return redirect(url_for('products.home'))
            
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            return redirect(url_for('auth.admin_login', next=request.path))
        
        if current_user.role != 'super_admin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Super Admin privileges required'}), 403
            # If it's a page, maybe just flash a message and redirect back
            from flask import flash
            flash('This action requires Super Admin permissions.', 'error')
            return redirect(request.referrer or url_for('admin.dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function
