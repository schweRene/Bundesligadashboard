import os
import time
import sqlite3
import datetime
from sqlalchemy import create_engine, text


from update_scrapper import run_scrapper, update_csv_from_db
from check_table import show_table, save_table_to_txt
from validate_bundesliga_csv import validate_csv

# --- KONFIGURATION ---
DB_NAME = "bundesliga.db"
SAISON = "2025/26"
LOG_FILE = "pipeline_log.txt"


def log_pipeline_run(status, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {status}: {message}\n")

def get_current_update_range():
    """
    Ermittelt automatisch, welche Spieltage ein Update benötigen.
    Prüft den ersten Spieltag ohne Tore und nimmt zur Sicherheit den davor mit.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Finde den kleinsten Spieltag, der noch keine Tore hat
        cursor.execute("""
            SELECT MIN(spieltag) FROM spiele 
            WHERE saison = ? AND (tore_heim IS NULL OR tore_gast IS NULL)
        """, (SAISON,))
        first_empty = cursor.fetchone()[0]
        conn.close()

        if first_empty is None:
            return 34, 34 # Saison scheint beendet
        
        # Wir starten beim Tag davor (falls Tore korrigiert wurden) 
        # aber nicht unter 1
        start_st = max(1, first_empty - 1)
        # Wir prüfen bis zu 2 Spieltage in die Zukunft
        end_st = min(34, first_empty + 1)
        
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
   
    log_pipeline_run("ENDE", f"Update Spieltag {start_st}-{max_st} erfolgreich.")
    print(f"{'='*50}\nALLE DATEN AKTUALISIERT!\n{'='*50}")

if __name__ == "__main__":
    run_pipeline()