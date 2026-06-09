from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user, fresh_login_required
from app.models import User, Product, Order, Review, Coupon, Announcement, SiteSetting, ChatbotLog, ProductImage, Wishlist, OrderItem
from app import db
import os
from flask import current_app
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def check_admin():
    # Skip for static files and login route
    if request.endpoint and ('static' in request.endpoint or 'login' in request.endpoint):
        return
        
    if not current_user.is_authenticated:
        return redirect(url_for('auth.admin_login', next=request.path))
        
    if current_user.role not in ['admin', 'super_admin']:
        return redirect(url_for('products.home'))

@admin_bp.route('/notifications/read-all')
@login_required
def read_all_notifications():
    from app.models import Notification
    Notification.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(request.referrer or url_for('admin.dashboard'))

@admin_bp.route('/notifications/<int:id>/read')
@login_required
def read_notification(id):
    from app.models import Notification
    notif = Notification.query.get_or_404(id)
    notif.is_read = True
    db.session.commit()
    return redirect(notif.link or url_for('admin.dashboard'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

@admin_bp.route('/dashboard')
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/api/stats')
def api_stats():
    period = request.args.get('period', 'year')
    start_date = datetime.utcnow()
    if period == 'day': start_date -= timedelta(days=1)
    elif period == 'week': start_date -= timedelta(weeks=1)
    elif period == 'month': start_date -= timedelta(days=30)
    else: start_date -= timedelta(days=365)

    # Total Revenue
    total_revenue = db.session.query(db.func.sum(Order.total_jod)).filter(
        Order.created_at >= start_date
    ).scalar() or 0

    # Total Customers (all time)
    total_customers = User.query.filter_by(role='user').count()

    # Average Order Value
    total_orders_count = Order.query.filter(Order.created_at >= start_date).count()
    avg_order_value = (float(total_revenue) / total_orders_count) if total_orders_count > 0 else 0

    # Pending Orders
    pending_orders = Order.query.filter_by(status='pending').count()

    # New Customers Today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_customers_today = User.query.filter(
        User.role == 'user',
        User.created_at >= today_start
    ).count()

    return jsonify({
        'total_revenue': float(total_revenue),
        'total_customers': total_customers,
        'total_orders': total_orders_count,
        'avg_order_value': round(avg_order_value, 3),
        'pending_orders': pending_orders,
        'new_customers_today': new_customers_today
    })

@admin_bp.route('/api/charts/weekly-revenue')
def api_chart_weekly_revenue():
    """Returns revenue per day for the last 7 days."""
    today = datetime.utcnow().date()
    labels = []
    data = []
    day_keys = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        revenue = db.session.query(db.func.sum(Order.total_jod)).filter(
            Order.created_at >= day_start,
            Order.created_at <= day_end
        ).scalar() or 0
        labels.append(day_keys[day.weekday() + 1 if day.weekday() < 6 else 0])  # convert Mon=0 to Sun=0
        data.append(round(float(revenue), 3))
    return jsonify({'labels': labels, 'data': data, 'dataset_label': 'weekly_revenue'})

@admin_bp.route('/api/charts/orders-daily')
def api_chart_orders_daily():
    labels = ["sat", "sun", "mon", "tue", "wed", "thu", "fri"]
    data = [12, 19, 15, 8, 12, 20, 25]
    return jsonify({'labels': labels, 'data': data, 'dataset_label': 'orders_count'})

@admin_bp.route('/api/charts/orders-status')
def api_chart_orders_status():
    period = request.args.get('period', 'year')
    start_date = datetime.utcnow()
    if period == 'day': start_date -= timedelta(days=1)
    elif period == 'week': start_date -= timedelta(weeks=1)
    elif period == 'month': start_date -= timedelta(days=30)
    else: start_date -= timedelta(days=365)
    results = db.session.query(Order.status, db.func.count(Order.id)).filter(
        Order.created_at >= start_date
    ).group_by(Order.status).all()
    labels = [r[0].lower() for r in results]
    data = [r[1] for r in results]
    return jsonify({'labels': labels, 'data': data})

@admin_bp.route('/api/charts/sales-by-category')
def api_chart_sales_by_category():
    """Returns total quantity sold per category via OrderItem joins."""
    results = db.session.query(
        Product.category,
        db.func.sum(OrderItem.quantity)
    ).join(OrderItem, OrderItem.product_id == Product.id
    ).group_by(Product.category
    ).order_by(db.func.sum(OrderItem.quantity).desc()
    ).all()

    category_labels = {
        'necklaces': 'قلائد', 'earrings': 'أقراط', 'bracelets': 'أساور',
        'rings': 'خواتم', 'belly-rings': 'بيرسينج', 'anklets': 'خلاخيل', 'sets': 'أطقم'
    }
    labels_ar = [category_labels.get(r[0], r[0]) for r in results]
    labels_en = [r[0].replace('-', ' ').title() for r in results]
    data = [int(r[1]) for r in results]
    return jsonify({'labels_ar': labels_ar, 'labels_en': labels_en, 'data': data})

@admin_bp.route('/api/charts/delivery-zones')
def api_chart_delivery_zones():
    results = db.session.query(Order.city, db.func.count(Order.id)).group_by(
        Order.city
    ).order_by(db.func.count(Order.id).desc()).limit(5).all()
    labels = [r[0] for r in results]
    data = [r[1] for r in results]
    return jsonify({'labels': labels, 'data': data})

@admin_bp.route('/api/charts/top-products')
def api_chart_top_products():
    """Top 5 best-selling by sales_count, enriched with OrderItem quantities."""
    results = db.session.query(
        Product,
        db.func.coalesce(db.func.sum(OrderItem.quantity), 0).label('qty_sold')
    ).outerjoin(OrderItem, OrderItem.product_id == Product.id
    ).group_by(Product.id
    ).order_by(db.text('qty_sold DESC')
    ).limit(5).all()

    return jsonify({
        'products': [{
            'id': p.id,
            'name_ar': p.name_ar,
            'name_en': p.name_en,
            'category': p.category,
            'primary_image': p.primary_image or '',
            'sales_count': int(qty)
        } for p, qty in results]
    })

@admin_bp.route('/api/products')
def api_get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    material = request.args.get('material', '')
    stock_status = request.args.get('stock_status', 'all')
    on_sale = request.args.get('on_sale', 'false').lower() == 'true'
    
    query = Product.query
    
    if search:
        term = f'%{search}%'
        query = query.filter(Product.name_ar.ilike(term) | Product.name_en.ilike(term))
        
    if category:
        query = query.filter_by(category=category)
        
    if material:
        query = query.filter_by(material=material)
        
    if stock_status == 'in_stock':
        query = query.filter(Product.stock_qty > 0)
    elif stock_status == 'out_of_stock':
        query = query.filter(Product.stock_qty <= 0)
        
    if on_sale:
        query = query.filter(Product.is_on_sale == True)
        
    pagination = query.order_by(Product.id.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'products': [{
            'id': p.id,
            'name_ar': p.name_ar,
            'name_en': p.name_en,
            'category': p.category,
            'price_jod': float(p.price_jod or 0),
            'is_on_sale': p.is_on_sale,
            'sale_price_jod': float(p.sale_price_jod) if p.sale_price_jod else None,
            'material': p.material,
            'stock_qty': p.stock_qty or 0,
            'is_visible': p.is_visible,
            'primary_image': p.primary_image
        } for p in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages
    })

@admin_bp.route('/products')
def products():
    return render_template('admin/products.html')

@admin_bp.route('/products/new', methods=['GET', 'POST'])
def new_product():
    if request.method == 'POST':
        # Simple implementation for now, usually would handle file uploads etc.
        data = request.form
        p = Product(
            name_ar=data.get('name_ar'),
            name_en=data.get('name_en'),
            description_ar=data.get('description_ar'),
            description_en=data.get('description_en'),
            price_jod=float(data.get('price_jod')),
            category=data.get('category'),
            material=data.get('material'),
            stock_qty=int(data.get('stock_qty', 0))
        )
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin.products'))
    return render_template('admin/product_form.html', product=None)

@admin_bp.route('/products/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    p = Product.query.get_or_404(id)
    if request.method == 'POST':
        data = request.form
        p.name_ar = data.get('name_ar')
        p.name_en = data.get('name_en')
        p.description_ar = data.get('description_ar')
        p.description_en = data.get('description_en')
        p.price_jod = float(data.get('price_jod'))
        p.category = data.get('category')
        p.material = data.get('material')
        p.stock_qty = int(data.get('stock_qty', 0))
        db.session.commit()
        return redirect(url_for('admin.products'))
    return render_template('admin/product_form.html', product=p)

@admin_bp.route('/api/products', methods=['POST'])
def api_create_product():
    data = request.get_json()
    p = Product(
        name_ar=data.get('name_ar'),
        name_en=data.get('name_en'),
        category=data.get('category'),
        material=data.get('material'),
        price_jod=data.get('price_jod'),
        is_on_sale=data.get('is_on_sale', False),
        sale_price_jod=data.get('sale_price_jod'),
        length=data.get('length'),
        size=data.get('size'),
        stone=data.get('stone'),
        weight=data.get('weight'),
        stock_qty=data.get('stock_qty', 0),
        is_new=data.get('is_new', False),
        is_visible=data.get('is_visible', True),
        description_ar=data.get('description_ar'),
        description_en=data.get('description_en'),
        care_ar=data.get('care_ar'),
        care_en=data.get('care_en')
    )
    
    images_data = data.get('images', [])
    has_primary = any(img.get('is_primary') for img in images_data)
    for idx, img in enumerate(images_data):
        is_primary = img.get('is_primary', False)
        if not has_primary and idx == 0:
            is_primary = True
        pi = ProductImage(
            image_path=img['path'],
            is_primary=is_primary,
            sort_order=idx
        )
        p.images.append(pi)
        
    db.session.add(p)
    db.session.commit()
    return jsonify({'success': True, 'id': p.id})

@admin_bp.route('/api/products/<int:id>', methods=['PUT', 'DELETE'])
def api_edit_product(id):
    p = Product.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(p)
        db.session.commit()
        return jsonify({'success': True})
    
    data = request.get_json()
    if 'is_visible' in data and len(data) <= 2:
        # Handling bulk toggle or quick toggle
        p.is_visible = data['is_visible']
        if 'stock_qty' in data: p.stock_qty = data['stock_qty']
    else:
        # Full update
        if 'name_ar' in data: p.name_ar = data['name_ar']
        if 'name_en' in data: p.name_en = data['name_en']
        if 'category' in data: p.category = data['category']
        if 'material' in data: p.material = data['material']
        if 'price_jod' in data: p.price_jod = data['price_jod']
        if 'is_on_sale' in data: p.is_on_sale = data['is_on_sale']
        if 'sale_price_jod' in data: p.sale_price_jod = data['sale_price_jod']
        if 'length' in data: p.length = data['length']
        if 'size' in data: p.size = data['size']
        if 'stone' in data: p.stone = data['stone']
        if 'weight' in data: p.weight = data['weight']
        if 'stock_qty' in data: p.stock_qty = data['stock_qty']
        if 'is_new' in data: p.is_new = data['is_new']
        if 'is_visible' in data: p.is_visible = data['is_visible']
        if 'description_ar' in data: p.description_ar = data['description_ar']
        if 'description_en' in data: p.description_en = data['description_en']
        if 'care_ar' in data: p.care_ar = data['care_ar']
        if 'care_en' in data: p.care_en = data['care_en']
        
        if 'images' in data:
            # Rebuild images
            ProductImage.query.filter_by(product_id=p.id).delete()
            images_data = data['images']
            has_primary = any(img.get('is_primary') for img in images_data)
            for idx, img in enumerate(images_data):
                is_primary = img.get('is_primary', False)
                if not has_primary and idx == 0:
                    is_primary = True
                pi = ProductImage(
                    image_path=img['path'],
                    is_primary=is_primary,
                    sort_order=idx,
                    product_id=p.id
                )
                db.session.add(pi)
                
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/api/products/upload-image', methods=['POST'])
def api_upload_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image provided'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Create a unique filename
        import uuid
        ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'products')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        return jsonify({'success': True, 'path': f'static/images/products/{unique_filename}'})
    return jsonify({'success': False, 'message': 'Invalid file type'}), 400

@admin_bp.route('/api/products/bulk-toggle-visible', methods=['PUT'])
def api_bulk_toggle_visible():
    ids = request.get_json().get('ids', [])
    products = Product.query.filter(Product.id.in_(ids)).all()
    for p in products:
        p.is_visible = not p.is_visible
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/api/products/bulk-delete', methods=['DELETE'])
def api_bulk_delete():
    ids = request.get_json().get('ids', [])
    Product.query.filter(Product.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/orders')
def orders():
    return render_template('admin/orders.html')

@admin_bp.route('/orders/<int:id>')
def order_detail(id):
    order = Order.query.get_or_404(id)
    return render_template('admin/order_detail.html', order=order)

@admin_bp.route('/api/orders/<int:id>/status', methods=['PUT', 'PATCH'])
def api_order_status(id):
    order = Order.query.get_or_404(id)
    data = request.get_json()
    if 'status' in data:
        new_status = data['status']
        # Allow admin to change the status to any state without any validation restrictions
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Status not provided'}), 400

@admin_bp.route('/api/orders/<int:id>', methods=['PUT'])
def api_update_order(id):
    order = Order.query.get_or_404(id)
    data = request.get_json()
    
    if 'admin_notes' in data: order.admin_notes = data['admin_notes']
    if 'full_name' in data: order.full_name = data['full_name']
    if 'phone' in data: order.phone = data['phone']
    if 'city' in data: order.city = data['city']
    if 'area' in data: order.area = data['area']
    if 'address' in data: order.address = data['address']
    if 'notes' in data: order.notes = data['notes']
    
    order.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/customers')
def customers():
    return render_template('admin/customers.html')

@admin_bp.route('/customers/<int:id>')
def customer_detail(id):
    customer = User.query.get_or_404(id)
    return render_template('admin/customer_detail.html', customer=customer)

@admin_bp.route('/api/customers/<int:id>', methods=['DELETE'])
def api_delete_customer(id):
    customer = User.query.get_or_404(id)
    
    # Do not allow deleting an admin/super_admin through this endpoint
    if customer.role in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': 'Cannot delete admin accounts'}), 400
        
    try:
        from app.models import Wishlist, WishlistShare, RecentlyViewed, ChatbotLog, SupportTicket, ReturnRequest, Review, Order
        
        # Delete related wishlist entries
        Wishlist.query.filter_by(user_id=id).delete()
        
        # Delete related wishlist shares
        WishlistShare.query.filter_by(user_id=id).delete()
        
        # Delete related recently viewed entries
        RecentlyViewed.query.filter_by(user_id=id).delete()
        
        # Nullify user reference in chatbot logs, support tickets, and return requests
        ChatbotLog.query.filter_by(user_id=id).update({ChatbotLog.user_id: None})
        SupportTicket.query.filter_by(user_id=id).update({SupportTicket.user_id: None})
        ReturnRequest.query.filter_by(user_id=id).update({ReturnRequest.user_id: None})
        
        # Delete reviews
        Review.query.filter_by(user_id=id).delete()
        
        # Delete orders and their items
        orders = Order.query.filter_by(user_id=id).all()
        for o in orders:
            db.session.delete(o)
            
        # Delete the customer user account itself
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Customer deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/customers/<int:id>/orders')
def api_customer_orders(id):
    orders = Order.query.filter_by(user_id=id).order_by(Order.id.desc()).all()
    return jsonify({
        'orders': [{
            'id': o.id,
            'display_id': o.display_id,
            'created_at': o.created_at.isoformat(),
            'items_count': sum(item.quantity for item in o.items),
            'total_jod': float(o.total_jod or 0),
            'status': o.status
        } for o in orders]
    })

@admin_bp.route('/api/customers/<int:id>/wishlist')
def api_customer_wishlist(id):
    wishlist = Wishlist.query.filter_by(user_id=id).all()
    products = [Product.query.get(w.product_id) for w in wishlist]
    return jsonify({
        'products': [{
            'id': p.id,
            'name_ar': p.name_ar,
            'name_en': p.name_en,
            'primary_image': p.primary_image
        } for p in products if p]
    })

@admin_bp.route('/api/customers/<int:id>/reviews')
def api_customer_reviews(id):
    reviews = Review.query.filter_by(user_id=id).all()
    return jsonify({
        'reviews': [{
            'id': r.id,
            'product_name': Product.query.get(r.product_id).name_ar,
            'stars': r.stars,
            'comment': r.comment,
            'created_at': r.created_at.isoformat(),
            'is_approved': r.is_approved
        } for r in reviews]
    })

@admin_bp.route('/api/reviews')
def api_get_reviews():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    filter_status = request.args.get('filter', 'all')
    
    query = Review.query
    if filter_status == 'pending':
        query = query.filter_by(is_approved=False)
    elif filter_status == 'approved':
        query = query.filter_by(is_approved=True)
        
    pagination = query.order_by(Review.id.desc()).paginate(page=page, per_page=per_page)
    
    # Summary stats
    total = Review.query.count()
    pending = Review.query.filter_by(is_approved=False).count()
    avg = db.session.query(db.func.avg(Review.stars)).scalar() or 0
    
    return jsonify({
        'reviews': [{
            'id': r.id,
            'product_name': Product.query.get(r.product_id).name_ar if Product.query.get(r.product_id) else "—",
            'customer_name': User.query.get(r.user_id).full_name if User.query.get(r.user_id) else "—",
            'stars': r.stars,
            'comment': r.comment,
            'created_at': r.created_at.isoformat(),
            'is_approved': r.is_approved
        } for r in pagination.items],
        'pages': pagination.pages,
        'summary': {
            'total': total,
            'pending': pending,
            'avg': float(avg or 0)
        }
    })

@admin_bp.route('/api/customers')
def api_get_customers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    query = User.query.filter_by(role='user')
    if search:
        term = f'%{search}%'
        query = query.filter(User.full_name.ilike(term) | User.email.ilike(term) | User.username.ilike(term) | User.phone.ilike(term))
        
    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'customers': [{
            'id': c.id,
            'username': c.username,
            'full_name': c.full_name,
            'email': c.email,
            'phone': c.phone,
            'created_at': c.created_at.isoformat(),
            'orders_count': Order.query.filter_by(user_id=c.id).count(),
            'total_spent': float(db.session.query(db.func.sum(Order.total_jod)).filter_by(user_id=c.id).scalar() or 0)
        } for c in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages
    })

@admin_bp.route('/api/orders')
def api_get_orders():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', 'all')
    search = request.args.get('search', '')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Order.query
    
    if status != 'all':
        query = query.filter_by(status=status)
        
    if search:
        term = f'%{search}%'
        query = query.filter(Order.full_name.ilike(term) | Order.phone.ilike(term) | db.cast(Order.id, db.String).ilike(term))
        
    if date_from:
        query = query.filter(Order.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Order.created_at <= datetime.fromisoformat(date_to) + timedelta(days=1))
        
    pagination = query.order_by(Order.id.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'orders': [{
            'id': o.id,
            'display_id': o.display_id,
            'full_name': o.full_name,
            'phone': o.phone,
            'created_at': o.created_at.isoformat(),
            'items_count': sum(item.quantity for item in o.items),
            'total_jod': float(o.total_jod or 0),
            'status': o.status
        } for o in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages
    })
@admin_bp.route('/admins')
def admins():
    return render_template('admin/admins.html')

@admin_bp.route('/api/admins', methods=['GET'])
def api_get_admins():
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'message': 'Super Admin required'}), 403
    admins = User.query.filter(User.role.in_(['admin', 'super_admin'])).all()
    return jsonify({
        'admins': [{
            'id': a.id,
            'username': a.username,
            'full_name': a.full_name,
            'email': a.email,
            'role': a.role,
            'created_at': a.created_at.isoformat()
        } for a in admins]
    })

@admin_bp.route('/api/admins', methods=['POST'])
@fresh_login_required
def api_add_admin():
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'message': 'Super Admin required'}), 403
    data = request.get_json()
    if not data: return jsonify({'success': False, 'message': 'No data'}), 400
    from app import bcrypt
    # Check username and email uniqueness
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({'success': False, 'message': 'Username already exists'}), 409
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'success': False, 'message': 'Email already exists'}), 409

    try:
        hashed = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
        new_admin = User(
            username=data.get('username'),
            email=data.get('email'),
            phone=data.get('phone', '0000000000'),
            full_name=data.get('full_name', 'Admin'),
            password_hash=hashed,
            role=data.get('role', 'admin')
        )
        db.session.add(new_admin)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    return jsonify({'success': True, 'message': 'Admin added successfully'})

@admin_bp.route('/api/admins/<int:admin_id>', methods=['DELETE'])
@fresh_login_required
def api_delete_admin(admin_id):
    if admin_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400
    admin = User.query.get_or_404(admin_id)
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'message': 'Super Admin required'}), 403
    db.session.delete(admin)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Admin deleted successfully'})

@admin_bp.route('/settings')
@login_required
def settings():
    if current_user.role not in ['admin', 'super_admin']:
        return redirect(url_for('auth.login'))
        
    settings_list = SiteSetting.query.all()
    settings_dict = {}
    for s in settings_list:
        settings_dict[s.key] = s.value_ar
        settings_dict[f"{s.key}_ar"] = s.value_ar
        settings_dict[f"{s.key}_en"] = s.value_en
        
    class SettingsObj:
        def __init__(self, d):
            self.__dict__.update(d)
        def __getattr__(self, key):
            return self.__dict__.get(key, '')
            
    return render_template('admin/settings.html', settings=SettingsObj(settings_dict))

@admin_bp.route('/api/settings', methods=['PUT'])
@login_required
def api_update_settings():
    if current_user.role not in ['admin', 'super_admin']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
        
    for key, val in data.items():
        is_lang = False
        base_key = key
        lang_suffix = None
        
        if key.endswith('_ar'):
            base_key = key[:-3]
            lang_suffix = 'ar'
            is_lang = True
        elif key.endswith('_en'):
            base_key = key[:-3]
            lang_suffix = 'en'
            is_lang = True
            
        setting = SiteSetting.query.filter_by(key=base_key).first()
        if not setting:
            setting = SiteSetting(key=base_key)
            db.session.add(setting)
            
        if is_lang:
            if lang_suffix == 'ar':
                setting.value_ar = val
            else:
                setting.value_en = val
        else:
            setting.value_ar = val
            setting.value_en = val
            
    db.session.commit()
    return jsonify({'success': True, 'message': 'Settings updated successfully'})

@admin_bp.route('/coupons')
def coupons():
    return render_template('admin/coupons.html')

@admin_bp.route('/api/coupons', methods=['GET'])
def api_get_coupons():
    coupons = Coupon.query.all()
    return jsonify({
        'coupons': [{
            'id': c.id,
            'code': c.code,
            'type': c.type,
            'value': float(c.value),
            'min_order_jod': float(c.min_order_jod or 0),
            'usage_limit': c.usage_limit,
            'used_count': c.used_count,
            'expires_at': c.expires_at.isoformat() if c.expires_at else None,
            'is_active': c.is_active
        } for c in coupons]
    })

@admin_bp.route('/api/coupons', methods=['POST'])
def api_add_coupon():
    data = request.get_json()
    if not data: return jsonify({'success': False, 'message': 'No data'}), 400
    
    # Check uniqueness
    if Coupon.query.filter_by(code=data.get('code')).first():
        return jsonify({'success': False, 'message': 'Coupon code already exists'}), 409

    try:
        new_coupon = Coupon(
            code=data.get('code', '').upper(),
            type=data.get('type'),
            value=data.get('value'),
            min_order_jod=data.get('min_order_jod', 0),
            usage_limit=data.get('usage_limit'),
            expires_at=datetime.fromisoformat(data.get('expires_at')) if data.get('expires_at') else None,
            is_active=data.get('is_active', True)
        )
        db.session.add(new_coupon)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    return jsonify({'success': True})

@admin_bp.route('/api/coupons/<int:id>', methods=['PUT', 'DELETE'])
def api_edit_coupon(id):
    coupon = Coupon.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(coupon)
        db.session.commit()
        return jsonify({'success': True})
    
    data = request.get_json()
    try:
        if 'is_active' in data: coupon.is_active = data['is_active']
        if 'code' in data: 
            # Check uniqueness if code changed
            new_code = data['code'].upper()
            if new_code != coupon.code:
                if Coupon.query.filter_by(code=new_code).first():
                    return jsonify({'success': False, 'message': 'Coupon code already exists'}), 409
            coupon.code = new_code
        if 'type' in data: coupon.type = data['type']
        if 'value' in data: coupon.value = data['value']
        if 'min_order_jod' in data: coupon.min_order_jod = data['min_order_jod']
        if 'usage_limit' in data: coupon.usage_limit = data['usage_limit']
        if 'expires_at' in data: 
            coupon.expires_at = datetime.fromisoformat(data['expires_at']) if data['expires_at'] else None
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    return jsonify({'success': True})

@admin_bp.route('/reviews')
def reviews():
    return render_template('admin/reviews.html')

@admin_bp.route('/api/reviews/<int:id>/approve', methods=['POST'])
def api_approve_review(id):
    review = Review.query.get_or_404(id)
    review.is_approved = True
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/api/reviews/<int:id>', methods=['DELETE'])
def api_delete_review(id):
    review = Review.query.get_or_404(id)
    db.session.delete(review)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/discounts')
def discounts():
    return render_template('admin/discounts.html')

@admin_bp.route('/api/discounts/bulk', methods=['POST', 'DELETE'])
def api_bulk_discounts():
    data = request.get_json()
    category = data.get('category')
    if not category: return jsonify({'success': False, 'message': 'Category required'}), 400
    
    products = Product.query.filter_by(category=category).all()
    
    if request.method == 'DELETE':
        for p in products:
            p.is_on_sale = False
            p.sale_price_jod = None
        db.session.commit()
        return jsonify({'success': True, 'message': f'Removed all discounts from {category}'})
        
    pct = data.get('discount_pct')
    if not pct: return jsonify({'success': False, 'message': 'Discount percentage required'}), 400
    
    for p in products:
        p.is_on_sale = True
        p.sale_price_jod = round(float(p.price_jod) * (1 - pct/100), 3)
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'Applied {pct}% discount to {category}'})

@admin_bp.route('/announcements')
def announcements():
    announcements = Announcement.query.all()
    return render_template('admin/announcements.html', announcements=announcements)

@admin_bp.route('/api/announcements', methods=['GET', 'POST'])
def api_announcements():
    if request.method == 'POST':
        data = request.get_json()
        new_ann = Announcement(
            text_ar=data.get('text_ar'),
            text_en=data.get('text_en'),
            is_active=data.get('is_active', True)
        )
        db.session.add(new_ann)
        db.session.commit()
        return jsonify({'success': True})
    
    anns = Announcement.query.all()
    return jsonify({
        'announcements': [{
            'id': a.id,
            'text_ar': a.text_ar,
            'text_en': a.text_en,
            'is_active': a.is_active
        } for a in anns]
    })

@admin_bp.route('/api/announcements/<int:id>', methods=['PUT', 'DELETE'])
def api_edit_announcement(id):
    ann = Announcement.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(ann)
        db.session.commit()
        return jsonify({'success': True})
    
    data = request.get_json()
    if 'is_active' in data: ann.is_active = data['is_active']
    if 'text_ar' in data: ann.text_ar = data['text_ar']
    if 'text_en' in data: ann.text_en = data['text_en']
    if 'bg_color' in data: ann.bg_color = data['bg_color']
    if 'link' in data: ann.link = data['link']
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/chatbot')
def chatbot():
    return render_template('admin/chatbot_logs.html')

@admin_bp.route('/api/chatbot/logs', methods=['GET'])
def api_chatbot_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    lang = request.args.get('lang')
    
    # Subquery to find the latest log per session_id
    sub = db.session.query(
        ChatbotLog.session_id,
        db.func.max(ChatbotLog.created_at).label('max_created_at')
    ).group_by(ChatbotLog.session_id).subquery()
    
    query = ChatbotLog.query.join(
        sub, (ChatbotLog.session_id == sub.c.session_id) & (ChatbotLog.created_at == sub.c.max_created_at)
    )
    
    if lang: query = query.filter(ChatbotLog.lang == lang)
    
    logs = query.order_by(ChatbotLog.created_at.desc()).paginate(page=page, per_page=per_page)
    
    today = datetime.utcnow().date()
    count_today = db.session.query(db.func.count(db.distinct(ChatbotLog.session_id))).filter(db.func.date(ChatbotLog.created_at) == today).scalar()
    total_chats = db.session.query(db.func.count(db.distinct(ChatbotLog.session_id))).scalar() or 1
    
    return jsonify({
        'sessions': [{
            'id': l.id,
            'session_id': l.session_id,
            'created_at': l.created_at.isoformat(),
            'username': User.query.get(l.user_id).username if l.user_id else None,
            'lang': l.lang,
            'last_message': l.user_message[:60] + '...'
        } for l in logs.items],
        'stats': {
            'count_today': count_today,
            'total_chats': total_chats
        },
        'pages': logs.pages
    })

@admin_bp.route('/api/chatbot/logs/session/<session_id>', methods=['GET'])
def api_chatbot_session_detail(session_id):
    messages = ChatbotLog.query.filter_by(session_id=session_id).order_by(ChatbotLog.created_at.asc()).all()
    
    result = []
    for m in messages:
        result.append({'sender': 'user', 'text': m.user_message, 'created_at': m.created_at.isoformat()})
        result.append({'sender': 'bot', 'text': m.bot_reply, 'created_at': m.created_at.isoformat()})
        
    return jsonify({'messages': result})
