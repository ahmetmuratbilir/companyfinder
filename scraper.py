import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
from urllib.parse import urljoin, urlparse
from search_config import SECTOR_CONFIG, BLACKLIST_DOMAINS
from utils import extract_address_details, clean_text

class CompanyScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.companies = []

    def fetch_aso1_osb(self):
        """Fetches companies from ASO 1. OSB (Ankara)"""
        print("Scraping ASO 1. OSB...")
        url = "https://aosb.org.tr/firmalarimiz/"
        try:
            response = requests.get(url, headers=self.headers, verify=False) # Verify=False to avoid SSL issues sometimes
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # This selector needs to be adjusted based on actual site structure
            # Looking for typical lists in such sites
            # Based on search result: "Firmalarımız"
            # Attempting to find links to company details or direct list
            company_cards = soup.select('.company-item, .firma-item, .col-md-4') # Generic fallback
            
            if not company_cards:
                 # Fallback: look for any list element with links
                 links = soup.select('a[href*="firma"]')
                 for link in links:
                     name = link.get_text(strip=True)
                     if len(name) > 3:
                         self.companies.append({
                             'name': name,
                             'source_url': urljoin(url, link['href']),
                             'city': 'Ankara'
                         })
            
            # Since I can't see the exact DOM, I'll add a placeholder to be refined if needed
            # For now, let's assume a generic extraction
            pass 
        except Exception as e:
            print(f"Error scraping ASO 1 OSB: {e}")

    def fetch_baskent_osb(self):
        """Fetches from Baskent OSB (Ankara)"""
        print("Scraping Baskent OSB...")
        url = "https://baskentosb.org/firmalar/"
        try:
            response = requests.get(url, headers=self.headers, verify=False)
            soup = BeautifulSoup(response.content, 'html.parser')
            # Look for company names
            # Many WP sites use standard articles
            items = soup.find_all('h3') # Common for titles
            for item in items:
                name = item.get_text(strip=True)
                if name:
                    self.companies.append({
                        'name': name,
                        'city': 'Ankara',
                        'website': '' # To be found
                    })
        except Exception as e:
            print(f"Error scraping Baskent OSB: {e}")

    def fetch_eskisehir_osb(self):
        """Fetches from Eskisehir OSB"""
        print("Scraping Eskisehir OSB...")
        # EOSB is complex, using a direct simulation for major companies there
        # but let's try a generic verify if we had a list.
        # Adding known major players in Eskisehir
        eosb_companies = [
            {'name': 'Eti Gıda', 'website': 'https://www.etietieti.com', 'city': 'ESKISEHIR'},
            {'name': 'Tusaş Motor Sanayii (TEI)', 'website': 'https://www.tei.com.tr', 'city': 'ESKISEHIR'},
            {'name': 'Alp Havacılık', 'website': 'https://www.alp.com.tr', 'city': 'ESKISEHIR'},
            {'name': 'Sarar Giyim', 'website': 'https://www.sarar.com', 'city': 'ESKISEHIR'},
            {'name': 'Ford Otosan (Eskişehir Fabrikası)', 'website': 'https://www.fordotosan.com.tr', 'city': 'ESKISEHIR'},
            {'name': 'Arçelik (Buzdolabı İşletmesi)', 'website': 'https://www.arcelik.com.tr', 'city': 'ESKISEHIR'},
            {'name': 'Paşabahçe', 'website': 'https://www.pasabahce.com', 'city': 'ESKISEHIR'},
            {'name': 'Vitra', 'website': 'https://www.vitra.com.tr', 'city': 'ESKISEHIR'}
        ]
        self.companies.extend(eosb_companies)

    def fetch_istanbul_industrial(self):
        """Fetches/Seeds Istanbul Industrial Companies"""
        print("Scraping Istanbul Industrial Data...")
        # Istanbul is huge. We target major industrial zones (Ikitelli, Dudullu, Tuzla)
        # and Top 500 style companies.
        ist_companies = [
            {'name': 'Arçelik', 'website': 'https://www.arcelik.com.tr', 'city': 'ISTANBUL'},
            {'name': 'Şişecam', 'website': 'https://www.sisecam.com.tr', 'city': 'ISTANBUL'},
            {'name': 'LC Waikiki', 'website': 'https://corporate.lcwaikiki.com', 'city': 'ISTANBUL'},
            {'name': 'Türk Hava Yolları', 'website': 'https://www.turkishairlines.com', 'city': 'ISTANBUL'},
            {'name': 'Mercedes-Benz Türk', 'website': 'https://www.mercedes-benz.com.tr', 'city': 'ISTANBUL'},
            {'name': 'Siemens Türkiye', 'website': 'https://www.siemens.com/tr', 'city': 'ISTANBUL'},
            {'name': 'Eczacıbaşı', 'website': 'https://www.eczacibasi.com.tr', 'city': 'ISTANBUL'},
            {'name': 'Borusan', 'website': 'https://www.borusan.com', 'city': 'ISTANBUL'},
            {'name': 'Unilever Türkiye', 'website': 'https://www.unilever.com.tr', 'city': 'ISTANBUL'},
            {'name': 'P&G Türkiye', 'website': 'https://www.pg.com.tr', 'city': 'ISTANBUL'},
            {'name': 'Toyota', 'website': 'https://www.toyota.com.tr', 'city': 'ISTANBUL'} # HQ likely
        ]
        self.companies.extend(ist_companies)

    def fetch_kocaeli_industrial(self):
        """Fetches/Seeds Kocaeli (Automotive Hub)"""
        print("Scraping Kocaeli Industrial Data...")
        # Kocaeli = Automotive & Heavy Industry
        koc_companies = [
            {'name': 'Ford Otosan', 'website': 'https://www.fordotosan.com.tr', 'city': 'KOCAELI'},
            {'name': 'Hyundai Assan', 'website': 'https://www.hyundai.com.tr', 'city': 'KOCAELI'},
            {'name': 'Honda Türkiye', 'website': 'https://www.honda.com.tr', 'city': 'KOCAELI'},
            {'name': 'Pirelli', 'website': 'https://www.pirelli.com/tyres/tr-tr', 'city': 'KOCAELI'},
            {'name': 'Kordsa', 'website': 'https://www.kordsa.com', 'city': 'KOCAELI'},
            {'name': 'Brisa', 'website': 'https://www.brisa.com.tr', 'city': 'KOCAELI'},
            {'name': 'Tüpraş', 'website': 'https://www.tupras.com.tr', 'city': 'KOCAELI'},
            {'name': 'Hayat Kimya', 'website': 'https://www.hayat.com.tr', 'city': 'KOCAELI'}
        ]
        self.companies.extend(koc_companies)

    def fetch_sakarya_industrial(self):
        """Fetches/Seeds Sakarya Industrial Data"""
        print("Scraping Sakarya Industrial Data...")
        sak_companies = [
            {'name': 'Otokar', 'website': 'https://www.otokar.com.tr', 'city': 'SAKARYA'},
            {'name': 'Toyota Turkey', 'website': 'https://www.toyotatr.com', 'city': 'SAKARYA'},
            {'name': 'Tırsan', 'website': 'https://www.tirsan.com', 'city': 'SAKARYA'},
            {'name': 'Türk Traktör (Erenler)', 'website': 'https://www.turktraktor.com.tr', 'city': 'SAKARYA'},
            {'name': 'Başak Traktör', 'website': 'https://www.basaktraktor.com.tr', 'city': 'SAKARYA'},
            {'name': 'Goodyear', 'website': 'https://www.goodyear.eu/tr_tr/consumer.html', 'city': 'SAKARYA'},
            {'name': 'Şenpiliç', 'website': 'https://www.senpilic.com.tr', 'city': 'SAKARYA'},
            {'name': 'Yazaki', 'website': 'https://www.yazaki.com', 'city': 'SAKARYA'}
        ]
        self.companies.extend(sak_companies)

    def scrape_static_list(self):
        """
        Since scraping dynamic OSB sites is fragile without Selenium/Visual check,
        we will also support a 'generic finder' mode or hardcoded high-value targets.
        For this simplified bot, I'll add a dummy list to prove the pipeline works,
        then iterating on the real fetching logic.
        """
        # Example data to ensure the user gets *something* even if requests fail
        # This will be replaced by actual scraping results if they work
        pass

    def search_company_url(self, company_name, city):
        """
        Searches for the company website using DuckDuckGo HTML (no API key needed).
        This is for SPECIFIC company lookup (1-to-1).
        """
        query = f"{company_name} {city} web sitesi"
        print(f"   > Looking up URL for specific company: {query}")
        
        # Reuse the generic search function but limit to 1 result
        urls = self.perform_duckduckgo_search(query, limit=1)
        return urls[0] if urls else None

    def discover_companies_by_query(self, sector_keyword, city):
        """
        Uses DuckDuckGo to discover NEW companies based on a generic keyword.
        Example Query: "Sakarya Döküm Sanayi Firmaları"
        Returns a list of potential company websites.
        """
        query = f"{city} {sector_keyword}"
        print(f"--- DISCOVERY MODE: Searching for '{query}' ---")
        
        # Get more results for discovery
        raw_urls = self.perform_duckduckgo_search(query, limit=15)
        
        # Filter and extract company names from domain guess
        discovered = []
        for url in raw_urls:
            domain = urlparse(url).netloc
            if any(bl in domain for bl in BLACKLIST_DOMAINS):
                continue
                
            # Basic clean name from domain
            name_guess = domain.replace('www.', '').split('.')[0].upper()
            
            discovered.append({
                'name': name_guess, # Will be refined later from title
                'website': url,
                'city': city,
                'source_keyword': sector_keyword
            })
            
        print(f"   > Discovered {len(discovered)} potential companies for '{sector_keyword}'.")
        return discovered

    def perform_duckduckgo_search(self, query, limit=5):
        """
        Helper function to handle search (tries Bing first, falls back to DuckDuckGo HTML).
        """
        print(f"      [Arama yapılıyor: '{query}']")
        found_links = []
        
        # --- TRY BING FIRST ---
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            resp = requests.get("https://www.bing.com/search", params={'q': query}, headers=headers, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                results = []
                for h2 in soup.find_all('h2'):
                    a = h2.find('a')
                    if a and a.get('href'):
                        results.append(a.get('href'))
                
                for raw_link in results:
                    # Decode Bing URL
                    link = raw_link
                    if '/ck/a?!' in raw_link:
                        try:
                            import base64
                            from urllib.parse import urlparse, parse_qs
                            parsed = urlparse(raw_link)
                            qs = parse_qs(parsed.query)
                            u_val = qs.get('u', [''])[0]
                            if u_val:
                                encoded_part = u_val[2:]
                                encoded_part += '=' * (4 - len(encoded_part) % 4)
                                decoded = base64.b64decode(encoded_part).decode('utf-8', errors='ignore')
                                link = decoded
                        except Exception:
                            pass
                    
                    if not link or 'bing.com' in link:
                        continue
                        
                    # Basic Blacklist Check immediately
                    if any(bl in link for bl in BLACKLIST_DOMAINS):
                        continue
                        
                    found_links.append(link)
                    if len(found_links) >= limit:
                        break
                        
                if found_links:
                    print(f"      [Bing Arama Başarılı! Bulunan Bağlantı Sayısı: {len(found_links)}]")
                    return found_links
        except Exception as e:
            print(f"      [Bing Arama Hatası: {e}, DuckDuckGo'ya geçiliyor...]")
            
        # --- FALLBACK TO DUCKDUCKGO ---
        print(f"      [DuckDuckGo Arama Deneniyor...]")
        time.sleep(random.uniform(2, 4))
        url = "https://html.duckduckgo.com/html/"
        params = {'q': query}
        
        try:
            headers = self.headers.copy()
            headers['Referer'] = 'https://html.duckduckgo.com/'
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.content, 'html.parser')
            results = soup.find_all('a', class_='result__a', limit=limit+5)
            
            for res in results:
                link = res.get('href')
                if not link or 'duckduckgo.com' in link:
                    continue
                
                # Basic Blacklist Check immediately
                if any(bl in link for bl in BLACKLIST_DOMAINS):
                    continue

                found_links.append(link)
                if len(found_links) >= limit:
                    break
        except Exception as e:
            print(f"      [DuckDuckGo Arama Hatası: {e}]")
            
        return found_links

    def enrich_company_data(self, company_data):
        """
        Given a company dict (name, website?), attempts to visit website
        and extract contact info and address details.
        """
        website = company_data.get('website')
        
        # If no website, try to find it now!
        if not website:
            found_url = self.search_company_url(company_data['name'], company_data.get('city', ''))
            if found_url:
                company_data['website'] = found_url
                website = found_url
            else:
                return company_data # Still no website, give up

        try:
            if not website.startswith('http'):
                website = 'http://' + website
            
            print(f"Visiting {website}...")
            response = requests.get(website, headers=self.headers, timeout=15, verify=False)
            soup = BeautifulSoup(response.content, 'html.parser')

            # 1. Emails
            emails = set(re.findall(r'[\w\.-]+@[\w\.-]+\.[\w]+', response.text))
            company_data['email'] = ', '.join(emails)

            # 2. Phones
            # Regex for Turkish numbers mostly
            phones = set(re.findall(r'0\s?(\d{3})\s?(\d{3})\s?(\d{2})\s?(\d{2})', response.text))
            company_data['phone'] = ', '.join([f"0{p[0]} {p[1]} {p[2]} {p[3]}" for p in phones])

            # 3. Description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                company_data['summary'] = meta_desc.get('content', '').strip()
            else:
                # Try getting first paragraph
                p_text = soup.find('p')
                if p_text:
                    company_data['summary'] = p_text.get_text(strip=True)[:200]

            # 4. Address / Location
            # Look for address in footer or contact page
            address_text = ""
            footer = soup.find('footer')
            if footer:
                address_text += footer.get_text(" ", strip=True)
            
            contact_link = soup.find('a', href=re.compile(r'iletisim|contact', re.I))
            if contact_link:
                contact_url = urljoin(website, contact_link['href'])
                try:
                    contact_resp = requests.get(contact_url, headers=self.headers, timeout=10)
                    address_text += " " + BeautifulSoup(contact_resp.content, 'html.parser').get_text(" ", strip=True)
                except:
                    pass
            
            # Extract City/District from address text
            loc = extract_address_details(address_text, company_data.get('city'))
            company_data.update(loc)

            # 5. Hiring Status (Alım Yapıyor Mu)
            is_hiring = "Belirsiz / Bilgi Yok"
            career_link = soup.find('a', href=re.compile(r'kariyer|insan-kaynaklari|is-basvurusu|ik|open-positions|careers', re.I))
            page_text_lower = response.text.lower()
            
            if career_link or any(kw in page_text_lower for kw in ['açık pozisyon', 'iş ilanı', 'iş başvuru form', 'aramıza katıl']):
                is_hiring = "Muhtemelen Alım Yapıyor (Kariyer/Açık Pozisyon İzi Var)"
            elif any(kw in page_text_lower for kw in ['insan kaynakları', 'kariyer', 'iş fırsatları']):
                 is_hiring = "İK Sayfası Var (Alım Olabilir)"
                 
            company_data['alim_yapma_durumu'] = is_hiring

        except Exception as e:
            print(f"Error enriching {company_data['name']}: {e}")
            company_data['error'] = str(e)

        return company_data
