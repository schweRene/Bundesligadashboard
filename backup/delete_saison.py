import sqlite3

DB_NAME = "dummy_bundesliga.db"
SAISON_ZU_LOESCHEN = "1966/67"  # Die Saison, die doppelt ist (1966/67 laut deiner Nachricht)

def remove_double_saison():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Erst prüfen, wie viele Spiele aktuell drin sind
        cursor.execute("SELECT COUNT(*) FROM spiele WHERE saison = ?", (SAISON_ZU_LOESCHEN,))
        anzahl = cursor.fetchone()[0]
        print(f"Gefundene Spiele für {SAISON_ZU_LOESCHEN}: {anzahl}")
        
        # Alle Spiele dieser Saison löschen
        cursor.execute("SELECT COUNT(*) FROM spiele WHERE saison = ?", (SAISON_ZU_LOESCHEN,))
        cursor.execute("DELETE FROM spiele WHERE saison = ?", (SAISON_ZU_LOESCHEN,))
        
        conn.commit()
        print(f"Erfolgreich gelöscht. Die Saison {SAISON_ZU_LOESCHEN} ist nun leer.")
        print("Du kannst sie jetzt einmalig neu mit deiner update_db.py importieren.")
        
    except Exception as e:
        print(f"Fehler: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    remove_double_saison()