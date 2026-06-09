from sqlalchemy import func, or_
from app.models import Product

def normalize_arabic(text):
    if not text: return ""
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه")
    text = text.replace("ى", "ي")
    text = text.replace("ؤ", "ء").replace("ئ", "ء")
    return text

def get_base_english(text):
    t = text.lower()
    if t.endswith('ies'): return t[:-3] + 'y'
    if t.endswith('es'): return t[:-2]
    if t.endswith('s') and not t.endswith('ss'): return t[:-1]
    return t

SYNONYM_GROUPS = [
    {'سلسلة', 'سنسال', 'عقد', 'قلادة', 'سلسله', 'سناسل', 'عقود', 'necklace', 'pendant', 'chain', 'choker', 'necklaces'},
    {'سوار', 'سوارة', 'اسورة', 'اساور', 'سواره', 'سوارات', 'bracelet', 'bangle', 'cuff', 'anklet', 'wristlet', 'bracelets'},
    {'خاتم', 'محبس', 'دبلة', 'خواتم', 'دبله', 'ring', 'band', 'rings'},
    {'اقراط', 'حلق', 'تراكي', 'أقراط', 'earrings', 'earring', 'studs', 'hoops', 'drops'}
]

def norm_sql(col):
    # Nested replaces for SQLite to handle normalization in DB
    return func.replace(func.replace(func.replace(func.replace(func.replace(
        col, 'أ', 'ا'), 'إ', 'ا'), 'آ', 'ا'), 'ة', 'ه'), 'ى', 'ي')

def get_search_query(q):
    if not q:
        return Product.query.filter(False)
    
    q_norm = normalize_arabic(q)
    q_lower = q.lower()
    q_base = get_base_english(q)
    
    # Expand query with synonyms
    search_terms = {q, q_norm, q_lower, q_base}
    for group in SYNONYM_GROUPS:
        if any(m.lower() == q_lower or get_base_english(m) == q_base for m in group) or \
           q_norm in [normalize_arabic(m) for m in group]:
            search_terms.update(group)
            for m in group:
                search_terms.add(normalize_arabic(m))
                search_terms.add(m.lower())
                search_terms.add(get_base_english(m))
    
    conditions = []
    for term in search_terms:
        if not term: continue
        pattern = f'%{term}%'
        conditions.append(Product.name_ar.ilike(pattern))
        conditions.append(Product.name_en.ilike(pattern))
        conditions.append(norm_sql(Product.name_ar).ilike(pattern))
        conditions.append(Product.description_ar.ilike(pattern))
        conditions.append(Product.description_en.ilike(pattern))
        conditions.append(norm_sql(Product.description_ar).ilike(pattern))
        conditions.append(Product.category.ilike(pattern))
        conditions.append(Product.material.ilike(pattern))
        conditions.append(Product.stone.ilike(pattern))
    
    query = Product.query.filter(
        Product.is_visible == True,
        or_(*conditions)
    ).distinct()

    # DEBUG LOGGING
    print(f"DEBUG: Search Terms for '{q}': {search_terms}")
    # print(f"DEBUG: Search Query for '{q}': {query}")
    
    return query
