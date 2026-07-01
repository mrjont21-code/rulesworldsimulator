"""
Skills: SPA JSON extraction
Mổ bụng thẻ JSON của Next.js hoặc Nuxt.js
"""
import json
import re
from bs4 import BeautifulSoup


def _extract_long_texts(obj):
    """Đệ quy extract text dài từ JSON object"""
    texts = []
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            # Skip non-content keys
            skip_keys = [
                'imageurl', 'thumbnail', 'videoid', 'author', 'url', 
                'href', 'link', 'id', 'src', 'icon', 'avatar', 'logo', 
                'srcset', 'alt', 'classname', 'type', 'style', 'class',
                'datetime', 'date', 'time', 'timestamp', 'format'
            ]
            if k.lower() in skip_keys:
                continue
            texts.extend(_extract_long_texts(v))
            
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(_extract_long_texts(item))
            
    elif isinstance(obj, str):
        # Chỉ lấy text dài, có dấu câu (có vẻ là nội dung)
        if len(obj) > 120 and not obj.startswith("http"):
            if "<" not in obj and ">" not in obj:  # Không phải HTML
                if any(c in obj for c in [".", ",", ";", ":", "!", "?"]):
                    texts.append(obj)
    
    return texts


def extract_spa_json_data(html_text: str) -> str | None:
    """
    Mổ bụng thẻ JSON của Next.js hoặc Nuxt.js
    Trả về text content hoặc None
    """
    try:
        soup = BeautifulSoup(html_text, 'lxml')
        
        # Tìm Next.js __NEXT_DATA__
        data_script = soup.find('script', id='__NEXT_DATA__')
        
        # Hoặc Nuxt.js __NUXT__
        if not data_script:
            data_script = soup.find('script', id='__NUXT__')
        
        if not data_script:
            return None
            
        json_data = json.loads(data_script.string)
        
        # Extract long texts
        extracted_texts = _extract_long_texts(json_data)
        
        if not extracted_texts:
            return None
        
        # Join và clean
        raw_text = "\n\n".join(extracted_texts)
        clean_text = re.sub(r'\s{2,}', ' ', re.sub(r'\n+', '\n', raw_text)).strip()
        
        return clean_text if len(clean_text) > 200 else None
        
    except Exception:
        return None
