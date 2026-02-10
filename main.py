import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# --- ČÁST 1: ZÍSKÁNÍ ODKAZŮ NA KRAJE ---

main_url = "https://www.volby.cz/pls/ps2017nss/ps3?xjazyk=CZ"
base_url = "https://www.volby.cz/pls/ps2017nss/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

try:
    print(f"Stahuji hlavní stránku: {main_url}")
    response = requests.get(main_url, headers=headers)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"Chyba při stahování stránky: {e}")
    exit()

soup = BeautifulSoup(response.content, 'html.parser')

# Najdeme všechny buňky s odkazy na kraje (mají specifické hlavičky)
region_links = []
# Najdeme všechny tabulky, které obsahují výsledky (pro jistotu, kdyby jich bylo více)
tables = soup.find_all('table', {'class': 'table'})
print(f"Nalezeno {len(tables)} tabulek na hlavní stránce.")

for table in tables:
    # Hledáme všechny buňky 'td' s atributem 'headers' obsahujícím 'sa1'
    region_cells = table.find_all('td', headers=lambda h: h and 'sa1' in h)
    for cell in region_cells:
        link_tag = cell.find('a')
        if link_tag and link_tag.has_attr('href'):
            region_name = link_tag.get_text(strip=True)
            relative_link = link_tag['href']
            full_link = base_url + relative_link
            region_links.append({'kraj': region_name, 'odkaz': full_link})

print("\n--- Nalezené odkazy na kraje ---")
for region in region_links:
    print(f"{region['kraj']}: {region['odkaz']}")

if not region_links:
    print("\nNepodařilo se najít žádné odkazy na kraje. Struktura stránky se možná změnila.")
    exit()

# --- ČÁST 2: PARSOVÁNÍ DAT PRO KONKRÉTNÍ KRAJ (PRAHA) ---

# Vezmeme první odkaz (Praha) jako příklad
prague_url = region_links[0]['odkaz']

print(f"\nStahuji data pro kraj Praha: {prague_url}")
# Přidáme malou pauzu, abychom nezahlcovali server
time.sleep(1)

try:
    response = requests.get(prague_url, headers=headers)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"Chyba při stahování stránky kraje: {e}")
    exit()

soup_prague = BeautifulSoup(response.content, 'html.parser')

# Najdeme všechny tabulky s obcemi/městskými částmi
city_tables = soup_prague.find_all('table', class_='table')

if not city_tables:
    print("Nebyly nalezeny žádné tabulky s obcemi.")
    exit()

# Zpracujeme data z tabulek
results_data = []
print("\n--- Výsledky pro Prahu ---")
for table in city_tables:
    # Hledáme řádky, které obsahují data o obci (přeskakujeme hlavičky)
    rows = table.find_all('tr')
    for row in rows:
        # Data o obci jsou v buňkách 'td'
        cells = row.find_all('td')
        # Řádek s daty má typicky více než 3 buňky
        if len(cells) > 3:
            city_name = cells[1].get_text(strip=True)
            voters = cells[3].get_text(strip=True).replace('\xa0', '') # Počet voličů a odstranění nezlomitelné mezery
            
            # Kontrola, zda je údaj o voličích platné číslo
            if voters.isdigit():
                results_data.append({
                    'Městská část': city_name,
                    'Voliči v seznamu': int(voters)
                })
                print(f"Městská část: {city_name}, Voliči v seznamu: {voters}")

# --- ČÁST 3: ULOŽENÍ DO CSV ---

if results_data:
    df = pd.DataFrame(results_data)
    df.to_csv('vysledky_praha.csv', index=False)
    print("\nData byla úspěšně uložena do souboru 'vysledky_praha.csv'")
else:
    print("\nNepodařilo se extrahovat žádná data o městských částech.")
