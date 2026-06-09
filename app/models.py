from app import db
from datetime import datetime
from sqlalchemy import Numeric

from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True,
                              nullable=False)
    full_name     = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True,
                              nullable=False)
    phone         = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), default='user')
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

    # Relationships
    orders         = db.relationship('Order', backref='user',
                                     lazy=True)
    wishlist       = db.relationship('Wishlist', backref='user',
                                     lazy=True)
    reviews        = db.relationship('Review', backref='user',
                                     lazy=True)
    wishlist_share = db.relationship('WishlistShare',
                                     backref='user',
                                     uselist=False)

class Product(db.Model):
    __tablename__ = 'products'
    id              = db.Column(db.Integer, primary_key=True)
    name_ar         = db.Column(db.String(200), nullable=False)
    name_en         = db.Column(db.String(200), nullable=False)
    category        = db.Column(db.String(50), nullable=False)
    # Values: necklaces|earrings|bracelets|rings|
    #         belly-rings|anklets|sets
    price_jod       = db.Column(Numeric(10, 3), nullable=False)
    sale_price_jod  = db.Column(Numeric(10, 3), nullable=True)
    is_on_sale      = db.Column(db.Boolean, default=False)
    material        = db.Column(db.String(50), nullable=False)
    # Values: gold|silver|gold-plated
    length          = db.Column(db.String(50), nullable=True)
    size            = db.Column(db.String(50), nullable=True)
    stone           = db.Column(db.String(100), nullable=True)
    weight          = db.Column(db.String(50), nullable=True)
    description_ar  = db.Column(db.Text, nullable=True)
    description_en  = db.Column(db.Text, nullable=True)
    care_ar         = db.Column(db.Text, nullable=True)
    care_en         = db.Column(db.Text, nullable=True)
    stock_qty       = db.Column(db.Integer, default=0)
    is_new          = db.Column(db.Boolean, default=False)
    is_visible      = db.Column(db.Boolean, default=True)
    sales_count     = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    images    = db.relationship('ProductImage',
                                backref='product',
                                lazy=True,
                                cascade='all, delete-orphan',
                                order_by='ProductImage.sort_order')
    reviews   = db.relationship('Review', backref='product',
                                lazy=True)
    wishlist  = db.relationship('Wishlist', backref='product',
                                lazy=True)

    @property
    def primary_image(self):
        primary = next((img for img in self.images
                        if img.is_primary), None)
        return primary.image_path if primary \
               else (self.images[0].image_path
                     if self.images else None)

    @property
    def avg_rating(self):
        approved = [r for r in self.reviews if r.is_approved]
        if not approved: return 0
        return round(sum(r.stars for r in approved)
                     / len(approved), 1)

    @property
    def review_count(self):
        return len([r for r in self.reviews if r.is_approved])

    @property
    def effective_price(self):
        return self.sale_price_jod \
               if self.is_on_sale and self.sale_price_jod \
               else self.price_jod

    @property
    def price(self):
        return self.price_jod

    @property
    def sale_price(self):
        return self.sale_price_jod

    @property
    def stock_status(self):
        if self.stock_qty == 0: return 'out_of_stock'
        if self.stock_qty <= 3: return 'low_stock'
        return 'in_stock'

    def to_dict(self):
        return {
            'id': self.id,
            'name_ar': self.name_ar,
            'name_en': self.name_en,
            'category': self.category,
            'price': float(self.price_jod),
            'sale_price': float(self.sale_price_jod) if self.sale_price_jod else None,
            'is_on_sale': self.is_on_sale,
            'material': self.material,
            'primary_image': self.primary_image,
            'secondary_image': self.images[1].image_path if len(self.images) > 1 else None,
            'is_new': self.is_new,
            'stock_qty': self.stock_qty,
            'weight': self.weight,
            'avg_rating': self.avg_rating,
            'review_count': self.review_count
        }

class ProductImage(db.Model):
    __tablename__ = 'product_images'
    id          = db.Column(db.Integer, primary_key=True)
    product_id  = db.Column(db.Integer,
                            db.ForeignKey('products.id'),
                            nullable=False)
    image_path  = db.Column(db.String(500), nullable=False)
    is_primary  = db.Column(db.Boolean, default=False)
    sort_order  = db.Column(db.Integer, default=0)

class Order(db.Model):
    __tablename__ = 'orders'
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer,
                                 db.ForeignKey('users.id'),
                                 nullable=False)
    STATUS_CHOICES = ('pending_verification', 'pending', 'confirmed', 'processing', 'delivered', 'cancelled')
    status           = db.Column(db.String(20),
                                 default='pending_verification')
    # Values correspond to STATUS_CHOICES
    subtotal_jod     = db.Column(Numeric(10, 3), nullable=False)
    discount_jod     = db.Column(Numeric(10, 3), default=0)
    delivery_fee_jod = db.Column(Numeric(10, 3), default=0)
    total_jod        = db.Column(Numeric(10, 3), nullable=False)
    coupon_code      = db.Column(db.String(50), nullable=True)
    payment_method   = db.Column(db.String(50),
                                 default='cash_on_delivery')
    full_name        = db.Column(db.String(120), nullable=False)
    phone            = db.Column(db.String(20), nullable=False)
    city             = db.Column(db.String(100), nullable=False)
    area             = db.Column(db.String(100), nullable=False)
    address          = db.Column(db.Text, nullable=False)
    national_id      = db.Column(db.String(20), nullable=True) # Identity verification
    notes            = db.Column(db.Text, nullable=True)
    admin_notes      = db.Column(db.Text, nullable=True)
    created_at       = db.Column(db.DateTime,
                                 default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime,
                                 default=datetime.utcnow,
                                 onupdate=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order',
                            lazy=True,
                            cascade='all, delete-orphan')

    @property
    def display_id(self):
        if self.notes and 'Chatbot verified order ID: ' in self.notes:
            parts = self.notes.split('Chatbot verified order ID: ')
            if len(parts) > 1:
                return parts[1].strip()
        return f"ORY-{self.id}"

    def to_dict(self):
        return {
            'id': self.id,
            'display_id': self.display_id,
            'status': self.status,
            'subtotal': float(self.subtotal_jod),
            'discount': float(self.discount_jod),
            'delivery_fee': float(self.delivery_fee_jod),
            'total': float(self.total_jod),
            'coupon_code': self.coupon_code,
            'payment_method': self.payment_method,
            'full_name': self.full_name,
            'phone': self.phone,
            'city': self.city,
            'area': self.area,
            'address': self.address,
            'national_id': self.national_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'items': [item.to_dict() for item in self.items]
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id            = db.Column(db.Integer, primary_key=True)
    order_id      = db.Column(db.Integer,
                              db.ForeignKey('orders.id'),
                              nullable=False)
    product_id    = db.Column(db.Integer,
                              db.ForeignKey('products.id'),
                              nullable=False)
    quantity      = db.Column(db.Integer, nullable=False)
    unit_price_jod= db.Column(Numeric(10, 3), nullable=False)

    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name_ar': self.product.name_ar,
            'product_name_en': self.product.name_en,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price_jod),
            'total_price': float(self.unit_price_jod * self.quantity),
            'image': self.product.primary_image
        }

class Wishlist(db.Model):
    __tablename__ = 'wishlist'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id'),
    )
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer,
                           db.ForeignKey('users.id'),
                           nullable=False)
    product_id = db.Column(db.Integer,
                           db.ForeignKey('products.id'),
                           nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WishlistShare(db.Model):
    __tablename__ = 'wishlist_shares'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer,
                            db.ForeignKey('users.id'),
                            unique=True, nullable=False)
    share_token = db.Column(db.String(64), unique=True,
                            nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    __tablename__ = 'reviews'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer,
                            db.ForeignKey('users.id'),
                            nullable=False)
    product_id  = db.Column(db.Integer,
                            db.ForeignKey('products.id'),
                            nullable=False)
    stars       = db.Column(db.Integer, nullable=False)
    comment     = db.Column(db.Text, nullable=True)
    is_approved = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Coupon(db.Model):
    __tablename__ = 'coupons'
    id            = db.Column(db.Integer, primary_key=True)
    code          = db.Column(db.String(50), unique=True,
                              nullable=False)
    type          = db.Column(db.String(20), nullable=False)
    # Values: percentage|fixed
    value         = db.Column(Numeric(10, 3), nullable=False)
    usage_limit   = db.Column(db.Integer, nullable=True)
    used_count    = db.Column(db.Integer, default=0)
    min_order_jod = db.Column(Numeric(10, 3), default=0)
    is_active     = db.Column(db.Boolean, default=True)
    expires_at    = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def is_valid(self, subtotal):
        import datetime
        
        # Comprehensive debugging dictionary
        debug_info = {
            'is_active': self.is_active,
            'expires_at': str(self.expires_at) if self.expires_at else None,
            'current_time_utc': str(datetime.datetime.utcnow()),
            'used_count': self.used_count,
            'usage_limit': self.usage_limit,
            'min_order_jod': float(self.min_order_jod) if self.min_order_jod else 0.0,
            'provided_subtotal': float(subtotal)
        }

        # 1. Check if active
        if not self.is_active:
            debug_info['reason'] = 'Coupon is marked as inactive in database.'
            return False, "كوبون غير صالح أو غير نشط", debug_info
            
        # 2. Check expiry date (handling UTC time properly)
        if self.expires_at and datetime.datetime.utcnow() > self.expires_at:
            debug_info['reason'] = 'Coupon has passed its expiry_date.'
            return False, "عذراً، هذا الكوبون منتهي الصلاحية", debug_info
            
        # 3. Check usage limit
        if self.usage_limit and self.used_count >= self.usage_limit:
            debug_info['reason'] = 'Coupon usage limit has been reached.'
            return False, "تم الوصول للحد الأقصى لاستخدام هذا الكوبون", debug_info
            
        # 4. Check minimum order amount
        if float(subtotal) < (float(self.min_order_jod) if self.min_order_jod else 0.0):
            debug_info['reason'] = f"Minimum order amount ({self.min_order_jod} JOD) not met."
            return False, f"الحد الأدنى للطلب لتفعيل الكوبون هو {self.min_order_jod} JOD", debug_info
            
        debug_info['reason'] = 'Coupon is perfectly valid.'
        return True, "كوبون صالح", debug_info

    def calculate_discount(self, subtotal):
        if self.type == 'percentage':
            return round(float(subtotal) * float(self.value)
                         / 100, 3)
        return min(float(self.value), float(subtotal))

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id         = db.Column(db.Integer, primary_key=True)
    text_ar    = db.Column(db.String(500), nullable=False)
    text_en    = db.Column(db.String(500), nullable=False)
    is_active  = db.Column(db.Boolean, default=False)
    bg_color   = db.Column(db.String(20), default='#C9A96E')
    link       = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'text_ar': self.text_ar,
            'text_en': self.text_en,
            'is_active': self.is_active,
            'bg_color': self.bg_color,
            'link': self.link,
            'created_at': self.created_at.isoformat()
        }

class SiteSetting(db.Model):
    __tablename__ = 'site_settings'
    id        = db.Column(db.Integer, primary_key=True)
    key       = db.Column(db.String(100), unique=True,
                          nullable=False)
    value_ar  = db.Column(db.Text, nullable=True)
    value_en  = db.Column(db.Text, nullable=True)

    @staticmethod
    def get(key, lang='ar'):
        setting = SiteSetting.query.filter_by(key=key).first()
        if not setting: return ''
        return (setting.value_ar if lang == 'ar'
                else setting.value_en) or ''

    @staticmethod
    def get_all():
        settings = SiteSetting.query.all()
        return {s.key: {'ar': s.value_ar, 'en': s.value_en}
                for s in settings}

class ChatbotLog(db.Model):
    __tablename__ = 'chatbot_logs'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer,
                             db.ForeignKey('users.id'),
                             nullable=True)
    session_id   = db.Column(db.String(100), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_reply    = db.Column(db.Text, nullable=False)
    lang         = db.Column(db.String(5), default='ar')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': User.query.get(self.user_id).username if self.user_id else None,
            'session_id': self.session_id,
            'user_message': self.user_message,
            'bot_reply': self.bot_reply,
            'lang': self.lang,
            'created_at': self.created_at.isoformat()
        }

class RecentlyViewed(db.Model):
    __tablename__ = 'recently_viewed'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer,
                           db.ForeignKey('users.id'),
                           nullable=True)
    session_id = db.Column(db.String(100), nullable=False)
    product_id = db.Column(db.Integer,
                           db.ForeignKey('products.id'),
                           nullable=False)
    viewed_at  = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    product = db.relationship('Product')

class Notification(db.Model):
    __tablename__ = 'notifications'
    id         = db.Column(db.Integer, primary_key=True)
    type       = db.Column(db.String(50)) # e.g., 'new_order', 'return_request', 'support_ticket'
    message    = db.Column(db.Text, nullable=False)
    link       = db.Column(db.String(500), nullable=True) # Direct link for admin
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }

class ReturnRequest(db.Model):
    __tablename__ = 'return_requests'
    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey('orders.id'))
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reason     = db.Column(db.Text)
    status     = db.Column(db.String(20), default='pending') # pending / contacted / resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship('Order', backref='return_requests')

class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id  = db.Column(db.String(100))
    description = db.Column(db.Text)
    status      = db.Column(db.String(20), default='open') # open / closed
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='support_tickets')

