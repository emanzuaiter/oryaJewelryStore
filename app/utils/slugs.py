import re
import unicodedata

def slugify(text):
    """
    Convert a string to a URL-friendly slug.
    Handles Arabic and English characters.
    """
    if not text:
        return ""
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace non-alphanumeric characters with hyphens
    # We keep Arabic characters
    text = re.sub(r'[^\w\s-]', '', text)
    
    # Replace whitespace with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    
    # Remove multiple hyphens
    text = re.sub(r'-+', '-', text).strip('-')
    
    return text
