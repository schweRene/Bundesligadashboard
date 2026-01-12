import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import re

# ====== Konfiguration ==========
DB_NAME = "bundesliga.db"
BASE_URL = "https://www.fussballdaten.de/bundesliga/2026/"

def clean_team_name(name):
    """Entfernt Tabellenplätze, Punkte und Klammern."""
    name = re.sub(r'\(\d+\.\)', '', name)
    name = name.replace('.)', '').replace('(', '').replace(')', '')
    return name.strip()

def get_next_missing_matchday():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(spieltag) FROM spiele WHERE saison = '2025/26' AND tore_heim IS NULL")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else None

def run_scrapper(spieltag=None, dry_run=False):
    if spieltag is None:
        spieltag = get_next_missing_matchday()

    if spieltag is None:
        print("✅ Alle Spieltage in der Datenbank sind bereits aktuell.")
        return False
    
    url = f"{BASE_URL}{spieltag}/"
    print(f"🔍 Scrape Spieltag {spieltag} von: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        for row in soup.find_all(['div', 'a', 'tr']):
            text = row.get_text(" ", strip=True)
            match = re.search(r'(\D+)\s+(\d+):(\d+)\s+(\d+):(\d+)\s+(\D+)', text)
            
            if match:
                heim = clean_team_name(match.group(1))
                t_h = int(match.group(2))
                t_g = int(match.group(3))
                gast = clean_team_name(match.group(6))
                
                if (t_h, t_g, heim, gast) not in results:
                    results.append((t_h, t_g, heim, gast))
                    print(f"   -> Gefunden: {heim} {t_h}:{t_g} {gast}")

        if not results:
            print(f"⚠️ Keine Ergebnisse gefunden.")
            return False

        if not dry_run:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            updated_count = 0
            for r in results:
                heim_name, gast_name = r[2], r[3]
                
                # Spezial-Logik für Gladbach und andere Abkürzungen:
                # Wir nehmen nur den aussagekräftigsten Teil des Namens
                h_search = heim_name.replace("M'gladbach", "gladbach").replace("Mönchengladbach", "gladbach")
                g_search = gast_name.replace("M'gladbach", "gladbach").replace("Mönchengladbach", "gladbach")
                
                # Wir suchen jetzt mit dem bereinigten Begriff
                cursor.execute("""
                    UPDATE spiele 
                    SET tore_heim = ?, tore_gast = ?
                    WHERE saison = '2025/26' AND spieltag = ? 
                    AND (heim LIKE ? OR gast LIKE ? OR ? LIKE '%' || heim || '%')
                    AND (heim LIKE ? OR gast LIKE ? OR ? LIKE '%' || gast || '%')
                """, (r[0], r[1], spieltag, 
                      f"%{h_search}%", f"%{h_search}%", h_search,
                      f"%{g_search}%", f"%{g_search}%", g_search))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                else:
                    print(f"      ⚠️  Konnte Spiel {heim_name} vs {gast_name} immer noch nicht zuordnen.")
            
            conn.commit()
            conn.close()
            print(f"✨ Erfolgreich {updated_count} Spiele aktualisiert!")
            return True
        return True

    except Exception as e:
        print(f"💥 Fehler: {e}")
        return False

if __name__ == "__main__":
    run_scrapper(dry_run=False)