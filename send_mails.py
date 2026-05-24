import os
import sys
import pandas as pd
import re

# 1. Ensure pywin32 is installed for Outlook automation
try:
    import win32com.client
except ImportError:
    print("Installing pywin32 package for Outlook automation...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])
    import win32com.client

def main():
    excel_path = '../Psikoloji_Firmalari.xlsx'
    if not os.path.exists(excel_path):
        excel_path = 'Psikoloji_Firmalari.xlsx'
        if not os.path.exists(excel_path):
            print("Error: Excel file not found!")
            return

    cv_filename = 'SİBEL DURAN CV.pdf'
    # Check current directory and parent directory for the CV
    cv_path = cv_filename
    if not os.path.exists(cv_path):
        cv_path = os.path.join('..', cv_filename)
        if not os.path.exists(cv_path):
            print(f"\n[HATA] '{cv_filename}' dosyası proje klasöründe bulunamadı!")
            print("Lütfen CV dosyanızı indirilenler klasöründen kopyalayıp 'firma bulma botu' klasörünün içine yapıştırın ve bu komutu tekrar çalıştırın.\n")
            return
            
    cv_abs_path = os.path.abspath(cv_path)
    print(f"CV bulundu: {cv_abs_path}")

    # Load Excel
    df = pd.read_excel(excel_path)
    print(f"Toplam psikoloji firma sayısı: {len(df)}")

    # Filter out companies with no emails
    df = df[df['email'] != 'Belirsiz / Bilgi Yok']

    # Filter out English/International firms just in case
    exclude_keywords = ['egonzehnder', 'stantonchase', 'amrop', 'isg.com', 'randstad']
    
    filtered_companies = []
    for idx, row in df.iterrows():
        name = str(row['name']).lower()
        website = str(row['website']).lower()
        
        is_exclude = False
        for kw in exclude_keywords:
            if kw in name or kw in website:
                is_exclude = True
                break
                
        if not is_exclude:
            filtered_companies.append(row)

    print(f"İngilizce/Uluslararası firmalar elendi. Gönderim yapılacak firma sayısı: {len(filtered_companies)}")

    email_body = """Merhaba,

Ben Psikolog Sibel Duran. Çocuk, ergen ve aile alanlarında çalışmaya ilgi duymakta; bu doğrultuda aile danışmanlığı, oyun terapisi, çocuk değerlendirme testleri, çocuk ve ergenlerde BDT ile MMPI uygulayıcı eğitimlerini almış bulunmaktayım. Klinik staj sürecimde çocuklarla görüşme ve gözlem çalışmalarında aktif olarak yer aldım.

Kurumunuzun psikolojik danışmanlık, oyun terapisi, aile danışmanlığı birimlerinde oluşabilecek uygun pozisyonlarda değerlendirilmek üzere özgeçmişimi bilgilerinize sunarım.

Değerlendirmeniz halinde memnuniyet duyarım.

İyi çalışmalar dilerim."""

    # 3. Try to automate Outlook
    outlook_available = False
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        outlook_available = True
    except Exception as e:
        print("\n[UYARI] Outlook uygulaması bilgisayarınızda kurulu veya yapılandırılmış bulunamadı.")
        print("Mailler otomatik gönderilemiyor. Ancak gönderilecek mail adreslerini aşağıda listeledim:\n")

    if outlook_available:
        print("\nOutlook bağlantısı başarılı. Mailler gönderilmeye başlanıyor...\n")
        for company in filtered_companies:
            emails = [e.strip() for e in str(company['email']).split(',')]
            for email_addr in emails:
                if not email_addr:
                    continue
                try:
                    mail = outlook.CreateItem(0)
                    mail.To = email_addr
                    mail.Subject = "Psikolog Özgeçmiş Başvurusu - Sibel Duran"
                    mail.Body = email_body
                    mail.Attachments.Add(cv_abs_path)
                    mail.Send()
                    print(f"✓ Başarıyla gönderildi: {company['name']} -> {email_addr}")
                except Exception as ex:
                    print(f"✗ HATA (Gönderilemedi): {company['name']} -> {email_addr}. Hata: {ex}")
        print("\nTüm mailler gönderildi!")
    else:
        # Display the list of emails for manual sending
        print("=== E-POSTA ADRESLERİ LİSTESİ (Kopyalayıp kendiniz gönderebilirsiniz) ===")
        for company in filtered_companies:
            print(f"- {company['name']}: {company['email']} ({company['website']})")
        print("=========================================================================")

if __name__ == "__main__":
    main()
