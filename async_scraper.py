import httpx
from bs4 import BeautifulSoup
import re
import asyncio
import random
import base64
from urllib.parse import urljoin, urlparse, parse_qs
from utils import extract_address_details, clean_text

class AsyncCompanyScraper:
    def __init__(self, blacklist=None, headers=None):
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.blacklist = blacklist or []
        
    async def search_company_url(self, company_name, city):
        """Searches for the company website url using search engine (limit 1)"""
        query = f"{company_name} {city} web sitesi"
        urls = await self.perform_search(query, limit=1)
        return urls[0] if urls else None

    async def discover_companies_by_query(self, sector_keyword, city, limit=15):
        """Discovers potential company links using search queries"""
        query = f"{city} {sector_keyword}"
        raw_urls = await self.perform_search(query, limit=limit)
        
        discovered = []
        for url in raw_urls:
            domain = urlparse(url).netloc
            if any(bl in domain for bl in self.blacklist):
                continue
                
            # basic name guess from domain
            name_guess = domain.replace('www.', '').split('.')[0].upper()
            
            discovered.append({
                'name': name_guess,
                'website': url,
                'city': city,
                'source_keyword': sector_keyword
            })
        return discovered

    async def perform_search(self, query, limit=5):
        """Tries Bing Search first (asynchronous), falls back to DuckDuckGo HTML"""
        found_links = []
        
        # --- BING SEARCH ---
        try:
            async with httpx.AsyncClient(headers=self.headers, verify=False, timeout=15.0) as client:
                resp = await client.get("https://www.bing.com/search", params={'q': query})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    results = []
                    for h2 in soup.find_all('h2'):
                        a = h2.find('a')
                        if a and a.get('href'):
                            results.append(a.get('href'))
                            
                    for raw_link in results:
                        link = raw_link
                        if '/ck/a?!' in raw_link:
                            try:
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
                            
                        if any(bl in link for bl in self.blacklist):
                            continue
                            
                        found_links.append(link)
                        if len(found_links) >= limit:
                            break
                            
                    if found_links:
                        return found_links
        except Exception as e:
            pass
            
        # --- DUCKDUCKGO FALLBACK ---
        await asyncio.sleep(random.uniform(2, 4))
        url = "https://html.duckduckgo.com/html/"
        params = {'q': query}
        
        try:
            custom_headers = self.headers.copy()
            custom_headers['Referer'] = 'https://html.duckduckgo.com/'
            async with httpx.AsyncClient(headers=custom_headers, verify=False, timeout=15.0) as client:
                resp = await client.get(url, params=params)
                soup = BeautifulSoup(resp.content, 'html.parser')
                results = soup.find_all('a', class_='result__a', limit=limit+5)
                
                for res in results:
                    link = res.get('href')
                    if not link or 'duckduckgo.com' in link:
                        continue
                        
                    if any(bl in link for bl in self.blacklist):
                        continue
                        
                    found_links.append(link)
                    if len(found_links) >= limit:
                        break
        except Exception as e:
            pass
            
        return found_links

    async def enrich_company_data(self, company_data):
        """Visits company website to extract emails, phones, description, hiring state, address"""
        website = company_data.get('website')
        
        if not website:
            found_url = await self.search_company_url(company_data['name'], company_data.get('city', ''))
            if found_url:
                company_data['website'] = found_url
                website = found_url
            else:
                return company_data
                
        try:
            if not website.startswith('http'):
                website = 'http://' + website
                
            async with httpx.AsyncClient(headers=self.headers, verify=False, timeout=15.0, follow_redirects=True) as client:
                response = await client.get(website)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 1. Emails
                emails = set(re.findall(r'[\w\.-]+@[\w\.-]+\.[\w]+', response.text))
                # Remove common garbage assets extensions like png/jpg matching email regex
                valid_emails = {e for e in emails if not e.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'))}
                company_data['email'] = ', '.join(valid_emails)
                
                # 2. Phones
                phones = set(re.findall(r'0\s?(\d{3})\s?(\d{3})\s?(\d{2})\s?(\d{2})', response.text))
                company_data['phone'] = ', '.join([f"0{p[0]} {p[1]} {p[2]} {p[3]}" for p in phones])
                
                # 3. Description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    company_data['summary'] = meta_desc.get('content', '').strip()
                else:
                    p_text = soup.find('p')
                    if p_text:
                        company_data['summary'] = p_text.get_text(strip=True)[:200]
                        
                # 4. Address Details
                address_text = ""
                footer = soup.find('footer')
                if footer:
                    address_text += footer.get_text(" ", strip=True)
                    
                contact_link = soup.find('a', href=re.compile(r'iletisim|contact', re.I))
                if contact_link:
                    contact_url = urljoin(website, contact_link['href'])
                    try:
                        contact_resp = await client.get(contact_url, timeout=10.0)
                        address_text += " " + BeautifulSoup(contact_resp.content, 'html.parser').get_text(" ", strip=True)
                    except:
                        pass
                        
                loc = extract_address_details(address_text, company_data.get('city'))
                company_data.update(loc)
                
                # 5. Career/Hiring Status
                is_hiring = "Belirsiz / Bilgi Yok"
                career_link = soup.find('a', href=re.compile(r'kariyer|insan-kaynaklari|is-basvurusu|ik|open-positions|careers', re.I))
                page_text_lower = response.text.lower()
                
                if career_link or any(kw in page_text_lower for kw in ['açık pozisyon', 'iş ilanı', 'iş başvuru form', 'aramıza katıl']):
                    is_hiring = "Muhtemelen Alım Yapıyor (Kariyer/Açık Pozisyon İzi Var)"
                elif any(kw in page_text_lower for kw in ['insan kaynakları', 'kariyer', 'iş fırsatları']):
                    is_hiring = "İK Sayfası Var (Alım Olabilir)"
                    
                company_data['alim_yapma_durumu'] = is_hiring
                
        except Exception as e:
            company_data['error'] = str(e)
            
        return company_data
