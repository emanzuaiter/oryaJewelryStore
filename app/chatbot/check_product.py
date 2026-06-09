import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app
from app.models import Product

app = create_app()
with app.app_context():
    p = Product.query.filter(Product.name_ar.ilike('%زمرد%')).first()
    if p:
        print(f"Price: {p.price_jod}")
        print(f"Is On Sale: {p.is_on_sale}")
        print(f"Sale Price: {p.sale_price_jod}")
    else:
        print("Product not found")
