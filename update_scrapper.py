import sqlite3
import requests
from bs4 import BeautifulSoup
import time

# ====== Konfiguration ==========
DB_NAME = "bundesliga.db"
# Struktur: https://www.fussballdaten.de/bundesliga/2026/{spieltag}/
BASE_URL = "https://www.fussballdaten.de/bundesliga/2026/"

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
        print("✅ Alle Spieltage sind bereits aktuell.")
        return False
    
    url = f"{BASE_URL}{spieltag}/"
    print(f"🔍 Scrape Spieltag {spieltag} {'(TEST-MODUS)' if dry_run else ''} von: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        time.sleep(1) # Etwas mehr Pause für fussballdaten.de
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        results = []
        # fussballdaten.de nutzt oft 'spiele-liste' oder spezifische Klassen
        # Wir suchen nach den Zeilen, die Ergebnisse enthalten
        matches = soup.select('.spiel-zeile') or soup.select('.match-list-item')
        
        # Falls die Selektoren nicht greifen, suchen wir generisch in der Tabelle
        if not matches:
            rows = soup.find_all('div', class_='ergebnis') # Beispiel für deren Struktur
            # ... (Logik zur Extraktion) ...
        
        # Vereinfachte Extraktion für fussballdaten (Beispielstruktur)
        # Hinweis: Da fussballdaten oft CSS-Grids nutzt, passen wir die Suche an:
        for match in soup.find_all(class_='ergebnis'):
            parent = match.find_parent()
            teams = parent.find_all(class_='team-name')
            if len(teams) >= 2:
                heim = teams[0].get_text(strip=True)
                gast = teams[1].get_text(strip=True)
                score = match.get_text(strip=True)
                
                if ":" in score:
                    t_h, t_g = map(int, score.split(":"))
                    results.append((t_h, t_g, heim, gast))
                    print(f" {'[WÜRDE SCHREIBEN]' if not dry_run else '[GEFUNDEN]'}: {heim} {t_h}:{t_g} {gast}")

        if not dry_run and results:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            for r in results:
                cursor.execute("""
                    UPDATE spiele SET tore_heim = ?, tore_gast = ?
                    WHERE saison = '2025/26' AND spieltag = ? AND heim = ? AND gast = ?
                """, (r[0], r[1], spieltag, r[2], r[3]))
            conn.commit()
            conn.close()
            print(f"✨ Datenbank für Spieltag {spieltag} aktualisiert!")
        
        return True

    except Exception as e:
        print(f"💥 Fehler beim Scrappen: {e}")
        return False

if __name__ == "__main__":
    # Testlauf für Spieltag 15
    success = run_scrapper(spieltag=15, dry_run=True)
    if success:
        from check_table import save_table_to_txt, show_table
        show_table()
        save_table_to_txt()