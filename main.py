import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd

def validate_arguments():
    """Ověří, zda uživatel zadal správný počet argumentů."""
    if len(sys.argv) != 3:
        print("Chyba: Nesprávný počet argumentů.")
        print("Použití: python main.py <URL_ADRESA> <VYSTUPNI_SOUBOR>")
        print('Příklad: python main.py "https://www.volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=2&xnumnuts=2103" "vysledky.csv"')
        sys.exit(1)
    
    url = sys.argv[1]
    if "https://www.volby.cz/pls/ps2017nss/" not in url:
        print("Chyba: Neplatný odkaz. Zadejte prosím korektní URL z webu volby.cz.")
        sys.exit(1)

def get_soup(url):
    header = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=header)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Chyba při stahování dat: {e}")
        return None

def scrape_data(url, output_file):
    soup = get_soup(url)
    if not soup: return

    print(f"STAHUJI DATA Z VYBRANÉHO URL: {url}")
    
    # Najdeme odkazy na obce v tabulkách
    links = []
    tables = soup.find_all("table", class_="table")
    for table in tables:
        rows = table.find_all("tr")[2:]
        for row in rows:
            tds = row.find_all("td")
            if len(tds) > 2 and tds[0].find("a"):
                links.append("https://www.volby.cz/pls/ps2017nss/" + tds[0].find("a")["href"])

    all_data = []
    
    for i, link in enumerate(links):
        city_soup = get_soup(link)
        if not city_soup: continue
        
        # Jméno obce
        city_name = city_soup.find_all("h3")[1].text.split(":")[-1].strip()
        print(f"Zpracovávám: {city_name}")
        
        # Základní statistiky
        summary_table = city_soup.find("table", id="ps311_t1")
        voters = summary_table.find_all("td")[3].text.replace('\xa0', '')
        envelopes = summary_table.find_all("td")[4].text.replace('\xa0', '')
        valid = summary_table.find_all("td")[7].text.replace('\xa0', '')

        row_data = {
            "code": link.split("xobec=")[1].split("&")[0],
            "location": city_name,
            "registered": voters,
            "envelopes": envelopes,
            "valid": valid
        }

        # Výsledky stran
        party_tables = city_soup.find_all("table", class_="table")[1:]
        for p_table in party_tables:
            p_rows = p_table.find_all("tr")[2:]
            for p_row in p_rows:
                p_tds = p_row.find_all("td")
                if len(p_tds) > 2 and p_tds[1].text != "-":
                    party_name = p_tds[1].text
                    votes = p_tds[2].text.replace('\xa0', '')
                    row_data[party_name] = votes
        
        all_data.append(row_data)

    # Uložení do CSV
    df = pd.DataFrame(all_data).fillna(0)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"HOTOVO. SOUBOR ULOŽEN: {output_file}")

if __name__ == "__main__":
    validate_arguments()
    scrape_data(sys.argv[1], sys.argv[2])
