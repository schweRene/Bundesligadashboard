import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import io
import re
from sqlalchemy import create_engine, text

#Konfiguration
DB_URL = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
engine = create_engine(DB_URL)

def clean_player_name(full_name):
    #Daten bereinigen ohne Verein, nur der Name
    # Wir suchen eine Zahl, die nicht Teil des Namens ist
    name = str(full_name).strip()
    name = re.split(r'\s\d', name)[0]

    # 2. Schritt: Wir teilen den Rest in einzelne Wörter auf
    words = name.split()

    if len(words) >= 2:
        return f"{words[0]} {words[1]}"
    return name

def update_torschuetzen_db():
    print("---Starte Torschützen-Update in die DB")
    url = "https://www.fussballdaten.de/bundesliga/historie/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    try:
        # 1. Webseite laden
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("Erfolgreich: Webseite geladen")

        # 2. HTML parsen
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table') 
        
        if table is None:
            print("Fehler: Tabelle nicht gefunden!")
            return False

        # 3. Tabelle einlesen mit StringIO
        df = pd.read_html(io.StringIO(str(table)))[0]
        
                
        # 4. Spalten präzise auswählen (#, Spieler, Spiele, Tore)
        df = df.iloc[:, [0, 1, 2, 3]].copy() 
        df.columns = ["platz", "spieler", "spiele", "tore"]

        # 5. Datenreinigung
        # Wir filtern Zeilen, die im Feld 'platz' keine Ziffern haben
        df['spieler'] = df['spieler'].apply(clean_player_name)
        df = df[df['platz'].astype(str).str.contains(r'^\d+$', na=False)].copy()
        
        # Typen konvertieren
        df['platz'] = df['platz'].astype(int)
        df['spiele'] = df['spiele'].astype(int)
        df['tore'] = df['tore'].astype(int)

        #Print-Anweisung Bestätigung in DB geschrieben
        print(f"Versuche {len(df)} Einträge in die DB zu schreiben")

        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS torschuetzen (
                    platz INT PRIMARY KEY,
                    spieler TEXT,
                    spiele INT,
                    tore INT
                );
            """))

            conn.execute(text("TRUNCATE TABLE torschuetzen;"))

            #Daten einfügen
            for _, row in df.iterrows():
                conn.execute(
                    text("INSERT INTO torschuetzen (platz, spieler, spiele, tore) VALUES (:p, :s, :sp, :t)"),
                    {"p": row['platz'], "s": row['spieler'], "sp": row['spiele'], "t": row['tore']}
                )

            print("✅ Datenbank erfolgreich aktualisiert.")       
            df.to_csv("torschuetzen.csv", index=False, encoding="utf-8")
            return True
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False

if __name__ == "__main__":
    update_torschuetzen_db()



