import sqlite3
import csv
import os

# === Konfig === 
DB_NAME = "dummy_bundesliga.db"
CSV_NAME = "bundesliga_2026.csv"
SAISON = "2025/26"

def simulation():
    if not os.path.exists(CSV_NAME):
        print(f"Fehler: {CSV_NAME} nicht gefunden!")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print(f"--- 2026 TEST-SIMULATION (Vollständiger Check) ---")
    
    try:
        with open(CSV_NAME, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [n.lower() for n in reader.fieldnames]
            
            count = 0
            results_found = 0
            null_values = 0
            
            # Speicher für Stichproben
            samples = {15: [], 16: [], 34: []}

            for row in reader:
                st = int(row.get('spieltag', 0))
                res = row.get('result', '-:-')
                
                # NULL-Logik
                if res == "-:-" or ":" not in str(res):
                    t_h, t_g = None, None
                    null_values += 1
                else:
                    try:
                        t_h, t_g = res.split(":")
                        t_h, t_g = int(t_h), int(t_g)
                        results_found += 1
                    except:
                        t_h, t_g = None, None
                        null_values += 1

                # Test-Insert
                cursor.execute("""
                    INSERT INTO spiele (spieltag, saison, heim, gast, tore_heim, tore_gast)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (st, SAISON, row['home'], row['away'], t_h, t_g))
                count += 1
                
                # Stichproben sammeln
                if st in samples:
                    samples[st].append(f"  {row['home']} vs {row['away']} -> {t_h}:{t_g}")

        # --- Detaillierte Auswertung ---
        for st in sorted(samples.keys()):
            print(f"\n[SPIELTAG {st}]")
            for m in samples[st]:
                print(m)

        print(f"\n{'-'*40}")
        print(f"TECHNISCHE ZUSAMMENFASSUNG:")
        print(f"Gesamt verarbeitet: {count} Spiele")
        print(f"Davon mit Toren:    {results_found}")
        print(f"Davon mit NULL:     {null_values}")
        print(f"{'-'*40}")
        
    except Exception as e:
        print(f"Fehler: {e}")
    finally:
        conn.rollback() 
        print("\nRollback ausgeführt. Datenbank bleibt sauber.")
        conn.close()

if __name__ == "__main__":
    simulation()