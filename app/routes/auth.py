from flask import Blueprint, request, jsonify, session, redirect, url_for
from flask_login import login_user, logout_user, \
                        login_required, current_user
from app import db, bcrypt
from app.models import User
import re

auth_bp = Blueprint('auth', __name__)

# ── Helpers ──────────────────────────────────────────────────

def validate_jordanian_phone(phone):
    return bool(re.match(r'^07[789]\d{7}$', phone))

def user_to_dict(user):
    return {
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'email': user.email,
        'phone': user.phone,
        'role': user.role
    }

# ── Register ─────────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        from flask import render_template
        return render_template('user/register.html')
    lang = session.get('lang', 'ar')
    data = request.get_json()
    if not data:
        msg = 'Invalid data' if lang == 'en' else 'بيانات غير صالحة'
        return jsonify({'success': False, 'message': msg}), 400

    full_name = data.get('full_name', '').strip()
    username  = data.get('username', '').strip().lower()
    email     = data.get('email', '').strip().lower()
    phone     = data.get('phone', '').strip()
    password  = data.get('password', '')

    # Validation
    errors = []
    if lang == 'en':
        if not full_name or len(full_name) < 2:
            errors.append('Full name is required (at least 2 characters)')
        if not username or len(username) < 3:
            errors.append('Username is required (at least 3 characters)')
        if not email or '@' not in email:
            errors.append('Invalid email address')
        if not validate_jordanian_phone(phone):
            errors.append('Invalid phone number (must start with 07X)')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters long')
    else:
        if not full_name or len(full_name) < 2:
            errors.append('الاسم الكامل مطلوب (حرفان على الأقل)')
        if not username or len(username) < 3:
            errors.append('اسم المستخدم مطلوب (3 أحرف على الأقل)')
        if not email or '@' not in email:
            errors.append('بريد إلكتروني غير صالح')
        if not validate_jordanian_phone(phone):
            errors.append('رقم هاتف غير صالح (يجب أن يبدأ بـ 07X)')
        if not password or len(password) < 8:
            errors.append('كلمة المرور يجب أن تكون 8 أحرف على الأقل')

    if errors:
        separator = ' • ' if lang == 'en' else ' · '
        return jsonify({'success': False,
                        'message': separator.join(errors)}), 422

    # Uniqueness checks
    if User.query.filter_by(username=username).first():
        msg = 'Username is already taken' if lang == 'en' else 'اسم المستخدم مستخدم بالفعل'
        return jsonify({'success': False, 'message': msg}), 409
    if User.query.filter_by(email=email).first():
        msg = 'Email is already registered' if lang == 'en' else 'البريد الإلكتروني مسجل بالفعل'
        return jsonify({'success': False, 'message': msg}), 409

    # Generate OTP
    import random
    import time
    from flask_mail import Message
    from app import mail

    otp_code = str(random.randint(100000, 999999))
    
    # Store pending user data and OTP in session
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    session['pending_user'] = {
        'full_name': full_name,
        'username': username,
        'email': email,
        'phone': phone,
        'password_hash': hashed,
        'role': 'user'
    }
    session['registration_otp'] = otp_code
    session['otp_timestamp'] = time.time()

    # Send the OTP via email
    try:
        msg = Message("ORYA - Your Verification Code",
                      recipients=[email])
        msg.body = f"Hello {full_name},\n\nYour 6-digit verification code is: {otp_code}\n\nThis code will expire in 5 minutes.\n\nThank you,\nORYA Luxury"
        mail.send(msg)
    except Exception as e:
        err_msg = 'Failed to send verification email. Please try again.' if lang == 'en' else 'فشل إرسال بريد التحقق. يرجى المحاولة مرة أخرى.'
        return jsonify({'success': False, 'message': err_msg}), 500

    next_url = request.args.get('next') or '/'
    session['registration_next_url'] = next_url

    success_msg = 'Verification code has been sent to your email' if lang == 'en' else 'تم إرسال رمز التحقق إلى بريدك الإلكتروني'
    return jsonify({
        'success':  True,
        'message':  success_msg,
        'redirect': '/verify-otp'
    }), 200

# ── OTP Verification ──────────────────────────────────────────

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'pending_user' not in session:
        # If no registration is in progress, redirect to register
        return redirect(url_for('auth.register'))

    pending_user = session['pending_user']
    email = pending_user.get('email', '')

    if request.method == 'GET':
        from flask import render_template
        return render_template('user/verify_otp.html', email=email)

    lang = session.get('lang', 'ar')
    data = request.get_json()
    if not data:
        msg = 'Invalid data' if lang == 'en' else 'بيانات غير صالحة'
        return jsonify({'success': False, 'message': msg}), 400

    submitted_otp = data.get('otp', '').strip()
    if len(submitted_otp) != 6:
        msg = 'Verification code must be 6 digits' if lang == 'en' else 'يجب أن يتكون رمز التحقق من 6 أرقام'
        return jsonify({'success': False, 'message': msg}), 422

    session_otp = session.get('registration_otp')
    otp_timestamp = session.get('otp_timestamp', 0)

    import time
    # Check expiry (5 minutes = 300 seconds)
    if time.time() - otp_timestamp > 300:
        msg = 'Verification code has expired. Please request a new code.' if lang == 'en' else 'انتهت صلاحية رمز التحقق. يرجى طلب رمز جديد.'
        return jsonify({'success': False, 'message': msg}), 400

    if submitted_otp != session_otp:
        msg = 'Incorrect verification code. Please try again.' if lang == 'en' else 'رمز التحقق غير صحيح. يرجى المحاولة مرة أخرى.'
        return jsonify({'success': False, 'message': msg}), 400

    # Code is valid! Save the user to the database
    try:
        user = User(
            full_name=pending_user['full_name'],
            username=pending_user['username'],
            email=pending_user['email'],
            phone=pending_user['phone'],
            password_hash=pending_user['password_hash'],
            role=pending_user['role']
        )
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        err_msg = 'An error occurred while creating your account. Please try again later.' if lang == 'en' else 'حدث خطأ أثناء إنشاء الحساب. يرجى المحاولة لاحقاً.'
        return jsonify({'success': False, 'message': err_msg}), 500

    # Log the user in
    login_user(user, remember=True)

    # Clean up session
    next_url = session.get('registration_next_url') or '/'
    session.pop('pending_user', None)
    session.pop('registration_otp', None)
    session.pop('otp_timestamp', None)
    session.pop('registration_next_url', None)

    success_msg = 'Account successfully verified!' if lang == 'en' else 'تم التحقق من الحساب بنجاح!'
    return jsonify({
        'success': True,
        'message': success_msg,
        'redirect': next_url
    }), 200

@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    lang = session.get('lang', 'ar')
    if 'pending_user' not in session:
        msg = 'No active registration process found' if lang == 'en' else 'لا توجد عملية تسجيل نشطة'
        return jsonify({'success': False, 'message': msg}), 400

    pending_user = session['pending_user']
    email = pending_user['email']
    full_name = pending_user['full_name']

    import random
    import time
    from flask_mail import Message
    from app import mail

    otp_code = str(random.randint(100000, 999999))
    session['registration_otp'] = otp_code
    session['otp_timestamp'] = time.time()

    try:
        msg = Message("ORYA - Your Verification Code", recipients=[email])
        msg.body = f"Hello {full_name},\n\nYour new 6-digit verification code is: {otp_code}\n\nThis code will expire in 5 minutes.\n\nThank you,\nORYA Luxury"
        mail.send(msg)
    except Exception as e:
        err_msg = 'Failed to send verification code. Please try again.' if lang == 'en' else 'فشل إرسال رمز التحقق. يرجى المحاولة مرة أخرى.'
        return jsonify({'success': False, 'message': err_msg}), 500

    success_msg = 'Verification code has been successfully resent to your email' if lang == 'en' else 'تم إعادة إرسال رمز التحقق إلى بريدك الإلكتروني بنجاح'
    return jsonify({
        'success': True,
        'message': success_msg
    }), 200

# ── Login ────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        from flask import render_template
        return render_template('user/login.html')
    data = request.get_json()
    if not data:
        return jsonify({'success': False,
                        'message': 'بيانات غير صالحة'}), 400

    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    remember = data.get('remember', False)

    if not username or not password:
        return jsonify({'success': False,
                        'message': 'يرجى إدخال اسم المستخدم'
                                   ' وكلمة المرور'}), 400

    user = User.query.filter_by(username=username).first()

    if not user or \
       not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({'success': False,
                        'message': 'اسم المستخدم أو كلمة المرور'
                                   ' غير صحيحة'}), 401

    if not user.is_active:
        return jsonify({'success': False,
                        'message': 'الحساب موقوف'}), 403

    login_user(user, remember=bool(remember))
    next_url = request.args.get('next') or '/'

    return jsonify({
        'success':  True,
        'message':  f'أهلاً {user.full_name}!',
        'redirect': next_url,
        'user':     user_to_dict(user)
    })

# ── Logout ───────────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect('/')

@auth_bp.route('/account')
@login_required
def account():
    from flask import render_template
    from app.models import Order
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    return render_template('user/account.html', orders=orders)

# ── Availability checks ──────────────────────────────────────

@auth_bp.route('/check-username/<username>')
def check_username(username):
    exists = User.query.filter_by(
        username=username.lower()).first() is not None
    return jsonify({'available': not exists})

@auth_bp.route('/check-email/<email>')
def check_email(email):
    exists = User.query.filter_by(
        email=email.lower()).first() is not None
    return jsonify({'available': not exists})

# ── Admin Login ──────────────────────────────────────────────

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        from flask import render_template
        return render_template('admin/login.html')

    if request.is_json:
        data = request.get_json()
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')
    else:
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

    # Allow both admin and super_admin
    user = User.query.filter(User.username == username, User.role.in_(['admin', 'super_admin'])).first()

    if not user or \
       not bcrypt.check_password_hash(user.password_hash, password):
        if request.is_json:
            return jsonify({'success': False,
                            'message': 'بيانات الدخول غير صحيحة'}), 401
        from flask import flash, redirect
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
        return redirect('/admin/login')

    login_user(user, remember=True, fresh=True)
    if request.is_json:
        return jsonify({'success':  True,
                        'redirect': '/admin/dashboard'})
    from flask import redirect
    return redirect('/admin/dashboard')

@auth_bp.route('/admin/logout')
def admin_logout():
    logout_user()
    from flask import redirect
    return redirect('/')

# ── Profile Update ───────────────────────────────────────────

@auth_bp.route('/api/account/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json()

    # Update basic fields
    if 'full_name' in data:
        current_user.full_name = data['full_name'].strip()
    if 'email' in data:
        email = data['email'].strip().lower()
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            return jsonify({'success': False,
                            'message': 'البريد مستخدم بالفعل'}), 409
        current_user.email = email
    if 'phone' in data:
        if not validate_jordanian_phone(data['phone']):
            return jsonify({'success': False,
                            'message': 'رقم هاتف غير صالح'}), 422
        current_user.phone = data['phone']

    # Password change
    if 'current_password' in data and 'new_password' in data:
        if not bcrypt.check_password_hash(
                current_user.password_hash, data['current_password']):
            return jsonify({'success': False,
                            'message': 'كلمة المرور الحالية غير صحيحة'
                            }), 401
        if len(data['new_password']) < 8:
            return jsonify({'success': False,
                            'message': 'كلمة المرور الجديدة قصيرة'
                            }), 422
        current_user.password_hash = bcrypt.generate_password_hash(
            data['new_password']).decode('utf-8')

    db.session.commit()
    return jsonify({'success': True, 'message': 'تم تحديث البيانات'})

# ── Language preference ───────────────────────────────────────

@auth_bp.route('/api/set-language', methods=['POST'])
def set_language():
    data = request.get_json()
    lang = data.get('lang', 'ar')
    if lang not in ('ar', 'en'):
        lang = 'ar'
    session['lang'] = lang
    return jsonify({'success': True, 'lang': lang})

# ── Test Email Route ──────────────────────────────────────────

@auth_bp.route('/test-email', methods=['GET'])
def test_email():
    from flask_mail import Message
    from app import mail
    import os

    try:
        msg = Message("Test Email from ORYA",
                      recipients=[os.environ.get('MAIL_USERNAME')])
        msg.body = "This is a test email sent from the ORYA Flask application to verify SMTP settings."
        mail.send(msg)
        return jsonify({
            'success': True, 
            'message': 'Test email sent successfully! Please check your inbox.'
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Failed to send email: {str(e)}'
        }), 500


# ── Order OTP Verification ─────────────────────────────────────

@auth_bp.route('/place-order', methods=['POST'])
@login_required
def place_order():
    from app.models import Product, Order, OrderItem, Coupon
    import random
    import time
    from flask_mail import Message
    from app import mail, db
    
    lang = session.get('lang', 'ar')
    data = request.get_json()
    if not data:
        msg = 'Invalid data' if lang == 'en' else 'بيانات غير صالحة'
        return jsonify({'success': False, 'message': msg}), 400
        
    items_data = data.get('items', [])
    if not items_data:
        msg = 'Cart is empty' if lang == 'en' else 'السلة فارغة'
        return jsonify({'success': False, 'message': msg}), 400
        
    try:
        subtotal = 0
        order_items = []
        
        # 1. Validate items and calculate subtotal
        for item in items_data:
            p = Product.query.get(item['product_id'])
            if not p or not p.is_visible:
                msg = f"Product not found: {item.get('product_id')}" if lang == 'en' else f"منتج غير موجود: {item.get('product_id')}"
                return jsonify({'success': False, 'message': msg}), 404
            
            qty = int(item['quantity'])
            if p.stock_qty < qty:
                msg = f"Insufficient stock for {p.name_en if lang=='en' else p.name_ar}" if lang == 'en' else f"كمية غير كافية لـ {p.name_ar if lang=='ar' else p.name_en}"
                return jsonify({'success': False, 'message': msg}), 400
                
            unit_price = float(p.effective_price)
            subtotal += unit_price * qty
            
            order_items.append(OrderItem(
                product_id=p.id,
                quantity=qty,
                unit_price_jod=unit_price
            ))
            
            # Decrement stock (reserved)
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

        # 3. Delivery Fee (calculated dynamically from settings)
        from app.utils.delivery import get_delivery_fee
        delivery_fee = get_delivery_fee(subtotal, items_data)
        total = subtotal - discount + delivery_fee
        
        # 4. Create Order with status 'pending_verification'
        new_order = Order(
            user_id=current_user.id,
            status='pending_verification',
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
        
        # Generate 6-digit Order OTP
        otp_code = str(random.randint(100000, 999999))
        print(f"[DEBUG ORDER OTP] Code is: {otp_code}")
        session['order_otp'] = {
            'otp': otp_code,
            'order_id': new_order.id,
            'timestamp': time.time()
        }
        
        # Send Email
        try:
            msg = Message("ORYA - Confirm Your Order", recipients=[current_user.email])
            msg.body = f"Hello {current_user.full_name},\n\nThank you for placing an order with ORYA Luxury!\n\nYour 6-digit order verification code is: {otp_code}\n\nPlease enter this code on the checkout page to confirm your order.\nThis code will expire in 5 minutes.\n\nThank you,\nORYA Luxury"
            mail.send(msg)
        except Exception as e:
            print(f"[Order OTP Email Error] {e}")
            
        return jsonify({
            'success': True,
            'message': 'Verification code sent' if lang == 'en' else 'تم إرسال رمز التحقق'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/verify-order-otp', methods=['POST'])
@login_required
def verify_order_otp():
    from app.models import Order
    from app import db
    from app.utils.email import send_order_confirmation, send_admin_new_order
    import time
    
    lang = session.get('lang', 'ar')
    data = request.get_json()
    if not data:
        msg = 'Invalid data' if lang == 'en' else 'بيانات غير صالحة'
        return jsonify({'success': False, 'message': msg}), 400
        
    submitted_otp = data.get('otp', '').strip()
    if len(submitted_otp) != 6:
        msg = 'Verification code must be 6 digits' if lang == 'en' else 'يجب أن يتكون رمز التحقق من 6 أرقام'
        return jsonify({'success': False, 'message': msg}), 422
        
    order_otp_data = session.get('order_otp')
    if not order_otp_data:
        msg = 'No pending order verification found. Please try placing your order again.' if lang == 'en' else 'لم يتم العثور على طلب معلق للتحقق. يرجى محاولة تقديم الطلب مرة أخرى.'
        return jsonify({'success': False, 'message': msg}), 400
        
    session_otp = order_otp_data.get('otp')
    order_id = order_otp_data.get('order_id')
    otp_timestamp = order_otp_data.get('timestamp', 0)
    
    # Check expiry (5 minutes = 300 seconds)
    if time.time() - otp_timestamp > 300:
        msg = 'Verification code has expired. Please place the order again.' if lang == 'en' else 'انتهت صلاحية رمز التحقق. يرجى تقديم الطلب مرة أخرى.'
        return jsonify({'success': False, 'message': msg}), 400
        
    if submitted_otp != session_otp:
        msg = 'Incorrect verification code. Please try again.' if lang == 'en' else 'رمز التحقق غير صحيح. يرجى المحاولة مرة أخرى.'
        return jsonify({'success': False, 'message': msg}), 400
        
    # Code is valid! 
    order = Order.query.get(order_id)
    if not order:
        msg = 'Order not found' if lang == 'en' else 'الطلب غير موجود'
        return jsonify({'success': False, 'message': msg}), 404
        
    try:
        order.status = 'confirmed'
        db.session.commit()
        
        # Clean up session
        session.pop('order_otp', None)
        
        # Send confirmation email
        try:
            send_order_confirmation(order, lang)
            send_admin_new_order(order)
        except Exception as e:
            print(f"[Order Confirmed Email Error] {e}")
            
        success_msg = 'Order successfully confirmed!' if lang == 'en' else 'تم تأكيد الطلب بنجاح!'
        return jsonify({
            'success': True,
            'message': success_msg,
            'redirect': f'/order-success/{order.id}'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        err_msg = 'An error occurred while confirming your order.' if lang == 'en' else 'حدث خطأ أثناء تأكيد طلبك.'
        return jsonify({'success': False, 'message': err_msg}), 500


@auth_bp.route('/resend-order-otp', methods=['POST'])
@login_required
def resend_order_otp():
    from app.models import Order
    import random
    import time
    from flask_mail import Message
    from app import mail
    
    lang = session.get('lang', 'ar')
    order_otp_data = session.get('order_otp')
    if not order_otp_data:
        msg = 'No pending order verification found.' if lang == 'en' else 'لم يتم العثور على طلب معلق للتحقق.'
        return jsonify({'success': False, 'message': msg}), 400
        
    order_id = order_otp_data.get('order_id')
    order = Order.query.get(order_id)
    if not order:
        msg = 'Order not found' if lang == 'en' else 'الطلب غير موجود'
        return jsonify({'success': False, 'message': msg}), 404
        
    otp_code = str(random.randint(100000, 999999))
    print(f"[DEBUG ORDER RESEND OTP] Code is: {otp_code}")
    session['order_otp'] = {
        'otp': otp_code,
        'order_id': order.id,
        'timestamp': time.time()
    }
    
    try:
        msg = Message("ORYA - Confirm Your Order (New Code)", recipients=[current_user.email])
        msg.body = f"Hello {current_user.full_name},\n\nYour new 6-digit order verification code is: {otp_code}\n\nPlease enter this code on the checkout page to confirm your order.\nThis code will expire in 5 minutes.\n\nThank you,\nORYA Luxury"
        mail.send(msg)
    except Exception as e:
        print(f"[Order Resend Email Error] {e}")
        
    success_msg = 'Verification code has been successfully resent' if lang == 'en' else 'تم إعادة إرسال رمز التحقق بنجاح'
    return jsonify({
        'success': True,
        'message': success_msg
    }), 200
