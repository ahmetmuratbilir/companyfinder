import re

# List of districts for major cities to help parsing (simplified)
DISTRICTS = {
    'SAKARYA': ['Adapazarı', 'Serdivan', 'Erenler', 'Arifiye', 'Sapanca', 'Hendek', 'Akyazı', 'Geyve', 'Pamukova', 'Karasu', 'Kocaali', 'Kaynarca', 'Ferizli', 'Söğütlü', 'Karapürçek', 'Taraklı'],
    'ANKARA': ['Çankaya', 'Keçiören', 'Yenimahalle', 'Mamak', 'Etimesgut', 'Sincan', 'Altındağ', 'Pursaklar', 'Gölbaşı', 'Polatlı', 'Çubuk', 'Kahramankazan', 'Beypazarı', 'Elmadağ', 'Nallıhan', 'Haymana', 'Kızılcahamam', 'Bala', 'Kalecik', 'Ayaş', 'Güdül', 'Çamlıdere', 'Evren'],
    'ISTANBUL': ['Esenyurt', 'Küçükçekmece', 'Bağcılar', 'Ümraniye', 'Pendik', 'Bahçelievler', 'Üsküdar', 'Sultangazi', 'Gaziosmanpaşa', 'Maltepe', 'Kartal', 'Esenler', 'Kadıköy', 'Kağıthane', 'Avcılar', 'Ataşehir', 'Fatih', 'Eyüpsultan', 'Sancaktepe', 'Başakşehir', 'Sarıyer', 'Sultanbeyli', 'Güngören', 'Zeytinburnu', 'Şişli', 'Bayrampaşa', 'Beykoz', 'Beylikdüzü', 'Arnavutköy', 'Tuzla', 'Çekmeköy', 'Büyükçekmece', 'Beyoğlu', 'Bakırköy', 'Silivri', 'Beşiktaş', 'Çatalca', 'Şile', 'Adalar'],
    'KOCAELI': ['Gebze', 'İzmit', 'Darıca', 'Körfez', 'Gölcük', 'Derince', 'Çayırova', 'Kartepe', 'Başiskele', 'Karamürsel', 'Kandıra', 'Dilovası'],
    'BURSA': ['Osmangazi', 'Yıldırım', 'Nilüfer', 'İnegöl', 'Gemlik', 'Mustafakemalpaşa', 'Mudanya', 'Gürsu', 'Karacabey', 'Orhangazi', 'Kestel', 'Yenişehir', 'İznik', 'Orhaneli', 'Keles', 'Büyükorhan', 'Harmancık'],
    'ESKISEHIR': ['Odunpazarı', 'Tepebaşı', 'Sivrihisar', 'Çifteler', 'Seyitgazi', 'Alpu', 'Mihalıççık', 'Mahmudiye', 'Beylikova', 'İnönü', 'Günyüzü', 'Han', 'Mihalgazi', 'Sarıcakaya'],
    'BOLU': ['Merkez', 'Gerede', 'Mudurnu', 'Göynük', 'Mengen', 'Yeniçağa', 'Dörtdivan', 'Seben', 'Kıbrıscık']
}

def extract_address_details(text, default_city=None):
    """
    Parses a text blob (entire page text or footer) to find:
    - City
    - District
    - Neighborhood (Semt)
    """
    text = text.upper().replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
    
    found_city = default_city.upper() if default_city else None
    found_district = None
    found_semt = None # Neighborhood detection is harder without a full DB, usually implied by "Mahallesi"

    # Detect City if not provided or to confirm
    for city in DISTRICTS.keys():
        if city in text:
            found_city = city
            break
            
    # Detect District
    if found_city and found_city in DISTRICTS:
        for dist in DISTRICTS[found_city]:
            dist_upper = dist.upper().replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
            if dist_upper in text:
                found_district = dist
                break
    
    # Simple Neighborhood extraction (looks for X Mahallesi)
    # Using regex to find word before "MAHALLESI"
    mahalle_match = re.search(r'([A-Z0-9\s]+)\s+MAHALLESI', text)
    if mahalle_match:
        # Take the last word or two before "Mahallesi"
        raw_mah = mahalle_match.group(1).strip().split()
        if raw_mah:
            found_semt = raw_mah[-1] # Simplistic, likely just the name
            if len(raw_mah) > 1 and len(raw_mah[-1]) < 3: # If last part is short (e.g. 1. Mah), take more
                 found_semt = " ".join(raw_mah[-2:])
    
    return {
        'city': found_city.title() if found_city else 'Unknown',
        'district': found_district if found_district else 'Unknown',
        'semt': found_semt.title() if found_semt else '',
        'full_address_hint': text[:500] # Debugging helper (truncated)
    }

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

import json

def calculate_lead_score(lead_dict, target_keywords=None):
    """
    Calculates lead quality score (0-100), breakdown, label, and explanation reason.
    lead_dict should contain:
      - website: str
      - email: str
      - phone: str
      - description/summary: str or description: str
      - district: str
      - alim_yapma_durumu: str
      - sector: str
    """
    breakdown = {}
    reason_lines = []
    
    # 1. Web Aktifliği (10 points)
    website = lead_dict.get('website') or ""
    has_website = bool(website and website not in ["Belirsiz / Bilgi Yok", ""])
    has_scraping_error = bool(lead_dict.get('error'))
    
    if has_website and not has_scraping_error:
        breakdown['web_active'] = 10
        reason_lines.append("+ Web sitesi aktif: 10/10")
    else:
        breakdown['web_active'] = 0
        reason_lines.append("- Web sitesi aktif değil veya hata alındı: 0/10")
        
    # 2. Sektör Uyumu (25 points)
    sector_points = 5
    desc = (lead_dict.get('description') or lead_dict.get('summary') or "").lower()
    name = (lead_dict.get('company_name') or lead_dict.get('name') or "").lower()
    source_kw = (lead_dict.get('source_keyword') or "").lower()
    
    if not target_keywords:
        sec_name = (lead_dict.get('sector') or "").lower()
        if "psikoloji" in sec_name or "klinik" in sec_name:
            target_keywords = ['psikolog', 'psikolojik', 'terapi', 'danismanlik', 'klinik', 'oyun', 'danışmanlık', 'aile', 'ergen', 'çocuk', 'seans']
        elif "insan kaynaklari" in sec_name or "ik" in sec_name or "hr" in sec_name or "insan kaynakları" in sec_name:
            target_keywords = ['insan kaynaklari', 'insan kaynakları', 'kariyer', 'danismanlik', 'danışmanlık', 'istihdam', 'secme', 'yerlestirme', 'seçme', 'yerleştirme']
        else:
            target_keywords = []
            
    matches = 0
    if target_keywords:
        combined_text = f"{name} {desc} {source_kw}"
        for kw in target_keywords:
            if kw.lower() in combined_text:
                matches += 1
                
    if matches >= 3:
        sector_points = 25
        reason_lines.append(f"+ Sektör uyumu yüksek ({matches} eşleşme): 25/25")
    elif matches >= 1:
        sector_points = 15
        reason_lines.append(f"+ Sektör uyumu orta ({matches} eşleşme): 15/25")
    else:
        sector_points = 5
        reason_lines.append("- Sektör uyumu düşük (eşleşme yok): 5/25")
        
    breakdown['sector_match'] = sector_points

    # 3. Lokasyon Uyumu (15 points)
    dist = lead_dict.get('district') or ""
    has_location = bool(dist and dist not in ["Unknown", "Belirsiz", "Bilgi Yok", ""])
    if has_location:
        breakdown['location_match'] = 15
        reason_lines.append(f"+ Lokasyon belirlendi ({dist}): 15/15")
    else:
        breakdown['location_match'] = 0
        reason_lines.append("- Lokasyon belirlenemedi: 0/15")

    # 4. E-posta Varlığı (20 points)
    email = lead_dict.get('email') or ""
    has_email = bool(email and email not in ["Belirsiz / Bilgi Yok", ""])
    if has_email:
        breakdown['email_presence'] = 20
        reason_lines.append("+ E-posta adresi bulundu: 20/20")
    else:
        breakdown['email_presence'] = 0
        reason_lines.append("- E-posta adresi bulunamadı: 0/20")

    # 5. Telefon Varlığı (10 points)
    phone = lead_dict.get('phone') or ""
    has_phone = bool(phone and phone not in ["Belirsiz / Bilgi Yok", ""])
    if has_phone:
        breakdown['phone_presence'] = 10
        reason_lines.append("+ Telefon numarası bulundu: 10/10")
    else:
        breakdown['phone_presence'] = 0
        reason_lines.append("- Telefon numarası bulunamadı: 0/10")

    # 6. Kariyer / İletişim Sayfası (10 points)
    alim = (lead_dict.get('alim_yapma_durumu') or "").lower()
    has_career = any(kw in alim for kw in ['alim', 'alıy', 'kariyer', 'ik', 'sayfası'])
    if has_career:
        breakdown['career_page'] = 10
        reason_lines.append("+ Kariyer / İK sayfası bulundu: 10/10")
    else:
        breakdown['career_page'] = 0
        reason_lines.append("- Kariyer sayfası bulunamadı: 0/10")

    # 7. Açıklama Uygunluğu (10 points)
    has_desc = len(desc.strip()) > 10
    if has_desc:
        breakdown['description_presence'] = 10
        reason_lines.append("+ Web sitesi açıklaması mevcut: 10/10")
    else:
        breakdown['description_presence'] = 0
        reason_lines.append("- Açıklama veya özet bulunamadı: 0/10")

    # Calculate Total Score
    total_score = sum(breakdown.values())
    
    # Labeling
    if total_score >= 80:
        score_label = "Güçlü Uyum"
    elif total_score >= 60:
        score_label = "Orta Uyum"
    elif total_score >= 40:
        score_label = "Zayıf Uyum"
    else:
        score_label = "Düşük Kalite"
        
    # Rule-based Recommendation
    if not has_website or has_scraping_error:
        recommendation = "Düşük öncelik (Web sitesi aktif değil)"
    elif total_score >= 80 and has_email:
        recommendation = "Mail kampanyasına ekle"
    elif total_score >= 60 and has_phone:
        recommendation = "Manuel kontrol önerilir"
    elif not has_email and has_phone:
        recommendation = "Telefonla ulaşılması önerilir"
    elif total_score < 40:
        recommendation = "Kampanyaya ekleme"
    else:
        recommendation = "Manuel kontrol önerilir"
        
    # Reason Summary Formatting
    full_reason = f"Genel Skor: {total_score}/100 ({score_label})\n\n" + "\n".join(reason_lines) + f"\n\nÖneri: {recommendation}"
    
    return {
        'score': total_score,
        'score_label': score_label,
        'score_breakdown_json': json.dumps(breakdown),
        'score_reason': full_reason,
        'recommendation': recommendation
    }
