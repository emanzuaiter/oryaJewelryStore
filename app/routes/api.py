from flask import Blueprint, request, jsonify, session
import secrets
from flask_login import login_required, current_user
from app import db
from app.models import (Product, ProductImage, Order, OrderItem,
                         Wishlist, WishlistShare, Review, Coupon,
                         Announcement, SiteSetting, ChatbotLog,
                         RecentlyViewed, User)
from sqlalchemy import func, desc
from datetime import datetime
from app.utils.email import (send_order_confirmation, send_admin_new_order, 
                             send_order_cancellation, send_admin_cancellation)

api_bp = Blueprint('api', __name__, url_prefix='/api')

# ── Helpers ──────────────────────────────────────────────────
def get_lang():
    return session.get('lang', 'ar')

def product_to_dict(p, lang='ar'):
    wishlisted = False
    if current_user.is_authenticated:
        wishlisted = any(w.product_id == p.id for w in current_user.wishlist)
        
    return {
        'id': p.id,
        'name': p.name_ar if lang == 'ar' else p.name_en,
        'name_ar': p.name_ar,
        'name_en': p.name_en,
        'price': float(p.price_jod),
        'sale_price': float(p.sale_price_jod) if p.sale_price_jod else None,
        'is_on_sale': p.is_on_sale,
        'category': p.category,
        'material': p.material,
        'stock_qty': p.stock_qty,
        'primary_image': p.primary_image,
        'secondary_image': p.images[1].image_path if len(p.images) > 1 else None,
        'is_new': p.is_new,
        'in_wishlist': wishlisted,
        'avg_rating': p.avg_rating,
        'description': p.description_ar if lang == 'ar' else p.description_en
    }

# ── Products Endpoints ────────────────────────────────────────
@api_bp.route('/products')
def get_products():
    lang = get_lang()
    
    # Query parameters
    category  = request.args.get('category', 'all')
    min_price = request.args.get('min_price', 0, type=float)
    max_price = request.args.get('max_price', 5000, type=float)
    sort      = request.args.get('sort', 'newest')
    material  = request.args.get('material', '')
    sale_only = request.args.get('sale', 'false').lower() == 'true'
    
    q = Product.query.filter(
        Product.is_visible == True,
        Product.price_jod >= min_price,
        Product.price_jod <= max_price
    )
    
    # Category Filter
    if category and category != 'all':
        q = q.filter(Product.category == category)
        
    # Material Filter
    if material:
        materials = [m.strip() for m in material.split(',') if m.strip()]
        if materials:
            q = q.filter(Product.material.in_(materials))
            
    # Sale Filter
    if sale_only:
        q = q.filter(Product.is_on_sale == True)
        
    # Sorting logic
    if sort == 'price_low':
        q = q.order_by(Product.price_jod.asc())
    elif sort == 'price_high':
        q = q.order_by(Product.price_jod.desc())
    elif sort == 'best_selling':
        q = q.order_by(Product.sales_count.desc())
    elif sort == 'rating':
        q = q.order_by(Product.id.desc())
    else: # newest
        q = q.order_by(Product.id.desc())
        
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    paginated = q.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'products': [product_to_dict(p, lang) for p in paginated.items],
            'total': paginated.total,
            'page': paginated.page,
            'pages': paginated.pages
        }
    })

@api_bp.route('/products/<int:product_id>')
def get_product(product_id):
    p = Product.query.get_or_404(product_id)
    return jsonify({'success': True, 'data': product_to_dict(p, get_lang())})

@api_bp.route('/products/search')
def search_products():
    q = request.args.get('q', '').strip()
    
    lang = get_lang()
    
    from app.utils.search import get_search_query
    query = get_search_query(q)
    
    # Apply filters
    min_price = request.args.get('min_price', 0, type=float)
    max_price = request.args.get('max_price', 5000, type=float)
    sort      = request.args.get('sort', 'newest')
    material  = request.args.get('material', '')
    sale_only = request.args.get('sale', 'false').lower() == 'true'
    
    query = query.filter(Product.price_jod >= min_price, Product.price_jod <= max_price)

    if material:
        materials = [m.strip() for m in material.split(',') if m.strip()]
        if materials:
            query = query.filter(Product.material.in_(materials))
            
    if sale_only:
        query = query.filter(Product.is_on_sale == True)
        
    if sort == 'price_low':
        query = query.order_by(Product.price_jod.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price_jod.desc())
    elif sort == 'best_selling':
        query = query.order_by(Product.sales_count.desc())
    else:
        query = query.order_by(Product.id.desc())
        
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    paginated = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True, 
        'data': {
            'products': [product_to_dict(p, lang) for p in paginated.items],
            'total': paginated.total,
            'page': paginated.page,
            'pages': paginated.pages
        }
    })

# ── Coupons & Orders ──────────────────────────────────────────

@api_bp.route('/coupons/validate', methods=['POST'])
def validate_coupon():
    data = request.get_json() or {}
    
    # 1. Handle user input errors (strip and upper)
    raw_code = data.get('code', '')
    code = str(raw_code).strip().upper()
    
    try:
        subtotal = float(data.get('subtotal', 0))
    except (ValueError, TypeError):
        subtotal = 0.0
        
    print(f"--- START COUPON VALIDATION ---")
    print(f"Code received: '{raw_code}' -> Cleaned: '{code}'")
    print(f"Subtotal: {subtotal}")

    # 2. Query the database
    coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    
    if not coupon:
        print(f"Failure Reason: Coupon '{code}' NOT FOUND or NOT ACTIVE in database")
        print(f"--- END COUPON VALIDATION ---")
        return jsonify({'success': True, 'data': {'valid': False}, 'message': 'كوبون غير موجود'})
        
    # 3. Perform robust validation
    is_valid, message, debug_info = coupon.is_valid(subtotal)
    
    # Print debug info
    print(f"Debug Info: {debug_info}")
    print(f"Validation Result: {is_valid} | Message: {message}")
    print(f"--- END COUPON VALIDATION ---")
    
    if not is_valid:
        return jsonify({
            'success': True, 
            'data': {'valid': False}, 
            'message': message,
            'debug': debug_info  # Expose to frontend/network tab for testing
        })
    
    # 4. Success: Calculate discount
    discount = float(coupon.calculate_discount(subtotal))
    return jsonify({
        'success': True,
        'data': {
            'valid': True,
            'discount': discount,
            'code': coupon.code,
            'debug': debug_info
        }
    })

@api_bp.route('/orders/create', methods=['POST'])
@login_required
def create_order():
    data = request.get_json()
    lang = get_lang()
    
    items_data = data.get('items', [])
    if not items_data:
        return jsonify({'success': False, 'message': 'السلة فارغة'}), 400
        
    try:
        subtotal = 0
        order_items = []
        
        # 1. Validate items and calculate subtotal
        for item in items_data:
            p = Product.query.get(item['product_id'])
            if not p or not p.is_visible:
                return jsonify({'success': False, 'message': f"منتج غير موجود: {item.get('product_id')}"}), 404
            
            qty = int(item['quantity'])
            if p.stock_qty < qty:
                return jsonify({'success': False, 'message': f"كمية غير كافية لـ {p.name_ar if lang=='ar' else p.name_en}"}), 400
                
            unit_price = float(p.effective_price)
            subtotal += unit_price * qty
            
            order_items.append(OrderItem(
                product_id=p.id,
                quantity=qty,
                unit_price_jod=unit_price
            ))
            
            # Decrement stock
            p.stock_qty -= qty
            
        # 2. Handle Coupon
        discount = 0
        coupon_code = data.get('coupon_code', '').upper()
        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
            if coupon:
                is_valid, msg, debug_info = coupon.is_valid(subtotal)
                if is_valid:
                    discount = float(coupon.calculate_discount(subtotal))
                    coupon.used_count += 1
                # If invalid, we just proceed without discount (or we could fail, but usually UI handles this)

        # 3. Delivery Fee (calculated dynamically from settings)
        from app.utils.delivery import get_delivery_fee
        delivery_fee = get_delivery_fee(subtotal, items_data)
        
        total = subtotal - discount + delivery_fee
        
        # 4. Create Order
        new_order = Order(
            user_id=current_user.id,
            status='pending',
            subtotal_jod=subtotal,
            discount_jod=discount,
            delivery_fee_jod=delivery_fee,
            total_jod=total,
            coupon_code=coupon_code if discount > 0 else None,
            full_name=data.get('full_name'),
            phone=data.get('phone'),
            city=data.get('city'),
            area=data.get('area', ''),
            address=data.get('address'),
            national_id=data.get('national_id'),
            notes=data.get('notes'),
            payment_method=data.get('payment_method', 'cash_on_delivery')
        )
        
        # Add items
        for oi in order_items:
            new_order.items.append(oi)
            
        db.session.add(new_order)
        db.session.commit()
        
        # 5. Emails
        try:
            send_order_confirmation(new_order, lang)
            send_admin_new_order(new_order)
        except Exception as e:
            # Don't fail the order if email fails
            pass
            
        return jsonify({
            'success': True, 
            'message': 'تم استلام طلبك بنجاح' if lang == 'ar' else 'Order placed successfully',
            'data': {'order_id': new_order.id}
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/orders/my-orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(desc(Order.created_at)).all()
    return jsonify({
        'success': True,
        'data': {'orders': [o.to_dict() for o in orders]}
    })

@api_bp.route('/orders/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    
    if order.status != 'pending':
        lang = get_lang()
        msg = "لا يمكن إلغاء الطلب بعد بدء التجهيز" if lang == 'ar' else "Order cannot be cancelled after processing"
        return jsonify({'success': False, 'message': msg}), 400
        
    order.status = 'cancelled'
    db.session.commit()
    
    lang = get_lang()
    msg = "تم إلغاء الطلب بنجاح" if lang == 'ar' else "Order cancelled successfully"
    return jsonify({'success': True, 'message': msg})

# ── Wishlist, Reviews & Misc ──────────────────────────────────

@api_bp.route('/wishlist/toggle', methods=['POST'])
@login_required
def wishlist_toggle():
    product_id = request.get_json().get('product_id')
    item = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({'success': True, 'data': {'wishlisted': False}})
    else:
        db.session.add(Wishlist(user_id=current_user.id, product_id=product_id))
        db.session.commit()
        return jsonify({'success': True, 'data': {'wishlisted': True}})

@api_bp.route('/wishlist/<int:product_id>', methods=['DELETE'])
@login_required
def wishlist_remove(product_id):
    item = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/wishlist/share-token')
@login_required
def get_wishlist_share_token():
    share = WishlistShare.query.filter_by(user_id=current_user.id).first()
    if not share:
        token = secrets.token_urlsafe(32)
        share = WishlistShare(user_id=current_user.id, share_token=token)
        db.session.add(share)
        db.session.commit()
    return jsonify({'success': True, 'token': share.share_token})
@login_required
def add_review():
    data = request.get_json()
    product_id = data.get('product_id')
    
    # Check if user bought product first
    has_purchased = OrderItem.query.join(Order).filter(
        Order.user_id == current_user.id,
        OrderItem.product_id == product_id
    ).first()
    
    if not has_purchased:
        return jsonify({'success': False, 'message': 'لا يمكنك تقييم منتج لم تقم بشرائه'}), 403
        
    new_review = Review(
        user_id=current_user.id, 
        product_id=product_id, 
        stars=data['stars'], 
        comment=data['comment']
    )
    db.session.add(new_review)
    db.session.commit()
    return jsonify({'success': True, 'message': 'شكراً لتقييمك! سيظهر بعد المراجعة'})

@api_bp.route('/site-settings')
def get_site_settings():
    settings = SiteSetting.get_all()
    lang = get_lang()
    # Map raw settings to current language
    return jsonify({'success': True, 'data': {k: v.get(lang) for k, v in settings.items()}})

@api_bp.route('/contact', methods=['POST'])
def contact():
    from app.utils.email import send_admin_contact_message
    data = request.get_json()
    try:
        send_admin_contact_message(data['name'], data.get('phone', ''), data['message'])
    except:
        pass
    return jsonify({'success': True, 'message': 'تم الإرسال بنجاح'})

@api_bp.route('/recently-viewed', methods=['POST'])
def add_recently_viewed():
    data = request.get_json()
    product_id = data.get('product_id')
    if not product_id:
        return jsonify({'success': False}), 400
        
    session_id = session.get('session_id')
    if not session_id:
        session_id = secrets.token_hex(16)
        session['session_id'] = session_id
        
    user_id = current_user.id if current_user.is_authenticated else None
    
    # Check if already exists
    existing = RecentlyViewed.query.filter_by(
        session_id=session_id, 
        product_id=product_id
    ).first()
    
    if existing:
        existing.viewed_at = datetime.utcnow()
    else:
        new_rv = RecentlyViewed(
            user_id=user_id,
            session_id=session_id,
            product_id=product_id
        )
        db.session.add(new_rv)
        
    db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/recently-viewed', methods=['GET'])
def get_recently_viewed():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'success': True, 'products': []})
        
    rvs = RecentlyViewed.query.filter_by(session_id=session_id).order_by(RecentlyViewed.viewed_at.desc()).limit(10).all()
    lang = get_lang()
    products = [product_to_dict(rv.product, lang) for rv in rvs]
    
    return jsonify({'success': True, 'products': products})
