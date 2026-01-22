import sqlite3

conn = sqlite3.connect("bundesliga.db")
cursor = conn.cursor()

# Update-Befehl für den Namen
cursor.execute("""
    UPDATE suenderkartei 
    SET spieler = 'Josué' 
    WHERE spieler LIKE 'JosuéDefensives Mittelfeld%'
""")

print(f"Lokale Datenbank: {cursor.rowcount} Zeilen korrigiert.")
conn.commit()
conn.close()