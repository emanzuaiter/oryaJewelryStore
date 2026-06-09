"""seed_data.py — ORYA Jewelry Store Seed Script
Run with: python seed_data.py
Flags:
  --coupons-only   : only add coupons and discounts
  --all            : run everything (default)
"""
import sys, os, random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db, bcrypt
from app.models import User, Product, Order, OrderItem, Wishlist, Review, Coupon

app = create_app()

# ── STATIC DATA ──────────────────────────────────────────────────────────────

USERS_DATA = [
    {"username": "sara_m",   "full_name": "Sara AlMohammad",  "email": "sara@orya.jo",   "phone": "0791234501"},
    {"username": "nour_k",   "full_name": "Nour AlKurdi",     "email": "nour@orya.jo",   "phone": "0791234502"},
    {"username": "lina_r",   "full_name": "Lina AlRasheed",   "email": "lina@orya.jo",   "phone": "0791234503"},
    {"username": "dana_h",   "full_name": "Dana AlHasan",     "email": "dana@orya.jo",   "phone": "0791234504"},
    {"username": "rana_s",   "full_name": "Rana AlSalem",     "email": "rana@orya.jo",   "phone": "0791234505"},
    {"username": "mona_a",   "full_name": "Mona AlAbdullah",  "email": "mona@orya.jo",   "phone": "0791234506"},
    {"username": "haya_b",   "full_name": "Haya AlBuraiki",   "email": "haya@orya.jo",   "phone": "0791234507"},
    {"username": "rita_n",   "full_name": "Rita AlNasr",      "email": "rita@orya.jo",   "phone": "0791234508"},
    {"username": "dima_f",   "full_name": "Dima AlFadel",     "email": "dima@orya.jo",   "phone": "0791234509"},
    {"username": "layla_q",  "full_name": "Layla AlQadi",     "email": "layla@orya.jo",  "phone": "0791234510"},
    {"username": "farah_z",  "full_name": "Farah AlZahrani",  "email": "farah@orya.jo",  "phone": "0791234511"},
    {"username": "reem_t",   "full_name": "Reem AlTamimi",    "email": "reem@orya.jo",   "phone": "0791234512"},
]

CITIES   = ["Amman", "Irbid", "Zarqa", "Aqaba", "Mafraq", "Jerash", "Karak"]
AREAS    = ["Jubeiha", "Sweileh", "Shmeisani", "Downtown", "7th Circle", "Rabyeh", "Marj Hamam"]
STATUSES = ["pending", "processing", "delivered", "delivered", "delivered", "cancelled"]

COMMENTS = [
    "Amazing quality, worth every penny!",
    "Elegant packaging and excellent product condition.",
    "Best gift I gave myself, thank you ORYA!",
    "Colors match the photos exactly, very happy!",
    "Fast delivery and beautiful product, will order again.",
    "High quality and durable, highly recommend!",
    "Very delicate and elegant, well done.",
    "Arrived perfectly, price is very reasonable.",
]

# ── COUPONS to seed ──────────────────────────────────────────────────────────
COUPONS_DATA = [
    # code          type          value   min_order  limit  used   active  expires_in_days
    ("ORYA10",      "percentage", 10.0,   0.0,       None,  8,     True,   30),
    ("ORYA20",      "percentage", 20.0,   20.0,      100,   15,    True,   60),
    ("WELCOME5",    "fixed",      5.0,    0.0,       200,   42,    True,   90),
    ("GOLD15",      "percentage", 15.0,   15.0,      50,    7,     True,   45),
    ("VIP25",       "percentage", 25.0,   30.0,      30,    3,     True,   120),
    ("SUMMER30",    "percentage", 30.0,   25.0,      50,    22,    True,   14),
    ("FREESHIP",    "fixed",      3.0,    0.0,       None,  31,    True,   30),
    ("FLASH50",     "percentage", 50.0,   40.0,      20,    20,    False,  -1),   # expired/inactive
    ("NEWCUST",     "fixed",      2.0,    0.0,       500,   0,     True,   180),
    ("ORYA2025",    "percentage", 12.0,   10.0,      75,    5,     True,   365),
]

# ── DISCOUNT CONFIG (category / percentage) ──────────────────────────────────
CATEGORY_DISCOUNTS = [
    ("earrings",  15),   # 15% off earrings
    ("anklets",   10),   # 10% off anklets
    ("sets",      20),   # 20% off sets (bundles)
]
# Also apply spot discounts to random individual products
SPOT_DISCOUNT_COUNT = 8     # number of random products to put on sale
SPOT_DISCOUNT_RANGE = (8, 25)  # % range


# ════════════════════════════════════════════════════════════════════════════
def seed_coupons():
    """Add coupons — skips existing codes."""
    count = 0
    for (code, ctype, value, min_ord, limit, used, active, days) in COUPONS_DATA:
        if Coupon.query.filter_by(code=code).first():
            print(f"   [SKIP] Coupon '{code}' already exists")
            continue
        expires = None
        if days > 0:
            expires = datetime.utcnow() + timedelta(days=days)
        elif days == -1:
            expires = datetime.utcnow() - timedelta(days=1)   # already expired

        c = Coupon(
            code=code,
            type=ctype,
            value=value,
            min_order_jod=min_ord,
            usage_limit=limit,
            used_count=used,
            is_active=active,
            expires_at=expires,
        )
        db.session.add(c)
        count += 1

    db.session.commit()
    print(f"[OK] {count} coupons added.")
    return count


def seed_discounts():
    """Apply category bulk discounts + random spot discounts to products."""
    disc_count = 0

    # A. Category discounts
    for (cat, pct) in CATEGORY_DISCOUNTS:
        prods = Product.query.filter_by(category=cat).all()
        for p in prods:
            if not p.is_on_sale:
                p.is_on_sale = True
                p.sale_price_jod = round(float(p.price_jod) * (1 - pct / 100), 3)
                disc_count += 1

    # B. Random spot discounts on individual products (any category)
    all_prods = Product.query.filter_by(is_on_sale=False).all()
    spot_targets = random.sample(all_prods, min(SPOT_DISCOUNT_COUNT, len(all_prods)))
    for p in spot_targets:
        pct = random.randint(*SPOT_DISCOUNT_RANGE)
        p.is_on_sale = True
        p.sale_price_jod = round(float(p.price_jod) * (1 - pct / 100), 3)
        disc_count += 1

    db.session.commit()
    print(f"[OK] {disc_count} product discounts applied.")
    return disc_count


# ════════════════════════════════════════════════════════════════════════════
def seed_users_orders():
    pw_hash  = bcrypt.generate_password_hash("1234").decode("utf-8")
    products = Product.query.filter(Product.stock_qty > 0).all()
    if not products:
        print("[ERROR] No products found! Add products first.")
        return

    print(f"[OK] Found {len(products)} products.")

    # Users
    created_users = []
    for ud in USERS_DATA:
        existing = User.query.filter_by(username=ud["username"]).first()
        if existing:
            print(f"   [SKIP] User '{ud['username']}' already exists")
            created_users.append(existing)
            continue
        days_ago = random.randint(1, 90)
        u = User(
            username=ud["username"],
            full_name=ud["full_name"],
            email=ud["email"],
            phone=ud["phone"],
            password_hash=pw_hash,
            role="user",
            is_active=True,
            created_at=datetime.utcnow() - timedelta(days=days_ago),
        )
        db.session.add(u)
        created_users.append(u)

    db.session.flush()
    print(f"[OK] {len(created_users)} users ready.")

    # Wishlists
    wish_count = 0
    for user in created_users:
        sample = random.sample(products, min(random.randint(2, 6), len(products)))
        for p in sample:
            if not Wishlist.query.filter_by(user_id=user.id, product_id=p.id).first():
                db.session.add(Wishlist(user_id=user.id, product_id=p.id))
                wish_count += 1
    db.session.flush()
    print(f"[OK] {wish_count} wishlist items added.")

    # Orders + reviews
    # Build coupon list for applying to some orders
    live_coupons = [code for (code, _, _, _, _, _, active, days) in COUPONS_DATA
                    if active and days != -1]

    order_count  = 0
    review_count = 0

    for user in created_users:
        for _ in range(random.randint(1, 4)):
            days_ago   = random.randint(0, 60)
            order_date = datetime.utcnow() - timedelta(days=days_ago)
            status     = random.choice(STATUSES)

            items_raw   = random.sample(products, min(random.randint(1, 3), len(products)))
            subtotal    = 0.0
            order_items = []
            for p in items_raw:
                qty   = random.randint(1, 2)
                price = float(p.sale_price_jod if p.is_on_sale and p.sale_price_jod else p.price_jod)
                subtotal += price * qty
                order_items.append((p, qty, price))

            # 30% chance to use a coupon
            coupon_code  = None
            discount_amt = 0.0
            if random.random() < 0.3 and live_coupons:
                coupon_code  = random.choice(live_coupons)
                # rough discount: 10% of subtotal
                discount_amt = round(subtotal * 0.10, 3)
                subtotal_after = max(0, subtotal - discount_amt)
            else:
                subtotal_after = subtotal

            delivery_fee = 0.0 if subtotal_after >= 30 else 3.0
            total        = round(subtotal_after + delivery_fee, 3)

            order = Order(
                user_id=user.id,
                status=status,
                subtotal_jod=round(subtotal, 3),
                discount_jod=discount_amt,
                delivery_fee_jod=delivery_fee,
                total_jod=total,
                coupon_code=coupon_code,
                payment_method="cash_on_delivery",
                full_name=user.full_name,
                phone=user.phone,
                city=random.choice(CITIES),
                area=random.choice(AREAS),
                address=f"Street {random.randint(1,50)}, Bldg {random.randint(1,20)}",
                created_at=order_date,
                updated_at=order_date,
            )
            db.session.add(order)
            db.session.flush()

            for p, qty, price in order_items:
                db.session.add(OrderItem(
                    order_id=order.id,
                    product_id=p.id,
                    quantity=qty,
                    unit_price_jod=price,
                ))
                p.sales_count = (p.sales_count or 0) + qty

            order_count += 1

            # Review (60% for delivered)
            if status == "delivered" and random.random() < 0.6:
                p, _, _ = order_items[0]
                if not Review.query.filter_by(user_id=user.id, product_id=p.id).first():
                    db.session.add(Review(
                        user_id=user.id,
                        product_id=p.id,
                        stars=random.choices([3, 4, 4, 5, 5, 5], k=1)[0],
                        comment=random.choice(COMMENTS),
                        is_approved=random.random() > 0.2,
                        created_at=order_date + timedelta(days=random.randint(2, 7)),
                    ))
                    review_count += 1

    db.session.commit()
    print(f"[OK] {order_count} orders created.")
    print(f"[OK] {review_count} reviews created.")


# ════════════════════════════════════════════════════════════════════════════
def run():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--all"

    with app.app_context():
        print(f"\n=== ORYA Seed Script (mode: {mode}) ===\n")

        if mode in ("--all", "--coupons-only"):
            print("-- Coupons --")
            seed_coupons()
            print("-- Discounts --")
            seed_discounts()

        if mode == "--all":
            print("-- Users / Wishlists / Orders --")
            seed_users_orders()

        print("\n[DONE] All done!\n")

        if mode in ("--all", "--coupons-only"):
            print("Active coupon codes (share with customers):")
            print("-" * 40)
            for (code, ctype, value, min_ord, _, _, active, days) in COUPONS_DATA:
                if active and days != -1:
                    val_str = f"{int(value)}%" if ctype == "percentage" else f"{value:.3f} JOD"
                    min_str = f"  (min order: {min_ord} JOD)" if min_ord > 0 else ""
                    print(f"  {code:12s} | {val_str:10s}{min_str}")
            print("-" * 40)

        if mode == "--all":
            print("\nUsers (all password: 1234):")
            for ud in USERS_DATA:
                print(f"   {ud['username']:15s} | {ud['full_name']}")


if __name__ == "__main__":
    run()
