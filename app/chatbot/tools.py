"""
LangChain tools for dynamic data (DB queries).
Each tool function reads from the database directly.
"""

from app import db
from app.models import User, Product, Order, OrderItem, Coupon, Announcement, SiteSetting, Notification, SupportTicket, ReturnRequest
from datetime import datetime
from flask_login import current_user
import re
import json

# ── Tool: Search Products (Semantic & Personalized) ──────────
def search_products_tool(query: str) -> str:
    """
    Search ORYA jewelry products using semantic similarity.
    Acts as a 'Personal Shopper' by mapping styles/colors to products.
    """
    from app.chatbot.rag_pipeline import load_vector_store, PRODUCTS_COL, TOP_K, MAX_DISTANCE
    from app.utils.slugs import slugify
    from flask import session
    import json

    try:
        lang = session.get('lang', 'ar')
        vs = load_vector_store(PRODUCTS_COL)
        # Fetch results using TOP_K constant from rag_pipeline
        results = vs.similarity_search_with_relevance_scores(query, k=TOP_K)
        
        # 1. Similarity Threshold — use MAX_DISTANCE constant
        threshold = MAX_DISTANCE
        good_results = [res for res in results if res[1] >= threshold]
        
        fallback_msg_ar = ""
        fallback_msg_en = ""
        if not good_results:
            # Fallback logic: If no exact match, show top 10 alternatives
            good_results = results[:10]
            if good_results:
                fallback_msg_ar = 'عذراً، لم أجد قطعة بهذا الاسم تحديداً، ولكن لدينا تشكيلة رائعة من الخيارات المميزة، هل تودين رؤيتها؟ 🌸'
                fallback_msg_en = "I couldn't find that exact piece, but we have some stunning alternatives you might love. Would you like to see them? 🌸"
            else:
                msg_ar = 'عذراً، لم أجد قطعة بهذا الوصف حالياً. هل تودين رؤية مجموعتنا الجديدة من الزمرد الملكي؟ 🌸'
                msg_en = "I'm sorry, I couldn't find a piece with that description. Would you like to see our new Royal Emerald collection? 🌸"
                return json.dumps({'message_ar': msg_ar, 'message_en': msg_en}, ensure_ascii=False)

        # 2. Data Extraction & Dynamic URL Generation
        result_data = []
        for doc, score in good_results:
            m = doc.metadata
            p_id = m.get('product_id')
            
            # Perform real-time DB check for stock and visibility
            p_db = Product.query.get(p_id)
            if not p_db or p_db.stock_qty is None or p_db.stock_qty <= 0 or not p_db.is_visible:
                continue # Skip out-of-stock or hidden products!

            p_name = m.get('name_en') if lang == 'en' else m.get('name_ar')
            p_name_ar = m.get('name_en') if lang == 'en' else m.get('name_ar') # Override name_ar with English to prevent LLM confusion in English chats
            p_name_en = m.get('name_en') or m.get('name_ar')
            
            # Generate URL-friendly slug
            slug = slugify(p_name)
            full_url = f"/product/{p_id}/{slug}"
            
            result_data.append({
                'id':             p_id,
                'name':           p_name,
                'name_ar':        p_name_ar,
                'name_en':        p_name_en,
                'price':          m.get('price'),
                'original_price': m.get('original_price'),
                'is_on_sale':     m.get('is_on_sale'),
                'image':          m.get('image'),
                'url':            full_url,
                'confidence':     round(score, 3)
            })

        # 3. JSON Response
        return json.dumps({
            'action':     'show_products',
            'data':       result_data,
            'message_ar': fallback_msg_ar,
            'message_en': fallback_msg_en
        }, ensure_ascii=False)

    except Exception as e:
        print(f'[Semantic Search Error] {e}')
        return json.dumps({
            'message_ar': 'عذراً، حدث خطأ في نظام البحث. يرجى المحاولة لاحقاً 🌸',
            'message_en': 'Sorry, something went wrong with the search system. Please try again later 🌸'
        }, ensure_ascii=False)


# ── Tool: Get Order Status ─────────────────────────────────────
def get_order_status_tool(query: str) -> str:
    """
    Get order status. Input: order number as string.
    """
    digit_sequences = re.findall(r'\d+', query)
    if not digit_sequences:
        return json.dumps({
            'message_ar': 'يرجى تزويدي برقم الطلب (مثال: #123) 🌸',
            'message_en': 'Please provide the order number (e.g., #123) 🌸'
        }, ensure_ascii=False)

    last_digits = digit_sequences[-1]
    order = None

    # Try direct lookup by database ID first
    try:
        order_id = int(last_digits)
        order = Order.query.get(order_id)
    except ValueError:
        pass

    # Fallback to searching notes (e.g., for chatbot generated random ID segment like 3165)
    if not order:
        order = Order.query.filter(Order.notes.like(f"%{last_digits}%")).first()

    if not order:
        return json.dumps({
            'message_ar': f'لم أجد طلباً بالرقم #{last_digits} 🌸',
            'message_en': f'I could not find order #{last_digits} 🌸'
        }, ensure_ascii=False)

    # Security: If user is logged in, verify ownership
    if current_user.is_authenticated and order.user_id != current_user.id:
        return json.dumps({
            'message_ar': f'عذراً، هذا الطلب (#{order.display_id}) غير مسجل تحت حسابك. يرجى التأكد من الرقم 🌸',
            'message_en': f'Sorry, this order (#{order.display_id}) is not associated with your account. Please check the number. 🌸'
        }, ensure_ascii=False)

    status_map_ar = {
        'pending':    'قيد الانتظار ⏳',
        'processing': 'جاري التجهيز 📦',
        'delivered':  'تم التوصيل ✅',
        'cancelled':  'ملغي ❌'
    }
    status_map_en = {
        'pending':    'Pending ⏳',
        'processing': 'Processing 📦',
        'delivered':  'Delivered ✅',
        'cancelled':  'Cancelled ❌'
    }
    
    status_ar = status_map_ar.get(order.status, order.status)
    status_en = status_map_en.get(order.status, order.status)
    
    # Include order items
    items_ar = []
    items_en = []
    for item in order.items:
        items_ar.append(f"- {item.product.name_ar} (x{item.quantity})")
        items_en.append(f"- {item.product.name_en} (x{item.quantity})")

    res_ar = f"📦 حالة الطلب #{order.display_id}: {status_ar}\n" + "\n".join(items_ar)
    res_en = f"📦 Status of order #{order.display_id}: {status_en}\n" + "\n".join(items_en)

    return json.dumps({
        'message_ar': res_ar,
        'message_en': res_en
    }, ensure_ascii=False)


# ── Tool: Cancel Order ─────────────────────────────────────────
def cancel_order_tool(query: str) -> str:
    """
    Cancel a pending order. Input: order number.
    """
    digit_sequences = re.findall(r'\d+', query)
    if not digit_sequences:
        return json.dumps({
            'message_ar': 'يرجى تزويدي برقم الطلب لإلغائه 🌸',
            'message_en': 'Please provide the order number to cancel it 🌸'
        }, ensure_ascii=False)

    last_digits = digit_sequences[-1]
    order = None

    # Try direct lookup by database ID first
    try:
        order_id = int(last_digits)
        order = Order.query.get(order_id)
    except ValueError:
        pass

    # Fallback to searching notes (e.g., for chatbot generated random ID segment like 3165)
    if not order:
        order = Order.query.filter(Order.notes.like(f"%{last_digits}%")).first()

    if not order:
        return json.dumps({
            'message_ar': f'لم أجد طلباً بالرقم #{last_digits} 🌸',
            'message_en': f'I could not find order #{last_digits} 🌸'
        }, ensure_ascii=False)

    # Security: If user is logged in, verify ownership
    if current_user.is_authenticated and order.user_id != current_user.id:
        return json.dumps({
            'message_ar': f'عذراً، لا يمكن إلغاء الطلب (#{order.display_id}) لأنه غير مسجل تحت حسابك 🌸',
            'message_en': f'Sorry, this order (#{order.display_id}) cannot be cancelled because it is not associated with your account. 🌸'
        }, ensure_ascii=False)

    if order.status != 'pending':
        return json.dumps({
            'message_ar': f'لا يمكن إلغاء الطلب #{order.display_id} — حالته: {order.status} 🌸',
            'message_en': f'Order #{order.display_id} cannot be cancelled — its status is: {order.status} 🌸'
        }, ensure_ascii=False)

    order.status = 'cancelled'
    db.session.commit()
    return json.dumps({
        'message_ar': f'تم إلغاء طلبك #{order.display_id} بنجاح ✅',
        'message_en': f'Order #{order.display_id} has been cancelled successfully ✅'
    }, ensure_ascii=False)


# ── Tool: Get Promotions ───────────────────────────────────────
def get_promotions_tool(_: str = '') -> str:
    """
    Get current active promotions and coupons.
    """
    coupons = Coupon.query.filter_by(is_active=True).all()
    ann     = Announcement.query.filter_by(is_active=True).first()

    res_ar = ""
    res_en = ""
    if ann:
        res_ar += f'{ann.text_ar}\n'
        res_en += f'{ann.text_en}\n'
    for c in coupons[:3]:
        sym = "%" if c.type == 'percentage' else "JOD"
        res_ar += f'🏷️ كوبون {c.code}: خصم {c.value} {sym}\n'
        res_en += f'🏷️ Coupon {c.code}: {c.value}' + ("% off" if c.type == 'percentage' else " JOD off") + "\n"

    return json.dumps({
        'message_ar': res_ar.strip() or 'لا توجد عروض حالياً 🌸',
        'message_en': res_en.strip() or 'No offers currently 🌸'
    }, ensure_ascii=False)


# ── Tool: Request Return ──────────────────────────────────────
def request_return_tool(query: str) -> str:
    """
    Handle a return request from a customer.
    Collects: order_id, reason.
    Creates a return request record and notifies admin.
    """
    digit_sequences = re.findall(r'\d+', query)
    if not digit_sequences:
        return json.dumps({
            'status':  'need_info',
            'message_ar': 'ما رقم طلبك الذي تريدين إرجاعه؟',
            'message_en': 'What is the order number you want to return?'
        })

    last_digits = digit_sequences[-1]
    order = None

    # Try direct lookup by database ID first
    try:
        order_id = int(last_digits)
        order = Order.query.get(order_id)
    except ValueError:
        pass

    # Fallback to searching notes (e.g., for chatbot generated random ID segment like 3165)
    if not order:
        order = Order.query.filter(Order.notes.like(f"%{last_digits}%")).first()

    if not order:
        return json.dumps({
            'status':  'not_found',
            'message_ar': f'لم أجد طلباً بالرقم #{last_digits}. تحققي من الرقم.',
            'message_en': f'Order #{last_digits} not found. Please check the number.'
        })

    if order.status == 'cancelled':
        return json.dumps({
            'status':  'invalid',
            'message_ar': f'طلبك #{order.display_id} ملغي مسبقاً ولا يمكن إرجاعه.',
            'message_en': f'Order #{order.display_id} is already cancelled.'
        })

    if order.status not in ('delivered',):
        return json.dumps({
            'status':  'invalid',
            'message_ar': (
                f'لا يمكن طلب إرجاع الآن — '
                f'حالة طلبك #{order.display_id} هي: {order.status}'
            ),
            'message_en': (
                f'Cannot request return — '
                f'order #{order.display_id} status is: {order.status}'
            )
        })

    # Create Return Request
    rr = ReturnRequest(
        order_id = order.id,
        user_id  = order.user_id,
        reason   = query, # The agent should have collected the reason
        status   = 'pending'
    )
    db.session.add(rr)

    # Create Admin Notification
    notif = Notification(
        type    = 'return_request',
        message = f'طلب إرجاع جديد للطلب #{order.display_id}',
        is_read = False
    )
    db.session.add(notif)
    db.session.commit()

    return json.dumps({
        'status':  'success',
        'order_id': order.display_id,
        'confirmation_ar': (
            f'✅ تم استلام طلب الإرجاع للطلب #{order.display_id}\n'
            f'سيتم التواصل معكِ لإرجاع القطعة خلال 48 إلى 72 ساعة 🌸'
        ),
        'confirmation_en': (
            f'✅ Return request received for order #{order.display_id}\n'
            f'We will contact you to arrange the return within 48 to 72 hours 🌸'
        )
    })


# ── Tool: Human Handoff ────────────────────────────────────────
def human_handoff_tool(issue_description: str = '') -> str:
    """
    Triggered when user explicitly wants to speak with a real human.
    """
    from flask import request
    session_id = 'anonymous'
    try:
        req_data = request.get_json()
        if req_data and 'session_id' in req_data:
            session_id = req_data['session_id']
    except Exception as e:
        print(f"[human_handoff_tool] Could not read session_id from request: {e}")

    # 1. Create a Support Ticket so it appears in Admin -> Messages
    ticket = SupportTicket(
        user_id=current_user.id if current_user.is_authenticated else None,
        session_id=session_id,
        description=f"طلب تواصل مباشر: {issue_description}",
        status='open'
    )
    db.session.add(ticket)
    db.session.flush() # Get ID

    # 2. Create Admin Notification for the Bell/Dashboard
    notif = Notification(
        type    = 'support_ticket',
        message = f'طلب تواصل جديد من العميل (تذكرة #{ticket.id})',
        link    = f'/admin/chatbot?session={session_id}', # Direct link to conversation
        is_read = False
    )
    db.session.add(notif)
    db.session.commit()

    whatsapp = SiteSetting.get('whatsapp_number') or '9627XXXXXXXX'

    return json.dumps({
        'action':    'human_handoff',
        'whatsapp':  whatsapp,
        'message_ar': (
            'بالطبع! يمكنك التواصل معنا بإحدى الطريقتين 🌸\n'
            '📱 واتساب مباشرة\n'
            '✉️ اترك رسالة وسنتواصل معك قريباً'
        ),
        'message_en': (
            'Of course! You can reach us in two ways 🌸\n'
            '📱 WhatsApp directly\n'
            '✉️ Leave a message and we will contact you soon'
        )
    }, ensure_ascii=False)


# ── Tool: Create Purchase Request ─────────────────────────────
def create_purchase_request_tool(query: str) -> str:
    """
    Handle a request to buy a product or multiple products directly in chat.
    Input: JSON string or text containing product_name, quantity, items, full_name, phone, city, address, user_id, confirmed, coupon_code, coupon_asked.
    IMPORTANT: coupon_asked must be set to true only AFTER the customer has been explicitly asked
    about a discount coupon code and has replied. Never set coupon_asked=true without first asking.
    """
    from flask_login import current_user
    from app.models import User, Order, Product, Coupon
    import json

    # Required fields
    fields = {
        'product_name': None,
        'quantity':     1,
        'items':        None, # New parameter for multiple products
        'full_name':    None,
        'phone':        None,
        'city':         None,
        'address':      None,
        'email':        None,
        'user_id':      None,
        'confirmed':    False,
        'coupon_code':  None,
        'coupon_asked': False  # SAFETY GATE: must be True before showing order summary
    }

    try:
        with open('error_log.txt', 'a', encoding='utf-8') as f:
            from datetime import datetime
            f.write(f"\n--- Tool Input at {datetime.now()} ---\n")
            f.write(query + "\n")
        parsed = json.loads(query)
        for k in fields:
            if k in parsed: fields[k] = parsed[k]
        
        # Clean coupon code
        if fields['coupon_code']:
            fields['coupon_code'] = str(fields['coupon_code']).strip().upper()
    except:
        pass

    # ── COUPON SAFETY GATE ──────────────────────────────────────
    # If not yet confirmed AND the coupon question hasn't been asked yet,
    # force the agent to ask about coupon before showing the order summary.
    if not fields['confirmed'] and not fields['coupon_asked']:
        return json.dumps({
            'status': 'ask_coupon',
            'message_ar': 'قبل أن نكمل طلبكِ، هل لديكِ كوبون خصم تودين إضافته؟ 🌸 (إذا لم يكن لديكِ، قولي "لا" أو "تخطي")',
            'message_en': 'Before we finalize your order, do you have a discount coupon code you\'d like to apply? 🌸 (If not, just say "no" or "skip")'
        }, ensure_ascii=False)

    # If user_id is provided, try to fetch their account info
    user_info_msg_ar = ""
    user_info_msg_en = ""
    
    user = None
    if fields['user_id'] and str(fields['user_id']).lower() != 'null':
        try:
            uid = int(fields['user_id'])
            user = User.query.get(uid)
        except:
            pass
    
    current_user_authenticated = False
    try:
        if current_user and current_user.is_authenticated:
            current_user_authenticated = True
    except Exception:
        pass

    if not user and current_user_authenticated:
        user = current_user

    if user:
        fields['user_id'] = user.id
        # Always use database values for registered users to avoid placeholders
        fields['full_name'] = user.full_name
        fields['phone'] = user.phone
        
        last_order = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).first()
        if last_order:
            if not fields['city']: fields['city'] = last_order.city
            if not fields['address']: fields['address'] = last_order.address

        user_info_msg_ar = f"الاسم المسجل في حسابك هو ({user.full_name}). "
        user_info_msg_en = f"The name registered in your account is ({user.full_name}). "
        
        if user.full_name.lower() in ('regular user', 'demo user', 'user'):
            user_info_msg_ar += "هل تودين استخدام اسم آخر لهذا الطلب؟ "
            user_info_msg_en += "Would you like to use a different name for this order? "

    # Determine items list to resolve
    items_to_resolve = []
    if fields['items'] and isinstance(fields['items'], list) and len(fields['items']) > 0:
        items_to_resolve = fields['items']
    elif fields['product_name']:
        items_to_resolve = [{
            'product_name': fields['product_name'],
            'quantity': fields['quantity'] or 1
        }]

    missing = []
    if not items_to_resolve: missing.append('اسم المنتج' if 'ar' in query else 'product name')
    if not fields['full_name']: missing.append('الاسم الكامل' if 'ar' in query else 'full name')
    if not fields['phone']: missing.append('رقم الهاتف' if 'ar' in query else 'phone number')
    if not fields['city']: missing.append('المحافظة/المدينة' if 'ar' in query else 'city')
    if not fields['address']: missing.append('العنوان بالتفصيل' if 'ar' in query else 'detailed address')
    if not current_user_authenticated and not fields.get('email'):
        missing.append('البريد الإلكتروني' if 'ar' in query else 'email')

    if missing:
        return json.dumps({
            'status': 'need_info',
            'missing': missing,
            'message_ar': f"{user_info_msg_ar}لإتمام طلبك، يرجى تزويدي بـ: {', '.join(missing)} 🌸",
            'message_en': f"{user_info_msg_en}To complete your order, please provide: {', '.join(missing)} 🌸"
        }, ensure_ascii=False)

    # Resolve all items to actual products
    resolved_items = []
    overall_subtotal = 0.0
    
    from app.chatbot.rag_pipeline import load_vector_store, PRODUCTS_COL, MAX_DISTANCE
    
    for item in items_to_resolve:
        p_name = item.get('product_name')
        p_qty = int(item.get('quantity', 1) or 1)
        
        if not p_name:
            continue
            
        product = None
        # RAG Search
        try:
            vs = load_vector_store(PRODUCTS_COL)
            search_results = vs.similarity_search_with_relevance_scores(p_name, k=1)
            if search_results and search_results[0][1] >= MAX_DISTANCE:
                p_id = search_results[0][0].metadata.get('product_id')
                product = Product.query.get(p_id)
        except Exception as e:
            print(f"[Create Order RAG Error] {e}")

        # Fallback to simple DB search
        if not product:
            product = Product.query.filter(
                (Product.name_ar.ilike(f'%{p_name}%')) |
                (Product.name_en.ilike(f'%{p_name}%'))
            ).first()

        if not product:
            return json.dumps({
                'status': 'not_found',
                'message_ar': f'عذراً، لم أجد منتجاً باسم "{p_name}". هل يمكنك التأكد من الاسم؟ 🌸',
                'message_en': f'Sorry, I could not find a product named "{p_name}". Please check the name. 🌸'
            }, ensure_ascii=False)

        # Stock check
        if product.stock_qty is not None and product.stock_qty <= 0:
            return json.dumps({
                'status': 'out_of_stock',
                'message_ar': f'عذراً، منتج "{product.name_ar}" منتهي المخزون حالياً ولا يمكن طلبه. 🌸',
                'message_en': f'Sorry, the product "{product.name_en}" is currently out of stock and cannot be ordered. 🌸'
            }, ensure_ascii=False)
        elif product.stock_qty is not None and product.stock_qty < p_qty:
            return json.dumps({
                'status': 'insufficient_stock',
                'message_ar': f'عذراً، يتوفر حالياً {product.stock_qty} قطعة فقط من "{product.name_ar}". هل تودين تعديل الكمية؟ 🌸',
                'message_en': f'Sorry, only {product.stock_qty} pieces of "{product.name_en}" are currently in stock. Would you like to adjust the quantity? 🌸'
            }, ensure_ascii=False)

        unit_price = float(product.sale_price_jod if product.is_on_sale else product.price_jod)
        item_subtotal = unit_price * p_qty
        overall_subtotal += item_subtotal
        
        resolved_items.append({
            'product_id': product.id,
            'product_name_ar': product.name_ar,
            'product_name_en': product.name_en,
            'quantity': p_qty,
            'unit_price': unit_price,
            'subtotal': item_subtotal
        })

    # Calculate dynamic delivery fee
    from app.utils.delivery import get_delivery_fee
    items_data = [{'product_id': item['product_id'], 'quantity': item['quantity']} for item in resolved_items]
    delivery_fee = get_delivery_fee(overall_subtotal, items_data)
    
    # Calculate Coupon Discount
    discount = 0.0
    coupon_msg_ar = ""
    coupon_msg_en = ""
    
    if fields['coupon_code']:
        coupon = Coupon.query.filter_by(code=fields['coupon_code'], is_active=True).first()
        if coupon:
            is_valid, msg, debug = coupon.is_valid(overall_subtotal)
            if is_valid:
                discount = float(coupon.calculate_discount(overall_subtotal))
                coupon_msg_ar = f"✅ تم تطبيق الكوبون {fields['coupon_code']}: -{discount:.2f} JOD\n"
                coupon_msg_en = f"✅ Coupon {fields['coupon_code']} applied: -{discount:.2f} JOD\n"
            else:
                coupon_msg_ar = f"❌ الكوبون غير صالح: {msg}\n"
                coupon_msg_en = f"❌ Coupon invalid: {msg}\n"
        else:
            coupon_msg_ar = f"❌ الكوبون {fields['coupon_code']} غير موجود.\n"
            coupon_msg_en = f"❌ Coupon {fields['coupon_code']} not found.\n"

    total = overall_subtotal - discount + delivery_fee
    
    # Awaiting Confirmation Summary Response
    if not fields['confirmed']:
        coupon_line_ar = f"🎫 خصم الكوبون: -{discount:.2f} JOD\n" if discount > 0 else ""
        coupon_line_en = f"🎫 Coupon Discount: -{discount:.2f} JOD\n" if discount > 0 else ""

        items_summary_ar = []
        items_summary_en = []
        for item in resolved_items:
            items_summary_ar.append(f"- {item['product_name_ar']} (عدد {item['quantity']}) : {item['subtotal']:.2f} JOD")
            items_summary_en.append(f"- {item['product_name_en']} (x{item['quantity']}) : {item['subtotal']:.2f} JOD")
            
        items_list_ar = "\n".join(items_summary_ar)
        items_list_en = "\n".join(items_summary_en)

        return json.dumps({
            'status': 'awaiting_confirmation',
            'summary_ar': (
                f"📦 ملخص طلبكِ النهائي:\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{items_list_ar}\n"
                f"💰 المجموع الفرعي: {overall_subtotal:.2f} JOD\n"
                f"{coupon_line_ar}"
                f"🚚 رسوم التوصيل: {delivery_fee:.2f} JOD\n"
                f"✨ المجموع الإجمالي: {total:.2f} JOD\n\n"
                f"{coupon_msg_ar}"
                f"الاسم: {fields['full_name']}\n"
                f"الهاتف: {fields['phone']}\n"
                f"العنوان: {fields['city']}, {fields['address']}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"هل تودين إضافة أي شيء آخر للطلب أم أؤكده لكِ بهذا السعر؟ 🌸"
            ),
            'summary_en': (
                f"📦 Final Order Summary:\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{items_list_en}\n"
                f"💰 Subtotal: {overall_subtotal:.2f} JOD\n"
                f"{coupon_line_en}"
                f"🚚 Delivery Fee: {delivery_fee:.2f} JOD\n"
                f"✨ Total Amount: {total:.2f} JOD\n\n"
                f"{coupon_msg_en}"
                f"Name: {fields['full_name']}\n"
                f"Phone: {fields['phone']}\n"
                f"Address: {fields['city']}, {fields['address']}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Should I confirm the order at this price? 🌸"
            )
        }, ensure_ascii=False)

    # If confirmed=True, construct OTP verification session payload
    from flask import session
    lang = session.get('lang', 'ar')
    
    legacy_product_name = resolved_items[0]['product_name_en'] if lang == 'en' else resolved_items[0]['product_name_ar']
    if len(resolved_items) > 1:
        legacy_product_name = ", ".join([item['product_name_en'] if lang == 'en' else item['product_name_ar'] for item in resolved_items])

    otp_payload = json.dumps({
        'product_id': resolved_items[0]['product_id'], # Legacy first item
        'product_name': legacy_product_name,
        'quantity': resolved_items[0]['quantity'], # Legacy first item
        'items': [{
            'product_id': item['product_id'],
            'product_name': item['product_name_en'] if lang == 'en' else item['product_name_ar'],
            'quantity': item['quantity'],
            'unit_price': item['unit_price']
        } for item in resolved_items],
        'full_name': fields['full_name'],
        'phone': fields['phone'],
        'city': fields['city'],
        'address': fields['address'],
        'coupon_code': fields['coupon_code'],
        'discount': discount,
        'subtotal': overall_subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'email': fields.get('email'),
        'user_id': fields['user_id']
    }, ensure_ascii=False)
    
    return send_order_otp_tool(otp_payload)


# ── Tool: Send Order OTP ───────────────────────────────────────
def send_order_otp_tool(query: str) -> str:
    """
    Generate an OTP, store the pending order details in Flask session, and email the code to the customer.
    Input: A JSON string containing "product_id", "product_name", "quantity", "items", "full_name", "phone", "city", "address", "coupon_code", "discount", "subtotal", "delivery_fee", "total", "email", "user_id".
    """
    import random
    import time
    from flask import session
    from flask_mail import Message
    from app import mail
    from flask_login import current_user

    try:
        data = json.loads(query)
        otp_code = str(random.randint(100000, 999999))
        print(f"[DEBUG CHATBOT OTP] Code is: {otp_code}")

        # Recipient email priorities: 1. Current user email, 2. Field from query
        recipient_email = None
        try:
            if current_user and current_user.is_authenticated:
                recipient_email = current_user.email
        except Exception:
            pass
        if not recipient_email:
            recipient_email = data.get('email')
        
        # Save details in Flask session
        session['chatbot_pending_order'] = {
            'otp': otp_code,
            'timestamp': time.time(),
            'product_id': data.get('product_id'),
            'product_name': data.get('product_name'),
            'quantity': data.get('quantity', 1),
            'items': data.get('items'),
            'full_name': data.get('full_name'),
            'phone': data.get('phone'),
            'city': data.get('city'),
            'address': data.get('address'),
            'coupon_code': data.get('coupon_code'),
            'discount': data.get('discount', 0),
            'subtotal': data.get('subtotal', 0.0),
            'delivery_fee': data.get('delivery_fee', 0.0),
            'total': data.get('total', 0.0),
            'email': recipient_email,
            'user_id': data.get('user_id')
        }

        # Send email via SMTP
        if recipient_email:
            try:
                msg = Message("ORYA - Chatbot Order Verification Code", recipients=[recipient_email])
                msg.body = (
                    f"Hello {data.get('full_name') or 'Customer'},\n\n"
                    f"Thank you for confirming your order request through our AI Assistant!\n\n"
                    f"Your 6-digit verification code is: {otp_code}\n\n"
                    f"Please reply directly to the AI Chatbot with this code to complete and confirm your order.\n"
                    f"This code will expire in 5 minutes.\n\n"
                    f"Thank you,\nORYA Luxury Jewelry Store"
                )
                mail.send(msg)
            except Exception as e:
                print(f"[Chatbot OTP Email Send Error] {e}")

        # Bilingual response payload
        lang = session.get('lang', 'ar')
        msg_en = 'I have sent a verification code to your email. Please reply with the code to confirm your order.'
        msg_ar = 'لقد أرسلت رمز تحقق إلى بريدك الإلكتروني. يرجى الرد بالرمز لتأكيد طلبك.'

        return json.dumps({
            'status': 'sent',
            'message_ar': msg_ar,
            'message_en': msg_en
        }, ensure_ascii=False)

    except Exception as e:
        print(f"[send_order_otp_tool Error] {e}")
        return json.dumps({
            'status': 'error',
            'message_ar': 'حدث خطأ أثناء إرسال رمز التحقق. يرجى المحاولة لاحقاً 🌸',
            'message_en': 'An error occurred while sending the verification code. Please try again later 🌸'
        }, ensure_ascii=False)
