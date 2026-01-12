import pandas as pd
import sqlite3

# 1. Check die Datenbank direkt
conn = sqlite3.connect('bundesliga.db')
df = pd.read_sql_query("SELECT COUNT(*) as anzahl FROM spiele WHERE result IS NOT NULL", conn)
print(f"Datenbank sagt: {df['anzahl'][0]} Spiele mit Ergebnis gefunden.")
conn.close()

# 2. Schau in die TXT, die deine Pipeline erstellt hat
with open('aktuelle_tabelle.txt', 'r') as f:
    print("\nInhalt der aktuellen_tabelle.txt (Auszug):")
    print(f.read()[:500]) # Zeigt nur den Anfang