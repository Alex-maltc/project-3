"""
Projekt: Election Scraper 2017
Autor: Aleksei Maltcev
Popis: Skript pro stahování výsledků voleb z webu volby.cz.
"""

import sys
import csv
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import pandas as pd


def validate_args(args: List[str]) -> None:
    """Ověří vstupní argumenty z příkazové řádky."""
    if len(args) != 3:
        print("Chyba: Zadejte URL a název výstupního souboru.")
        print('Příklad: python main.py "URL_ADRESA" "vysledky.csv"')
        sys.exit(1)
    if "volby.cz" not in args[1]:
        print("Chyba: Neplatná doména v URL.")
        sys.exit(1)


def get_soup(url: str) -> Optional[BeautifulSoup]:
    """Stáhne obsah stránky a vrátí objekt BeautifulSoup."""
    headers: Dict[str, str] = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.RequestException as exc:
        print(f"Chyba při stahování {url}: {exc}")
        return None


def get_municipality_links(url: str) -> List[str]:
    """Získá seznam všech odkazů na detaily obcí."""
    soup = get_soup(url)
    if not soup:
        return []
    
    links: List[str] = []
    base_url = "https://www.volby.cz/pls/ps2017nss/"
    # Odkazy jsou v buňkách td s třídou 'cislo'
    for td in soup.find_all("td", class_="cislo"):
        a_tag = td.find("a")
        if a_tag:
            links.append(base_url + a_tag["href"])
    return links


def parse_municipality_data(url: str) -> Dict[str, str]:
    """Získá statistiky a výsledky stran z konkrétní obce."""
    soup = get_soup(url)
    if not soup:
        return {}

    # Základní info o obci
    # ID obce se bere z URL parametru 'xobec'
    m_id = url.split("xobec=")[1].split("&")[0]
    name = soup.find_all("h3")[1].text.split(":")[-1].strip()
    
    # Účast (tabulka ps311_t1)
    table_sum = soup.find("table", id="ps311_t1")
    tds = table_sum.find_all("td")
    
    data = {
        "code": m_id,
        "location": name,
        "registered": tds[3].text.replace('\xa0', ''),
        "envelopes": tds[4].text.replace('\xa0', ''),
        "valid": tds[7].text.replace('\xa0', '')
    }

    # Hlasy pro strany (všechny tabulky s třídou 'table' kromě první)
    for table in soup.find_all("table", class_="table")[1:]:
        for row in table.find_all("tr")[2:]:
            cols = row.find_all("td")
            if len(cols) > 2 and cols[1].text != "-":
                data[cols[1].text] = cols[2].text.replace('\xa0', '')
    
    return data


def run_scraper(target_url: str, output_name: str) -> None:
    """Hlavní procesní funkce scraperu."""
    print(f"Stahuji data z: {target_url}")
    links = get_municipality_links(target_url)
    
    if not links:
        print("Nebyly nalezeny žádné odkazy na obce.")
        return

    results: List[Dict[str, str]] = []
    for i, link in enumerate(links, 1):
        m_data = parse_municipality_data(link)
        if m_data:
            print(f"Zpracovávám {i}/{len(links)}: {m_data['location']}")
            results.append(m_data)

    # Uložení pomocí pandas pro správné zarovnání sloupců (stran)
    df = pd.DataFrame(results).fillna(0)
    df.to_csv(output_name, index=False, encoding="utf-8-sig")
    print(f"Hotovo. Data uložena do {output_name}")


if __name__ == "__main__":
    validate_args(sys.argv)
    run_scraper(sys.argv[1], sys.argv[2])