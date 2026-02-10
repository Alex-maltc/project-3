"""
Projekt: Election Scraper 2017
Autor: Aleksei Maltcev
Popis: Skript pro stahování výsledků voleb z webu volby.cz.
"""
import sys
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import pandas as pd


def validate_args(args: List[str]) -> None:
    """Ověří přítomnost dvou povinných argumentů a validitu URL."""
    if len(args) != 3:
        print("Chyba: Zadejte URL adresu a název výstupního souboru.")
        print('Použití: python main.py "URL" "vysledky.csv"')
        sys.exit(1)
    if "volby.cz" not in args[1]:
        print("Chyba: Zadaný odkaz není z domény volby.cz.")
        sys.exit(1)


def get_soup(url: str) -> Optional[BeautifulSoup]:
    """Stáhne HTML obsah a vrátí objekt BeautifulSoup."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.RequestException as e:
        print(f"Nastala chyba při stahování dat: {e}")
        return None


def get_municipality_links(url: str) -> List[Dict[str, str]]:
    """Získá kódy obcí a jejich URL z přehledu územního celku."""
    soup = get_soup(url)
    if not soup:
        return []

    base_url: str = "https://www.volby.cz/pls/ps2017nss/"
    links: List[Dict[str, str]] = []

    for td_code in soup.find_all("td", class_="cislo"):
        a_tag = td_code.find("a")
        if a_tag:
            links.append({
                "code": a_tag.text,
                "url": base_url + a_tag["href"]
            })
    return links


def parse_city_data(city_info: Dict[str, str]) -> Dict[str, str]:
    """Získá název, statistiky a hlasy stran z konkrétní obce."""
    soup = get_soup(city_info["url"])
    if not soup:
        return {}

    # Název obce je v druhém nadpisu h3
    city_name = soup.find_all("h3")[1].text.split(":")[-1].strip()
    
    # Účast (tabulka s ID ps311_t1)
    summary_tds = soup.find("table", id="ps311_t1").find_all("td")
    
    data: Dict[str, str] = {
        "code": city_info["code"],
        "location": city_name,
        "registered": summary_tds[3].text.replace('\xa0', ''),
        "envelopes": summary_tds[4].text.replace('\xa0', ''),
        "valid": summary_tds[7].text.replace('\xa0', '')
    }

    # Hlasy pro strany (všechny tabulky 'table' kromě první)
    for table in soup.find_all("table", class_="table")[1:]:
        for row in table.find_all("tr")[2:]:
            cols = row.find_all("td")
            if len(cols) > 2 and cols[1].text != "-":
                data[cols[1].text] = cols[2].text.replace('\xa0', '')
    
    return data


def main() -> None:
    """Řídící funkce scraperu."""
    validate_args(sys.argv)
    target_url, output_file = sys.argv[1], sys.argv[2]
    
    print(f"VYHLEDÁVÁM OBCE NA ADRESE: {target_url}")
    municipality_links = get_municipality_links(target_url)
    
    if not municipality_links:
        print("Nebyly nalezeny žádné obce ke zpracování.")
        return

    all_results: List[Dict[str, str]] = []
    print(f"ZPRACOVÁVÁM CELKEM {len(municipality_links)} OBCÍ...")
    
    for item in municipality_links:
        row = parse_city_data(item)
        if row:
            all_results.append(row)
    
    # Uložení pomocí pandas (automaticky vyřeší chybějící sloupce stran)
    df = pd.DataFrame(all_results).fillna("0")
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"HOTOVO. DATA ULOŽENA DO SOUBORU: {output_file}")


if __name__ == "__main__":
    main()