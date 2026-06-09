from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.models import Product
from app import db

products_bp = Blueprint('products', __name__)

@products_bp.route('/')
def home():
    new_arrivals = Product.query.filter_by(is_visible=True, is_new=True).limit(4).all()
    best_sellers = Product.query.filter_by(is_visible=True).order_by(Product.sales_count.desc()).limit(4).all()
    
    # If not enough data, just show some products
    if not new_arrivals:
        new_arrivals = Product.query.filter_by(is_visible=True).limit(4).all()
    if not best_sellers:
        best_sellers = Product.query.filter_by(is_visible=True).offset(4).limit(4).all()
        
    # Fetch user wishlist if logged in
    from flask_login import current_user
    user_wishlist = []
    if current_user.is_authenticated:
        from app.models import Wishlist
        user_wishlist = [w.product_id for w in Wishlist.query.filter_by(user_id=current_user.id).all()]

    # Fetch active announcement for the Ad Modal
    from app.models import Announcement
    from flask import session
    active_ann = Announcement.query.filter_by(is_active=True).first()
    current_ad_text = None
    dynamic_bg_color = None
    ad_modal_link = None
    if active_ann:
        lang = session.get('lang', 'ar')
        current_ad_text = active_ann.text_ar if lang == 'ar' else active_ann.text_en
        dynamic_bg_color = active_ann.bg_color
        ad_modal_link = active_ann.link

    return render_template('user/index.html', 
                           new_arrivals=new_arrivals, 
                           best_sellers=best_sellers,
                           user_wishlist=user_wishlist,
                           current_ad_text=current_ad_text,
                           dynamic_bg_color=dynamic_bg_color,
                           ad_modal_link=ad_modal_link,
                           active_ann=active_ann)

@products_bp.route('/products/<category>')
def product_list(category):
    # Fetch initial products for the server-side render
    if category == 'all':
        products = Product.query.filter_by(is_visible=True).all()
    else:
        products = Product.query.filter_by(category=category, is_visible=True).all()
    
    total_count = len(products)
    
    # Fetch user wishlist if logged in
    from flask_login import current_user
    user_wishlist = []
    if current_user.is_authenticated:
        from app.models import Wishlist
        user_wishlist = [w.product_id for w in Wishlist.query.filter_by(user_id=current_user.id).all()]

    return render_template('user/products.html', category=category, products=products, total_count=total_count, user_wishlist=user_wishlist)

@products_bp.route('/product/<int:id>')
@products_bp.route('/product/<int:id>/<slug>')
def product_detail(id, slug=None):
    product = Product.query.get_or_404(id)
    is_wishlisted = False
    if current_user.is_authenticated:
        from app.models import Wishlist
        is_wishlisted = Wishlist.query.filter_by(user_id=current_user.id, product_id=id).first() is not None
    return render_template('user/product.html', product=product, is_wishlisted=is_wishlisted)

# ── Fallback routes: handle AI-generated URL variants ──────────────
# The chatbot AI sometimes generates /products/<id> instead of /product/<id>
# These routes catch those cases and redirect to the correct URL.

@products_bp.route('/products/<int:id>')
def product_detail_redirect(id):
    """Redirect /products/<id> → /product/<id> (chatbot sometimes generates wrong URL)"""
    return redirect(url_for('products.product_detail', id=id), code=301)

@products_bp.route('/wishlist')
@login_required
def wishlist():
    from app.models import Wishlist, Product
    items = Wishlist.query.filter_by(user_id=current_user.id).all()
    wishlist_products = []
    for item in items:
        p = Product.query.get(item.product_id)
        if p:
            wishlist_products.append(p)
    return render_template('user/wishlist.html', wishlist_items=wishlist_products)

@products_bp.route('/search')
def search():
    q = request.args.get('q', '')
    from app.utils.search import get_search_query
    products = get_search_query(q).limit(12).all()
    return render_template('user/search.html', q=q, products=products)

@products_bp.route('/about')
def about():
    return render_template('user/about.html')

@products_bp.route('/contact')
def contact():
    return render_template('user/contact.html')
@products_bp.route('/checkout')
@login_required
def checkout():
    return render_template('user/checkout.html')

@products_bp.route('/my-orders')
@login_required
def my_orders():
    # Fetch orders for the current user
    from app.models import Order
    from sqlalchemy import desc
    orders = Order.query.filter_by(user_id=current_user.id).order_by(desc(Order.created_at)).all()
    return render_template('user/my_orders.html', orders=orders)

@products_bp.route('/order-success/<int:order_id>')
@login_required
def order_success(order_id):
    return render_template('user/order_success.html', order_id=order_id)

@products_bp.route('/refund')
def refund_policy():
    return render_template('user/refund.html')

@products_bp.route('/shipping')
def shipping_policy():
    return render_template('user/shipping.html')

@products_bp.route('/privacy')
def privacy_policy():
    return render_template('user/privacy.html')

@products_bp.route('/terms')
def terms_conditions():
    return render_template('user/terms.html')

@products_bp.route('/accessibility')
def accessibility_statement():
    return render_template('user/accessibility.html')
