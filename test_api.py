from fastapi.testclient import TestClient
from app import app
import json

client = TestClient(app)

def test_workflow():
    print("\n==========================================")
    print(" RUNNING API INTEGRATION TESTS")
    print("==========================================")
    
    # 1. Test Search Configs
    print("\n1. Testing GET /api/search-configs...")
    response = client.get("/api/search-configs")
    assert response.status_code == 200
    configs = response.json()
    print(f"   > Success! Found {len(configs)} search configs.")
    for c in configs:
        print(f"     - Sektör: {c['sector_name']}, Kelime Sayısı: {len(c['keywords'])}")
        
    # 2. Test Leads Listing
    print("\n2. Testing GET /api/leads...")
    response = client.get("/api/leads?limit=5")
    assert response.status_code == 200
    leads_data = response.json()
    print(f"   > Success! Found total {leads_data['total_count']} leads in database.")
    print(f"   > Showing top 3 leads with scores:")
    for lead in leads_data['leads'][:3]:
        print(f"     - {lead['company_name']} ({lead['sector']}) - Skor: {lead['score']}/100 [{lead['score_label']}]")
        
    # 3. Test Lead Details
    if leads_data['leads']:
        first_lead_id = leads_data['leads'][0]['id']
        print(f"\n3. Testing GET /api/leads/{first_lead_id}...")
        response = client.get(f"/api/leads/{first_lead_id}")
        assert response.status_code == 200
        lead_details = response.json()
        print(f"   > Success! Lead Details:")
        print(f"     - Firma: {lead_details['company_name']}")
        print(f"     - Email: {lead_details['email']}")
        print(f"     - Website: {lead_details['website']}")
        print(f"     - Skor Kırılımı: {lead_details['score_breakdown_json']}")
        print(f"     - Açıklama (Reason):\n{lead_details['score_reason']}")
        
    # 4. Test Manual Lead Creation (which recalculates score automatically)
    print("\n4. Testing POST /api/leads (Manual creation)...")
    manual_lead = {
        "company_name": "Test Klinik Psikoloji Merkezi",
        "sector": "Psikoloji",
        "city": "Sakarya",
        "district": "Serdivan",
        "website": "https://www.testklinikpsikoloji.com",
        "email": "info@testklinikpsikoloji.com",
        "phone": "0555 123 45 67",
        "description": "Klinik psikoloji, aile danışmanlığı, oyun terapisi ve ergen terapisi seansları.",
        "source_url": "https://manual-entry.com",
        "lead_status": "yeni",
        "notes": "Manuel test girdisi"
    }
    response = client.post("/api/leads", json=manual_lead)
    assert response.status_code == 200
    new_lead = response.json()
    print(f"   > Success! Manually created lead:")
    print(f"     - ID: {new_lead['id']}")
    print(f"     - Otomatik Skor: {new_lead['score']}/100")
    print(f"     - Durum Rozeti: {new_lead['score_label']}")
    print(f"     - Skor Açıklaması:\n{new_lead['score_reason']}")
    
    # 5. Test SMTP Settings
    print("\n5. Testing GET and POST /api/smtp-settings...")
    # Fetch first (should be empty if never set)
    response = client.get("/api/smtp-settings")
    assert response.status_code == 200
    print(f"   > SMTP Settings (Initial): {response.json()}")
    
    # Save SMTP settings
    smtp_payload = {
        "sender_email": "psikologsibelduran@gmail.com",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "password": "my_super_secret_app_password"
    }
    response = client.post("/api/smtp-settings", json=smtp_payload)
    assert response.status_code == 200
    saved_smtp = response.json()
    print(f"   > Success! SMTP settings saved: {saved_smtp['sender_email']} on {saved_smtp['smtp_host']}")
    
    # Verify we can fetch them now
    response = client.get("/api/smtp-settings")
    assert response.status_code == 200
    fetched_smtp = response.json()
    assert fetched_smtp is not None
    print(f"   > Verification successful! Fetched SMTP settings: {fetched_smtp['sender_email']}")
    
    # 6. Test Campaign Creation and Auto-recipients queue
    print("\n6. Testing POST /api/campaigns...")
    campaign_payload = {
        "name": "Psikoloji Kliniklerine Başvuru Kampanyası",
        "subject": "Psikolog Pozisyonu Başvurusu - Sibel Duran",
        "template_html": "Sayın {firma_adi} yetkilisi, staj ve iş başvurusu...",
        "attachment_path": "SIBEL_DURAN_CV.pdf",
        "delay_min": 15,
        "delay_max": 30
    }
    response = client.post("/api/campaigns", json=campaign_payload)
    assert response.status_code == 200
    campaign = response.json()
    print(f"   > Success! Campaign created:")
    print(f"     - ID: {campaign['id']}")
    print(f"     - İsim: {campaign['name']}")
    print(f"     - Konu: {campaign['subject']}")
    print(f"     - Alıcı (Recipient) Sayısı: {campaign['recipient_count']}")
    
    # Fetch campaign details with recipients
    print(f"\n7. Testing GET /api/campaigns/{campaign['id']}...")
    response = client.get(f"/api/campaigns/{campaign['id']}")
    assert response.status_code == 200
    camp_details = response.json()
    print(f"   > Success! Campaign Details:")
    print(f"     - Kampanya Durumu: {camp_details['campaign']['status']}")
    print(f"     - Toplam Alıcı: {camp_details['campaign']['recipient_count']}")
    print(f"     - İlk 3 Alıcı Kuyruğu:")
    for r in camp_details['recipients'][:3]:
        print(f"       * Firma ID: {r['lead_id']} | Email: {r['email']} | Durum: {r['status']}")
        
    # Clean up test campaign and manual lead
    print("\n8. Cleaning up test data...")
    # Delete campaign
    response = client.delete(f"/api/campaigns/{campaign['id']}")
    assert response.status_code == 204
    # Delete manual lead
    response = client.delete(f"/api/leads/{new_lead['id']}")
    assert response.status_code == 204
    print("   > Clean up successful! All tests passed!")
    print("\n==========================================")

if __name__ == "__main__":
    test_workflow()
