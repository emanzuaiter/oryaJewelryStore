from app.models import SiteSetting
from datetime import datetime

def get_delivery_fee(subtotal, items_data=None):
    """
    Calculate the delivery fee dynamically based on subtotal, total item count,
    specific item categories in the cart, and active free shipping rules in site settings.
    """
    try:
        # 1. Fetch free shipping rule
        rule_setting = SiteSetting.query.filter_by(key='free_delivery_rule').first()
        rule = rule_setting.value_en.strip().lower() if rule_setting and rule_setting.value_en else 'disabled'
        
        is_free = False
        
        if rule == 'always':
            is_free = True
            
        elif rule == 'min_amount':
            amount_setting = SiteSetting.query.filter_by(key='free_delivery_min_amount').first()
            if amount_setting and amount_setting.value_en:
                min_amount = float(amount_setting.value_en)
                if min_amount > 0 and subtotal >= min_amount:
                    is_free = True
                    
        elif rule == 'min_quantity':
            qty_setting = SiteSetting.query.filter_by(key='free_delivery_min_quantity').first()
            min_qty = int(qty_setting.value_en) if qty_setting and qty_setting.value_en else 2
            
            # Sum total quantity in cart
            total_items = 0
            if items_data:
                for item in items_data:
                    if isinstance(item, dict):
                        qty = int(item.get('quantity', 1))
                    else:
                        qty = int(getattr(item, 'quantity', 1))
                    total_items += qty
                    
            if min_qty > 0 and total_items >= min_qty:
                is_free = True
                
        elif rule == 'date_range':
            start_setting = SiteSetting.query.filter_by(key='free_delivery_start_date').first()
            end_setting = SiteSetting.query.filter_by(key='free_delivery_end_date').first()
            if start_setting and end_setting and start_setting.value_en and end_setting.value_en:
                start_date = start_setting.value_en.strip()
                end_date = end_setting.value_en.strip()
                today_str = datetime.now().strftime('%Y-%m-%d')
                if start_date <= today_str <= end_date:
                    is_free = True
                    
        elif rule == 'category':
            cat_setting = SiteSetting.query.filter_by(key='free_delivery_category').first()
            target_category = cat_setting.value_en.strip().lower() if cat_setting and cat_setting.value_en else ''
            
            if target_category and items_data:
                from app.models import Product
                for item in items_data:
                    if isinstance(item, dict):
                        pid = item.get('product_id') or item.get('id')
                    else:
                        pid = getattr(item, 'product_id', None) or getattr(item, 'id', None)
                        
                    if pid:
                        p = Product.query.get(pid)
                        if p and p.category and p.category.strip().lower() == target_category:
                            is_free = True
                            break
                            
        if is_free:
            return 0.0
            
    except Exception as e:
        print(f"[Delivery Fee Calc Error] {e}")

    # Fallback to default delivery fee JOD
    try:
        fee_setting = SiteSetting.query.filter_by(key='delivery_fee_jod').first()
        if fee_setting and fee_setting.value_en:
            return float(fee_setting.value_en)
    except Exception as e:
        print(f"[Delivery Fee Fetch Default Error] {e}")

    return 3.0  # Fallback to standard 3.0 JOD
