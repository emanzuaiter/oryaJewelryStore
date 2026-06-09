from app import create_app, db
from app.models import User, Product, Order, OrderItem
from werkzeug.security import generate_password_hash
from flask_bcrypt import Bcrypt
import random

app = create_app()
bcrypt = Bcrypt(app)

def seed():
    with app.app_context():
        # db.drop_all() # Optional, but let's not drop to be safe, just add if not exists
        db.create_all()

        # 1. Add Users
        admin_user = User.query.filter_by(email='admin@orya.com').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                full_name='Admin User',
                email='admin@orya.com',
                phone='1234567890',
                password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                role='admin'
            )
            db.session.add(admin_user)
            print("Admin user created.")

        regular_user = User.query.filter_by(email='user@orya.com').first()
        if not regular_user:
            regular_user = User(
                username='johndoe',
                full_name='John Doe',
                email='user@orya.com',
                phone='0987654321',
                password_hash=bcrypt.generate_password_hash('user123').decode('utf-8'),
                role='user'
            )
            db.session.add(regular_user)
            print("Regular user created.")

        db.session.commit()

        # 2. Add Dummy Products
        products_data = [
            # Necklaces
            {"name_ar": "عقد ألماس ماجستيك", "name_en": "Majestic Diamond Necklace", "category": "necklaces", "price": 1250.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "سلسلة ذهب كلاسيكية", "name_en": "Classic Gold Chain", "category": "necklaces", "price": 350.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "قلادة لؤلؤ المياه العذبة", "name_en": "Freshwater Pearl Pendant", "category": "necklaces", "price": 180.000, "material": "silver", "img": "images/products/placeholder.jpg"},
            {"name_ar": "عقد حجر الزمرد", "name_en": "Emerald Stone Necklace", "category": "necklaces", "price": 850.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            
            # Earrings
            {"name_ar": "أقراط ألماس متدلية", "name_en": "Diamond Drop Earrings", "category": "earrings", "price": 650.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "أقراط ذهب دائرية", "name_en": "Gold Hoop Earrings", "category": "earrings", "price": 220.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "أقراط فضة مرصعة", "name_en": "Studded Silver Earrings", "category": "earrings", "price": 95.000, "material": "silver", "img": "images/products/placeholder.jpg"},
            {"name_ar": "أقراط لؤلؤ كلاسيكية", "name_en": "Classic Pearl Studs", "category": "earrings", "price": 150.000, "material": "gold-plated", "img": "images/products/placeholder.jpg"},

            # Bracelets
            {"name_ar": "سوار تنس ألماسي", "name_en": "Diamond Tennis Bracelet", "category": "bracelets", "price": 1500.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "سوار ذهب وردي صلب", "name_en": "Solid Rose Gold Bangle", "category": "bracelets", "price": 480.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "سوار فضة سحر", "name_en": "Silver Charm Bracelet", "category": "bracelets", "price": 120.000, "material": "silver", "img": "images/products/placeholder.jpg"},

            # Rings
            {"name_ar": "خاتم خطوبة سوليتير", "name_en": "Solitaire Engagement Ring", "category": "rings", "price": 2100.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "خاتم ذهب مرصع بالياقوت", "name_en": "Sapphire Gold Ring", "category": "rings", "price": 750.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "خاتم فضة ناعم", "name_en": "Delicate Silver Ring", "category": "rings", "price": 60.000, "material": "silver", "img": "images/products/placeholder.jpg"},
            {"name_ar": "خاتم زفاف كلاسيكي", "name_en": "Classic Wedding Band", "category": "rings", "price": 320.000, "material": "gold", "img": "images/products/placeholder.jpg"},

            # Belly Rings
            {"name_ar": "بيرسينج بطن كريستال", "name_en": "Crystal Belly Ring", "category": "belly-rings", "price": 45.000, "material": "silver", "img": "images/products/placeholder.jpg"},
            {"name_ar": "بيرسينج بطن ذهبي", "name_en": "Gold Teardrop Belly Ring", "category": "belly-rings", "price": 85.000, "material": "gold", "img": "images/products/placeholder.jpg"},

            # Anklets
            {"name_ar": "خلخال ذهب ناعم", "name_en": "Fine Gold Anklet", "category": "anklets", "price": 190.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "خلخال فضة بقلوب", "name_en": "Silver Hearts Anklet", "category": "anklets", "price": 55.000, "material": "silver", "img": "images/products/placeholder.jpg"},

            # Sets
            {"name_ar": "طقم زفاف ألماس كامل", "name_en": "Complete Diamond Bridal Set", "category": "sets", "price": 4500.000, "material": "gold", "img": "images/products/placeholder.jpg"},
            {"name_ar": "طقم لؤلؤ كلاسيكي", "name_en": "Classic Pearl Set", "category": "sets", "price": 650.000, "material": "gold-plated", "img": "images/products/placeholder.jpg"},
        ]
        
        # Only add if they don't exist to prevent duplicates if run multiple times
        existing_names = [p.name_en for p in Product.query.all()]
        added = 0
        for p_data in products_data:
            if p_data["name_en"] not in existing_names:
                p = Product(
                    name_ar=p_data["name_ar"],
                    name_en=p_data["name_en"],
                    category=p_data["category"],
                    price_jod=p_data["price"],
                    material=p_data["material"],
                    stock_qty=random.randint(2, 25),
                    is_visible=True
                )
                db.session.add(p)
                added += 1
                
        if added > 0:
            db.session.commit()
            print(f"Added {added} new dummy products.")
        else:
            print("No new products added (already exist).")

        # 3. Add Dummy Orders for regular user
        if regular_user and not regular_user.orders:
            p1 = Product.query.first()
            if p1:
                order = Order(
                    user_id=regular_user.id,
                    status='delivered',
                    subtotal_jod=p1.price_jod,
                    total_jod=p1.price_jod + 5,
                    delivery_fee_jod=5,
                    full_name=regular_user.full_name,
                    phone=regular_user.phone,
                    city='Amman',
                    area='Abdoun',
                    address='Street 123, Building 4'
                )
                db.session.add(order)
                db.session.commit()

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=p1.id,
                    quantity=1,
                    unit_price_jod=p1.price_jod
                )
                db.session.add(order_item)
                db.session.commit()
                print("Dummy order created.")

        print("Database seeding completed.")

if __name__ == '__main__':
    seed()
