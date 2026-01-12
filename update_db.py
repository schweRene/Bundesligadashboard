import os
import time
import sqlite3
import datetime
from update_scrapper import run_scrapper, update_csv_from_db
from check_table import show_table, save_table_to_txt
from validate_bundesliga_csv import validate_csv

DB_NAME = "bundesliga.db"
SAISON = "2025/26"
LOG_FILE = "pipeline_log.txt"

def log_pipeline_run(status, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {status}: {message}\n")

def reset_db_season():
    print(f"🧹 Bereinige Datenbank für Saison {SAISON}...")
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM spiele WHERE saison = ?", (SAISON,))
    conn.commit()
    conn.close()

def run_pipeline():
    log_pipeline_run("START", "Pipeline mit Timeout-Schutz gestartet.")
    print(f"{'='*50}\nBUNDESLIGA UPDATE (RETRY-MODUS)\n{'='*50}")

    reset_db_season()

    for st in range(1, 35):
        print(f"Spieltag {st}/34...", end=" ", flush=True)
        count = run_scrapper(st)
        print(f"Gefunden: {count}/9")
        time.sleep(1.0) # Höhere Pause zwischen den Spieltagen gegen Blocking

    update_csv_from_db()

    print(f"\n--- AUDIT & VALIDIERUNG ---")
    if validate_csv():
        log_pipeline_run("SUCCESS", "Alle Daten geladen.")
        show_table()
        save_table_to_txt()
    else:
        log_pipeline_run("ERROR", "Audit fehlerhaft.")

if __name__ == "__main__":
    run_pipeline()