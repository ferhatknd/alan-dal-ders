#!/usr/bin/env python3
"""
Server.py dosyasındaki bozuk string literallerini düzelt
"""

import re

# server.py dosyasını oku
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Bozuk pattern'leri düzelt
patterns = [
    # Kesik string'leri düzelt
    (r"yield f\"data: \{json\.dumps\(.*?\)\}\n\n\"\n", lambda m: m.group(0).replace('\n\n"\n', '\n\n')),
    
    # Eksik kapanış parantezlerini ekle
    (r"yield f\"data: \{json\.dumps\(.*?\)\}\n\n\n", lambda m: m.group(0).replace('\n\n\n', '}\n\n')),
]

# Pattern'leri uygula
for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Manuel düzeltmeler
fixes = [
    ("yield f\"data: {json.dumps({'type': 'error', 'message': 'Veritabanı bulunamadı veya oluşturulamadı'})}\n\n\"\n                return",
     "yield f\"data: {json.dumps({'type': 'error', 'message': 'Veritabanı bulunamadı veya oluşturulamadı'})}\n\n\"\n                return"),
    
    # Tüm bozuk yield statement'leri düzelt
    ("})}\n\n\"\n", "})}\n\n\""),
    ("})}\n\n\"", "})\n\n\""),
    ("}\n\n\"", "})}\n\n\""),
]

for old, new in fixes:
    content = content.replace(old, new)

# Manuel çözüm: Tüm yield satırlarını tek tek düzelt
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'yield f"data:' in line and line.strip().endswith('})}'):
        # Bu satırdan sonraki boş satırları kontrol et
        if i + 1 < len(lines) and lines[i + 1].strip() == '':
            if i + 2 < len(lines) and lines[i + 2].strip() == '"':
                # Bozuk pattern bulundu, düzelt
                lines[i] = line + '\n\n'
                lines[i + 1] = ''
                lines[i + 2] = ''

# Dosyayı kaydet
with open('server.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("✅ Server.py düzeltildi")