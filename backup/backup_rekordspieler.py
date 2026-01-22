import pandas as pd
import requests
import io
import re
import streamlit as st
from sqlalchemy import create_engine, text

# Konfiguration 
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

def player_scraping():
    print("----------- Starte Rekordspieler-Update -----")
    url = "https://www.fussballdaten.de/bundesliga/rekordspieler/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    print(f"Starte Scraping von {url}....")

    try:
        response = requests.get(url, headers=headers)
        #Lesen aller Tabellen auf der Seite
        dfs = pd.read_html(io.StringIO(response.text))
        df = dfs[0]

        # Picken der Spalten # (0), Spieler(1), Spiele(3)
        #Webseitenstruktur: Rang, Spieler, Tore, Spiele
        df_clean = df.iloc[:, [0, 1, 3]].copy()
        df_clean.columns = ['platz', 'spieler', 'spiele']

        # Datenbereinigung
        df_clean['spieler'] = df_clean['spieler'].apply(clean_player_name)
        df_clean['platz'] = df_clean['platz'].astype(int)
        df_clean['spiele'] = df_clean['spiele'].astype(int)

        print(f"Versuche {len(df_clean)} Einträge in die DB zu schreiben..........")

        # In DB schreiben
        with engine.begin() as conn:
            #Tabelle erstellen, falls noch nicht vorhanden
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS rekordspieler (
                        platz INT PRIMARY KEY,
                        spieler TEXT, 
                        spiele INT
                );
            """))

            #Tabelle leeren
            conn.execute(text("TRUNCATE TABLE rekordspieler;"))

            # Daten einfügen
            for _, row in df_clean.iterrows():
                conn.execute(
                    text("INSERT INTO rekordspieler (platz, spieler, spiele) VALUES (:p, :s, :sp)"),
                    {"p": row['platz'], "s": row['spieler'], "sp": row['spiele']}
                )

        print("✅ Datenbank 'rekordspieler' erfolgreich aktualisiert.")

        # In CSV speichern als Backup zur Kontrolle
        df_clean.to_csv("rekordspieler.csv", index=False, encoding="utf-8")

    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False

if __name__ == "__main__":
    player_scraping()