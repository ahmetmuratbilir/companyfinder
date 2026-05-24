# Bu dosya, botun sektör bazlı arama yaparken kullanacağı sorguları ve şehirleri tanımlar.
# AI tarafından optimize edilmiş sorgularla orta ölçekli firmalar keşfedilir.

SECTOR_CONFIG = {
    'Psikoloji': {
        'keywords': [
            'Psikolojik Danışmanlık Merkezi',
            'Aile Danışma Merkezi',
            'Çocuk ve Ergen Psikoloji',
            'Oyun Terapisi Merkezi',
            'Özel Anaokulu Kreş',
            'Huzurevi Yaşlı Bakımevi'
        ],
        'cities': ['SAKARYA SERDIVAN', 'ISTANBUL AVRUPA']
    },
    'Insan_Kaynaklari': {
        'keywords': [
            'İnsan Kaynakları Danışmanlık',
            'İşe Alım Şirketi'
        ],
        'cities': ['SAKARYA SERDIVAN', 'ISTANBUL AVRUPA']
    }
}

# Sonuçlardaki gereksiz ("directory") siteleri elemek için
BLACKLIST_DOMAINS = [
    'kariyer.net', 'sahibinden.com', 'trendyol.com', 'facebook.com', 
    'instagram.com', 'youtube.com', 'wikipedia.org', 'yellowpages', 
    'rehber', 'firmaekle', 'bulurum.com', 'armut.com', 'doktortakvimi.com',
    'linkedin.com', 'twitter.com', 'eniyihekim.com', 'doktorsitesi.com',
    'tavsiyedefteri.com', 'haritapark', 'yandex.com', 'google.com',
    'gelisim.edu.tr', 'uskudar.edu.tr', 'aydin.edu.tr', 'bilgi.edu.tr',
    
    # Seyahat, Turizm ve Blog Siteleri
    'enuygun.com', 'turna.com', 'etstur.com', 'gezimanya.com', 'blog.obilet',
    'tripadvisor', 'neredekal', 'tatil', 'bilet', 'gezilmesigerekenyerler',
    'oggusto.com', 'visitistanbul', 'istanbul.com', 'anadolugazetesi', 
    'haber', 'gazete', 'kulturportali', 'zhihu.com',
    
    # Kamu ve Eğitim Siteleri (İşe alım yapmayacak veya genel bilgi siteleri)
    'gov.tr', 'bel.tr', 'edu.tr', 'org.tr', 'meb.k12.tr'
]
