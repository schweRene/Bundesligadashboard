import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
import re
from sqlalchemy import create_engine, text
import os
from datetime import datetime, timedelta

# --- KONFIGURATION ---
DB_NAME = "bundesliga.db"
SAISON = "2025/26"
BASE_URL = "https://www.fussballdaten.de/bundesliga/2026/"
DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
engine_cloud = create_engine(DB_URL_CLOUD)

# Deine vollständige Mapping-Liste (unverändert)
TEAM_MAP = {
    "Bremen": "SV Werder Bremen", "Dortmund": "Borussia Dortmund",
    "Frankfurt": "Eintracht Frankfurt", "Nürnberg": "1. FC Nürnberg",
    "Braunschweig": "Eintracht Braunschweig", "Karlsruhe": "Karlsruher SC",
    "TSV 1860": "TSV 1860 München", "Münster": "Preußen Münster",
    "Hamburg": "Hamburger SV", "Kaiserslautern": "1.FC Kaiserslautern",
    "K'lautern": "1.FC Kaiserslautern", "1. FC Kaiserslautern": "1.FC Kaiserslautern",
    "Meidericher SV": "MSV Duisburg", "Duisburg": "MSV Duisburg",
    "Saarbrücken": "1. FC Saarbrücken", "Schalke": "FC Schalke 04",
    "Hertha": "Hertha BSC", "Hannover": "Hannover 96",
    "Neunkirchen": "Borussia Neunkirchen", "Tasmania": "Tasmania Berlin",
    "Essen": "Rot-Weiss Essen", "Offenbach": "Kickers Offenbach",
    "Leipzig": "RB Leipzig", "Oberhausen": "Rot-Weiß Oberhausen",
    "Bielefeld": "Arminia Bielefeld", "Uerdingen": "Bayer 05 Uerdingen",
    "Wattenscheid": "SG Wattenscheid 09", "St. Pauli": "FC St. Pauli",
    "Homburg": "FC 08 Homburg", "Stuttg. Kickers": "Stuttgarter Kickers",
    "Dresden": "Dynamo Dresden", "Rostock": "Hansastat Rostock",
    "Düsseldorf": "Fortuna Düsseldorf", "Unterhaching": "SpVgg Unterhaching",
    "Cottbus": "Energie Cottbus", "Fürth": "SpVgg Greuther Fürth",
    "Paderborn": "SC Paderborn 07", "Ingolstadt": "FC Intolstadt 04",
    "Darmstadt": "SV Darmstadt 98", "Heidenheim": "1. FC Heidenheim",
    "Bayern": "FC Bayern München", "Leverkusen": "Bayer 04 Leverkusen",
    "Gladbach": "Borussia Mönchengladbach", "Stuttgart": "VfB Stuttgart",
    "Augsburg": "1.FC Augsburg", "Mainz": "FSV Mainz 05",
    "Wolfsburg": "VfL Wolfsburg", "Hoffenheim": "TSG Hoffenheim",
    "Freiburg": "SC Freiburg", "Union Berlin": "1. FC Union Berlin",
    "Köln": "1. FC Köln", "Bochum": "VfL Bochum", "Kiel": "Holstein Kiel",
    "M'gladbach": "Borussia Mönchengladbach", "Meiderich": "Meidericher SV"
}

def get_full_team_name(short_name):
    """Sucht den Namen in der TEAM_MAP basierend auf enthaltenen Schlüsselwörtern."""
    for key, full_name in TEAM_MAP.items():
        if key.lower() in short_name.lower():
            return full_name
    return short_name

def run_scrapper():
    print(f"--- Starte Ergebnis-Update für {SAISON} ---")
    # Nutze cloudscraper wie in deinem erfolgreichen Test
    scraper = cloudscraper.create_scraper()
    
    # 1. Welche Spieltage fehlen in der lokalen DB?
    conn_local = sqlite3.connect(DB_NAME)
    cursor = conn_local.cursor()
    cursor.execute("""
        SELECT DISTINCT spieltag FROM spiele 
        WHERE (tore_heim IS NULL OR tore_gast IS NULL) 
        AND saison = ? ORDER BY spieltag ASC
    """, (SAISON,))
    missing_days = [row[0] for row in cursor.fetchall()]
    conn_local.close()

    if not missing_days:
        print("✅ Alle bisherigen Spiele haben Ergebnisse.")
        return

    for spieltag in missing_days:
        url = f"{BASE_URL}{spieltag}/"
        try:
            # cloudscraper statt requests
            response = scraper.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            matches_found = 0
            
            # Die robuste Suche aus deinem Testskript
            all_links = soup.find_all('a')
            seen_matches = set()

            for link in all_links:
                text_content = link.get_text(" ", strip=True)
                
                # Ergebnis-Muster finden
                if re.search(r'\d+:\d+', text_content):
                    raw_line = link.parent.get_text(" ", strip=True)
                    
                    # Regex zum Trennen von Heim, Ergebnis und Gast
                    match = re.search(r'(.+?)\s+(\d+:\d+)\s+(\d+:\d+)?\s*(.+)', raw_line)
                    
                    if match:
                        h_raw = match.group(1)
                        res_raw = match.group(2)
                        g_raw = match.group(4)
                        
                        h_full = get_full_team_name(h_raw)
                        g_full = get_full_team_name(g_raw)
                        
                        match_id = f"{h_full}-{g_full}-{spieltag}"
                        if match_id not in seen_matches:
                            try:
                                th, tg = map(int, res_raw.split(':'))
                                
                                # A. LOKALE DB UPDATE
                                conn_l = sqlite3.connect(DB_NAME)
                                cur_l = conn_l.cursor()
                                cur_l.execute("""
                                    UPDATE spiele SET tore_heim = ?, tore_gast = ? 
                                    WHERE saison = ? AND spieltag = ? AND heim = ? AND gast = ?
                                """, (th, tg, SAISON, spieltag, h_full, g_full))
                                
                                if cur_l.rowcount > 0:
                                    conn_l.commit()
                                    # B. CLOUD DB UPDATE
                                    if engine_cloud:
                                        try:
                                            with engine_cloud.begin() as conn_c:
                                                conn_c.execute(text("""
                                                    UPDATE spiele SET tore_heim = :th, tore_gast = :tg 
                                                    WHERE saison = :s AND spieltag = :st AND heim = :h AND gast = :g
                                                """), {"th": th, "tg": tg, "s": SAISON, "st": spieltag, "h": h_full, "g": g_full})
                                        except Exception as cloud_err:
                                            print(f"Cloud-Fehler: {cloud_err}")
                                    
                                    matches_found += 1
                                    print(f"Spieltag {spieltag}: {h_full} {th}:{tg} {g_full} eingetragen.")
                                
                                conn_l.close()
                                seen_matches.add(match_id)
                                
                            except ValueError:
                                continue

            print(f"Spieltag {spieltag}: {matches_found} Ergebnisse aktualisiert.")

        except Exception as e:
            print(f"Fehler bei Spieltag {spieltag}: {e}")

if __name__ == "__main__":
    run_scrapper()