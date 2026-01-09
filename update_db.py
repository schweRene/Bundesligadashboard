from update_scrapper import run_scrapper
from check_table import show_table, save_table_to_txt
from validate_bundesliga_csv import validate_csv
import sqlite3
import csv 
import os
import datetime

DB_NAME = "bundesliga.db"
CSV_NAME = "bundesliga_2026.csv"
SAISON = "2025/26"

def run_update():
    print(f"{'=' *50}\nPIPELINE START: SAISON {SAISON}\n{'='*50}")
    if not validate_csv():
        return False
        
    if not os.path.exists(CSV_NAME):
        print(f"❌ FEHLER: {CSV_NAME} fehlt!")
        return False
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        with open(CSV_NAME, mode='r', encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [n.lower() for n in reader.fieldnames]
            added = 0
            for row in reader:
                res = str(row.get('result', '-:-')).strip()
                t_h, t_g = (None, None) if ":" not in res or res == "-:-" else map(int, res.split(":"))
                cursor.execute("""
                    INSERT OR IGNORE INTO spiele (spieltag, saison, heim, gast, tore_heim, tore_gast)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (int(row['spieltag']), SAISON, row['home'].strip(), row['away'].strip(), t_h, t_g))
                if cursor.rowcount > 0: added += 1
        conn.commit()
        print(f"✨ {added} neue Spiele importiert.")
        return True
    except Exception as e:
        print(f"💥 Fehler: {e}")
        return False
    finally:
        conn.close()

def log_pipeline_run(status, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_enty = f"[{timestamp}] STATUS: {status} | {message}\n"

    with open("pipeline_log.txt", "a", encoding="utf-8") as f:
        f.write(log_enty)

def run_pipeline():
    # Wir starten den Log
    log_pipeline_run("START", "Pipeline gestartet.")
    
    update_success = run_update()
    if not update_success:
        log_pipeline_run("ERROR", "CSV-Import oder Validierung fehlgeschlagen.")
        return

    print(f"\n--- STARTE AUTOMATISCHES WEB-UPDATE ----")
    scrapper_success = run_scrapper(dry_run=False)
    
    if scrapper_success:
        log_pipeline_run("SUCCESS", "Web-Update erfolgreich durchgeführt.")
    else:
        log_pipeline_run("WARNING", "Web-Update lieferte keine neuen Daten oder schlug fehl.")

    # Tabelle wird erzeugt
    print("\n--- AKTUALISIERE TABELLEN-DATEI ----")
    show_table()
    save_table_to_txt()
    
    log_pipeline_run("END", "Pipeline-Lauf beendet und Tabelle aktualisiert.")

if __name__ == "__main__":
    run_pipeline()