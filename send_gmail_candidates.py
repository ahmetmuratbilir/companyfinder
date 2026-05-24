import os
import sys
import time
import random
import pandas as pd
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_gmail(sender_email, password, to_email, subject, body, attachment_path):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Attach body in UTF-8
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # Attach CV
    filename = os.path.basename(attachment_path)
    with open(attachment_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= "{filename}"')
        msg.attach(part)
        
    # Connect and send
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, to_email, msg.as_string())
    server.quit()

def main():
    print("Gmail CV Gönderim Botu Başlatılıyor...")
    
    # 1. Excel dosyasını bul
    excel_path = '../Psikoloji_Firmalari.xlsx'
    if not os.path.exists(excel_path):
        excel_path = 'Psikoloji_Firmalari.xlsx'
        if not os.path.exists(excel_path):
            print("[HATA] Psikoloji_Firmalari.xlsx dosyası bulunamadı!")
            return

    # 2. CV dosyasını bul
    cv_filename = 'SIBEL_DURAN_CV.pdf'
    possible_paths = [
        cv_filename,
        os.path.join('..', cv_filename),
        os.path.join('C:\\Users\\ahmet murat bilir\\Downloads', cv_filename)
    ]
    
    cv_path = None
    for p in possible_paths:
        if os.path.exists(p):
            cv_path = p
            break
            
    if not cv_path:
        print(f"\n[HATA] '{cv_filename}' dosyası ne proje klasöründe ne de İndirilenler (Downloads) klasöründe bulunamadı!")
        print("Lütfen CV dosyasını 'firma bulma botu' klasörünün içine kopyalayıp yapıştırın.\n")
        return
        
    cv_abs_path = os.path.abspath(cv_path)
    print(f"CV Bulundu: {cv_abs_path}")

    # 3. Şirket maillerini yükle
    df = pd.read_excel(excel_path)
    df = df[df['email'] != 'Belirsiz / Bilgi Yok']
    
    # Benzersiz e-posta adreslerini topla
    email_list = []
    for idx, row in df.iterrows():
        parts = [e.strip() for e in str(row['email']).split(',')]
        for email_addr in parts:
            if email_addr and re.match(r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,4}$', email_addr):
                email_list.append((row['name'], email_addr))
                
    # Mükerrer e-postaları ele
    seen = set()
    unique_emails = []
    for name, email in email_list:
        if email not in seen:
            seen.add(email)
            unique_emails.append((name, email))

    print(f"Toplam gönderim yapılacak benzersiz alıcı sayısı: {len(unique_emails)}")
    if len(unique_emails) == 0:
        print("[HATA] Gönderilecek e-posta adresi bulunamadı!")
        return

    # 4. Giriş Bilgileri
    sender_email = "psikologsibelduran@gmail.com"
    passwords_to_try = ["100768.Ss ", "100768.Ss"] # Try both with and without trailing space
    
    email_body = """Merhaba,

Ben Psikolog Sibel Duran. Çocuk, ergen ve aile alanlarında çalışmaya ilgi duymakta; bu doğrultuda aile danışmanlığı, oyun terapisi, çocuk değerlendirme testleri, çocuk ve ergenlerde BDT ile MMPI uygulayıcı eğitimlerini almış bulunmaktayım. Klinik staj sürecimde çocuklarla görüşme ve gözlem çalışmalarında aktif olarak yer aldım.

Kurumunuzun psikolojik danışmanlık, oyun terapisi, aile danışmanlığı birimlerinde oluşabilecek uygun pozisyonlarda değerlendirilmek üzere özgeçmişimi bilgilerinize sunarım.

Değerlendirmeniz halinde memnuniyet duyarım.

İyi çalışmalar dilerim."""

    # 5. Giriş test et
    authenticated_pass = None
    for pwd in passwords_to_try:
        try:
            print(f"Gmail girişi test ediliyor (Şifre: '{pwd}')...")
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, pwd)
            server.quit()
            authenticated_pass = pwd
            print("Giriş BAŞARILI!")
            break
        except Exception as e:
            print(f"Giriş başarısız: {e}")

    if not authenticated_pass:
        print("\n[HATA] Gmail girişi başarısız oldu!")
        print("Bunun iki olası nedeni vardır:")
        print("1. Şifre yanlış olabilir.")
        print("2. Google, hesabın güvenliği için doğrudan şifreyle girişi engellemiş olabilir (Bu çok yaygındır).")
        print("\nÇÖZÜM: Sibel Duran'ın Google hesabına giriş yapıp (myaccount.google.com) 'Güvenlik' sekmesinden '2 Adımlı Doğrulama'yı açmalı ve ardından en alttaki 'Uygulama Şifreleri' (App Passwords) kısmından mail gönderme botu için 16 haneli özel bir şifre üretip buraya yazmalıyız.\n")
        return

    # 6. Sırayla gönderim yap
    print("\nGönderim başlıyor. Spam koruması için her mail arasına 15-30 saniye rastgele gecikme eklendi.\n")
    
    for i, (name, to_email) in enumerate(unique_emails):
        print(f"[{i+1}/{len(unique_emails)}] Gönderiliyor: {name} -> {to_email}...")
        try:
            send_gmail(sender_email, authenticated_pass, to_email, "Psikolog Özgeçmiş Başvurusu - Sibel Duran", email_body, cv_abs_path)
            print(f"✓ Başarıyla gönderildi!")
        except Exception as e:
            print(f"✗ HATA (Gönderilemedi): {e}")
            
        # Delay except for the last mail
        if i < len(unique_emails) - 1:
            delay = random.uniform(15, 30)
            print(f"Bekleniyor: {delay:.2f} saniye...")
            time.sleep(delay)
            
    print("\nTüm gönderimler tamamlandı!")

if __name__ == "__main__":
    main()
