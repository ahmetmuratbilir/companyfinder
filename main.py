from scraper import CompanyScraper
from search_config import SECTOR_CONFIG
import pandas as pd
import time
import os

def main():
    print("Starting Multi-Sector Search Bot (Industry & Psychology)...")
    scraper = CompanyScraper()
    
    # Dictionary to hold dataframes for each sector
    all_sector_data = {}

    for sector_name, config in SECTOR_CONFIG.items():
        print(f"\n==========================================")
        print(f" PROCESSING SECTOR: {sector_name}")
        print(f"==========================================")
        
        sector_companies = []
        
        # 1. Discover Companies via Search Queries
        for city in config['cities']:
            for keyword in config['keywords']:
                # Example: "Sakarya Döküm Sanayi"
                discovered = scraper.discover_companies_by_query(keyword, city)
                sector_companies.extend(discovered)
                
                # Small delay between queries to be safe
                time.sleep(1)
        
        # Remove duplicates based on website domain
        unique_companies = {c['website']: c for c in sector_companies}.values()
        print(f"\n> Found {len(unique_companies)} unique potential companies for {sector_name}.")
        
        # 2. Enrich Data (Visit websites)
        enriched_data = []
        print(f"> Enriching data for {sector_name}...")
        for i, company in enumerate(unique_companies):
            print(f"  [{i+1}/{len(unique_companies)}] Visiting {company['name']} ({company['website']})...")
            details = scraper.enrich_company_data(company)
            details['sector'] = sector_name # Add sector tag
            enriched_data.append(details)
            time.sleep(1)
            
        if enriched_data:
            df = pd.DataFrame(enriched_data)
            
            # Standard columns
            cols = ['name', 'sector', 'city', 'district', 'semt', 'phone', 'email', 'website', 'summary', 'source_keyword', 'alim_yapma_durumu']
            for c in cols:
                if c not in df.columns: df[c] = "Belirsiz / Bilgi Yok"
            
            # Save EACH sector to its own file
            file_name_clean = sector_name.replace(" ", "_").replace("/", "-")
            output_file = f"{file_name_clean}_Firmalari.xlsx"
            
            df[cols].to_excel(output_file, index=False)
            print(f"> Saved data for {sector_name} to {output_file}")
            
        else:
            print(f"Warning: No data found for {sector_name}")

    print("\nALL SECTORS PROCESSED!")

if __name__ == "__main__":
    main()
