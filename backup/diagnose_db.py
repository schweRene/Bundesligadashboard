import sqlite3
import os

DB_NAME = "bundesliga.db"

def diagnose():
    if not os.path.exists(DB_NAME):
        print("DB nicht gefunden.")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("--- TEAMNAMEN IN DEINER DATENBANK ---")
    cursor.execute("SELECT DISTINCT heim FROM spiele ORDER BY heim")
    db_teams = [row[0] for row in cursor.fetchall()]
    for team in db_teams:
        print(f"'{team}'")
        
    conn.close()

if __name__ == "__main__":
    diagnose()