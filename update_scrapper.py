import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import csv
import time

DB_NAME = "bundesliga.db"
CSV_NAME = "bundesliga_2026.csv"
SAISON = "2025/26"
BASE_URL = "https://www.fussballdaten.de/bundesliga/2026/"

# Deine vollständige Mapping-Liste (Bitte im Code behalten)
TEAM_MAP = {
    "Bremen": "SV Werder Bremen", "Dortmund": "Borussia Dortmund",
    "K'lautern": "1.FC Kaiserslautern", "1. FC Kaiserslautern": "1.FC Kaiserslautern",
    "Frankfurt": "Eintracht Frankfurt", "Nürnberg": "1. FC Nürnberg",
    "Braunschweig": "Eintracht Braunschweig", "Karlsruhe": "Karlsruher SC",
    "TSV 1860": "TSV 1860 München", "Münster": "Preußen Münster",
    "Hamburg": "Hamburger SV", "Köln": "1. FC Köln",
    "Stuttgart": "VfB Stuttgart", "Saarbrücken": "1. FC Saarbrücken",
    "Schalke": "FC Schalke 04", "Schalke 04": "FC Schalke 04",
    "M'gladbach": "Borussia Mönchengladbach", "Bayern": "FC Bayern München",
    "Düsseldorf": "Fortuna Düsseldorf", "Offenbach": "Kickers Offenbach",
    "Wuppertal": "Wuppertaler SV", "Bielefeld": "Arminia Bielefeld",
    "Tasmania": "Tasmania Berlin", "Mannheim": "Waldhof Mannheim",
    "Leverkusen": "Bayer 04 Leverkusen", "St. Kickers": "Stuttgarter Kickers",
    "Uerdingen": "KFC Uerdingen", "Wattenscheid": "SG Wattenscheid 09",
    "TB Berlin": "Tennis Borussia Berlin", "Duisburg": "MSV Duisburg",
    "RW Essen": "Rot Weiss Essen", "Dresden": "SG Dynamo Dresden",
    "Freiburg": "SC Freiburg", "Rostock": "FC Hansa Rostock",
    "St. Pauli": "FC St Pauli", "Wolfsburg": "VfL Wolfsburg",
    "Cottbus": "Energie Cottbus", "Hoffenheim": "TSG Hoffenheim",
    "Hannover": "Hannover 96", "Paderborn": "SC Paderborn 07",
    "Ingolstadt": "FC Ingolstadt 04", "Darmstadt": "SV Darmstadt 98",
    "Leipzig": "RB Leipzig", "Union Berlin": "1. FC Union Berlin",
    "Heidenheim": "1. FC Heidenheim", "Holstein Kiel": "Holstein Kiel",
    "Augsburg": "1.FC Augsburg", "Mainz": "FSV Mainz 05",
    "Neunkirchen": "Borussia Neunkirchen", "Homburg": "FC 08 Homburg",
    "Fürth": "SpVgg Greuther Fürth", "Oberhausen": "Rot Weiss Oberhausen",
    "Ulm": "SSV Ulm 1846", "Aachen": "Alemania Aachen", "Meiderich": "MSV Duisburg"
}

def get_clean_team_name(text):
    if not text: return None
    for key, full_name in TEAM_MAP.items():
        if key.lower() in text.lower():
            return full_name
    return None

def update_csv_from_db():
    conn = sqlite3.connect(DB_NAME)
    query = f"SELECT spieltag, heim, gast, tore_heim, tore_gast FROM spiele WHERE saison = '{SAISON}' ORDER BY spieltag ASC, heim ASC"
    rows = conn.execute(query).fetchall()
    conn.close()
    with open(CSV_NAME, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['spieltag', 'home', 'away', 'result'])
        for r in rows:
            res = f"{r[3]}:{r[4]}" if r[3] is not None else "-:-"
            writer.writerow([r[0], r[1], r[2], res])

def run_scrapper(spieltag):
    url = f"{BASE_URL}{spieltag}/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # Retry-Logik (versucht es bis zu 3 Mal bei Timeouts)
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=20) # Timeout auf 20s erhöht
            soup = BeautifulSoup(response.text, 'html.parser')
            found_count = 0
            
            for row in soup.find_all(['div', 'a', 'tr'], class_=re.compile(r'spiele-row|det-match')):
                text = row.get_text(" ", strip=True)
                teams = []
                potential_parts = re.split(r'\d+:\d+|\s-\s|\|', text)
                for part in potential_parts:
                    name = get_clean_team_name(part)
                    if name and name not in teams: teams.append(name)
                
                if len(teams) >= 2:
                    heim, gast = teams[0], teams[1]
                    t_h, t_g = None, None
                    res_match = re.search(r'(\d+):(\d+)', text)
                    if res_match:
                        h_val, g_val = int(res_match.group(1)), int(res_match.group(2))
                        hat_datum = bool(re.search(r'\d{2}\.\d{2}\.', text))
                        # Strenge Prüfung gegen Geister-Tore
                        if h_val < 15 and "uhr" not in text.lower():
                            if spieltag <= 17 or hat_datum:
                                t_h, t_g = h_val, g_val

                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("""INSERT OR REPLACE INTO spiele (saison, spieltag, heim, gast, tore_heim, tore_gast)
                                    VALUES (?, ?, ?, ?, ?, ?)""", (SAISON, spieltag, heim, gast, t_h, t_g))
                    conn.commit()
                    conn.close()
                    found_count += 1
            return found_count
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            print(f" (Timeout-Retry {attempt+1})...", end="")
            time.sleep(2) # Kurz warten vor dem nächsten Versuch
    return 0