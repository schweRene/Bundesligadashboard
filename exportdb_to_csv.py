import sqlite3
import pandas as pd

#Verbindung zur lokalen Datei
conn = sqlite3.connect('bundesliga.db')
df = pd.read_sql_query('SELECT * FROM spiele', conn)

#Konvertiere die Tore-Spalten explizit in Ganzzahlen(Integer)
#Falls leere Felder vorhanden, mit 0 füllen oder als String lassen
df['tore_heim'] = df['tore_heim'].fillna(0).astype(int)
df['tore_gast'] = df['tore_gast'].fillna(0).astype(int)

# Als CSV speichern (ohne Index, damit Supabase nicht verwirrt ist)
df.to_csv('spiele_export.csv', index=False)
conn.close()
print("Fertig! Die Datei 'spiele_export.csv' wurde erstellt!")