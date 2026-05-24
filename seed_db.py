import os
import json
import pandas as pd
from db import init_db, SessionLocal, SearchConfig, Lead
from search_config import SECTOR_CONFIG, BLACKLIST_DOMAINS
from utils import calculate_lead_score

def seed_database():
    print("Veritabanı ilklendiriliyor ve tohumlanıyor (Seeding)...")
    
    # 1. Initialize Tables
    init_db()
    
    db = SessionLocal()
    try:
        # 2. Seed Search Configs
        print("\n--- Arama Konfigürasyonları Ekleniyor ---")
        for sector_name, config in SECTOR_CONFIG.items():
            existing = db.query(SearchConfig).filter(SearchConfig.sector_name == sector_name).first()
            if not existing:
                sc = SearchConfig(
                    sector_name=sector_name,
                    keywords=json.dumps(config['keywords']),
                    cities=json.dumps(config['cities']),
                    districts=json.dumps([]), # Will be selected dynamically later
                    search_limit=15,
                    delay_min=15,
                    delay_max=30,
                    blacklist_domains=json.dumps(BLACKLIST_DOMAINS)
                )
                db.add(sc)
                print(f"> Sektör konfigürasyonu eklendi: {sector_name}")
            else:
                print(f"> Sektör konfigürasyonu zaten var: {sector_name}")
        db.commit()
        
        # 3. Import Leads from Excel Files
        print("\n--- Mevcut Excel Dosyalarından Firmalar Aktarılıyor ---")
        # Look for excel files in the workspace (parent directory) and current directory
        workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        excel_files = []
        for d in [workspace_dir, current_dir]:
            for f in os.listdir(d):
                if f.endswith(".xlsx") and not f.startswith("~$") and "Marmara" not in f:
                    excel_files.append(os.path.join(d, f))
                    
        # Filter duplicates in path
        excel_files = list(set(excel_files))
        
        total_imported = 0
        
        for file_path in excel_files:
            file_name = os.path.basename(file_path)
            print(f"\nDosya okunuyor: {file_name}")
            try:
                df = pd.read_excel(file_path)
                
                # Check required columns
                if 'name' not in df.columns:
                    print(f"! Hata: {file_name} dosyasında 'name' kolonu bulunamadı, atlanıyor.")
                    continue
                    
                for idx, row in df.iterrows():
                    name = str(row.get('name', '')).strip()
                    if not name or name == "nan" or name == "Belirsiz / Bilgi Yok":
                        continue
                        
                    website = str(row.get('website', '')).strip()
                    if website == "nan" or website == "Belirsiz / Bilgi Yok":
                        website = ""
                        
                    email = str(row.get('email', '')).strip()
                    if email == "nan" or email == "Belirsiz / Bilgi Yok":
                        email = ""
                        
                    phone = str(row.get('phone', '')).strip()
                    if phone == "nan" or phone == "Belirsiz / Bilgi Yok":
                        phone = ""
                        
                    summary = str(row.get('summary', '')).strip()
                    if summary == "nan" or summary == "Belirsiz / Bilgi Yok":
                        summary = ""
                        
                    alim_durumu = str(row.get('alim_yapma_durumu', '')).strip()
                    if alim_durumu == "nan" or alim_durumu == "Belirsiz / Bilgi Yok":
                        alim_durumu = "Belirsiz / Bilgi Yok"
                        
                    city = str(row.get('city', 'Unknown')).strip()
                    district = str(row.get('district', 'Unknown')).strip()
                    sector = str(row.get('sector', 'Bilinmeyen Sektör')).strip()
                    
                    if city == "nan": city = "Unknown"
                    if district == "nan": district = "Unknown"
                    if sector == "nan": sector = "Bilinmeyen Sektör"
                    
                    # Deduplicate in DB
                    existing_lead = None
                    if website:
                        existing_lead = db.query(Lead).filter(Lead.website == website).first()
                    if not existing_lead:
                        existing_lead = db.query(Lead).filter(Lead.company_name == name, Lead.city == city).first()
                        
                    if existing_lead:
                        # Update fields but don't duplicate
                        existing_lead.email = email or existing_lead.email
                        existing_lead.phone = phone or existing_lead.phone
                        existing_lead.description = summary or existing_lead.description
                        existing_lead.sector = sector or existing_lead.sector
                        existing_lead.lead_status = "yeni" # Default reset
                        
                        # Recalculate score
                        lead_dict = {
                            'website': existing_lead.website,
                            'email': existing_lead.email,
                            'phone': existing_lead.phone,
                            'description': existing_lead.description,
                            'district': existing_lead.district,
                            'alim_yapma_durumu': alim_durumu,
                            'sector': existing_lead.sector
                        }
                        score_details = calculate_lead_score(lead_dict)
                        existing_lead.score = score_details['score']
                        existing_lead.score_label = score_details['score_label']
                        existing_lead.score_breakdown_json = score_details['score_breakdown_json']
                        existing_lead.score_reason = score_details['score_reason']
                        
                        print(f"  [GÜNCELLENDİ] {name} - Skor: {existing_lead.score} - Durum: {existing_lead.score_label}")
                    else:
                        # Calculate lead score
                        lead_dict = {
                            'website': website,
                            'email': email,
                            'phone': phone,
                            'description': summary,
                            'district': district,
                            'alim_yapma_durumu': alim_durumu,
                            'sector': sector
                        }
                        score_details = calculate_lead_score(lead_dict)
                        
                        new_lead = Lead(
                            company_name=name,
                            sector=sector,
                            city=city,
                            district=district,
                            website=website or None,
                            email=email or None,
                            phone=phone or None,
                            description=summary or None,
                            source_url=None,
                            score=score_details['score'],
                            score_label=score_details['score_label'],
                            score_breakdown_json=score_details['score_breakdown_json'],
                            score_reason=score_details['score_reason'],
                            lead_status="yeni",
                            notes=None
                        )
                        db.add(new_lead)
                        total_imported += 1
                        print(f"  [EKLENDİ] {name} - Skor: {score_details['score']} - Durum: {score_details['score_label']}")
                        
                db.commit()
            except Exception as e:
                print(f"! {file_name} dosyasından aktarım sırasında hata: {e}")
                
        print(f"\nTohumlama (Seeding) tamamlandı! Toplam {total_imported} yeni firma eklendi.")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
