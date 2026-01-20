import os
import time
import sqlite3
import datetime
from sqlalchemy import create_engine, text


from update_scrapper import run_scrapper, update_csv_from_db
from check_table import show_table, save_table_to_txt
from validate_bundesliga_csv import validate_csv
from torschuetzenscrapper import update_torschuetzen_db
from rekordspieler import player_scraping

# --- KONFIGURATION ---
DB_NAME = "bundesliga.db"
SAISON = "2025/26"
LOG_FILE = "pipeline_log.txt"


def log_pipeline_run(status, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {status}: {message}\n")

def get_current_update_range():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # 1. Finde alle Spieltage der Saison, die noch NULL-Werte bei den Toren haben
        cursor.execute("""
            SELECT DISTINCT spieltag FROM spiele 
            WHERE saison = ? AND (tore_heim IS NULL OR tore_gast IS NULL)
            ORDER BY spieltag ASC
        """, (SAISON,))
        
        missing_days = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not missing_days:
            return None # Alles aktuell
        
        # Wir nehmen den kleinsten fehlenden Spieltag (z.B. 16 für Nachholspiele)
        start_st = missing_days[0]
        
        # Wir nehmen den höchsten Spieltag, der gerade aktuell sein könnte (heute 18)
        # Um sicherzugehen, nehmen wir den höchsten fehlenden Tag aus der Liste, 
        # aber deckeln ihn sinnvoll (z.B. nicht Spieltag 34 im Januar)
        # Wir nehmen einfach den höchsten 'missing', aber maximal +1 auf den aktuellsten
        end_st = min(34, max(missing_days))
        
        return start_st, end_st
    except Exception:
        return 1, 34

def run_pipeline():
    log_pipeline_run("START", "Intelligentes Update gestartet.")
    print(f"{'='*50}\nBUNDESLIGA SMART UPDATE\n{'='*50}")

    # 1. Automatischer Start- und Endpunkt
    start_st, max_st = get_current_update_range()
    
    print(f"🚀 Analyse abgeschlossen.")
    print(f"🔄 Update-Fokus: Spieltag {start_st} bis {max_st}")

    for st in range(start_st, max_st + 1):
        print(f"Verarbeite Spieltag {st}...", end=" ", flush=True)
        try:
            count = run_scrapper(st)
            print(f"({count} Spiele synchronisiert)")
            time.sleep(1) 
        except Exception as e:
            print(f"\n❌ Fehler an Spieltag {st}: {e}")
            break

    # 2. Abschlussarbeiten
    print(f"\n{'*'*20} FINISH {'*'*20}")
    update_csv_from_db()    # CSV aktualisieren
    validate_csv()          # Logik-Check
    save_table_to_txt()     # Tabelle berechnen & exportieren

    #3. Spielerstatistiken aktualisieren
    print(f"\n{'='*50}")
    print("📊 Starte Update der Spielerstatistiken")
    print(f"{'='*50}")

    # Torschützen aktualisieren
    try:
        update_torschuetzen_db()
    except Exception as e:
        print(f"❌ Fehler beim Erstellen des Updates für die Torschützen: {e}")

    # Rekordspieler aktualisieren
    try:
        player_scraping()
    except Exception as e:
        print(f"❌ Fehler beim Erstellen des Updates der Rekordspieler: {e}")

    print(f"{'='*50}\nALLE DATEN AKTUALISIERT!\n{'='*50}")   
    log_pipeline_run("Success:,  Updates erfolgreich durchgeführt.")
    
if __name__ == "__main__":
    run_pipeline()