import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import io
import re
from sqlalchemy import create_engine, text
import sqlite3

# --- KONFIGURATION ---
# 1. Cloud-Verbindung (Supabase)
DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
engine_cloud = create_engine(DB_URL_CLOUD)

# 2. Lokale Verbindung (SQLite Datei)
DB_NAME_LOCAL = "bundesliga.db"

def clean_player_name(full_name):
    name = str(full_name).strip()
    name = re.split(r'\s\d', name)[0]
    words = name.split()
    if len(words) >= 2:
        return f"{words[0]} {words[1]}"
    return name

def update_torschuetzen_db():
    print("--- Starte Torschützen-Update ---")
    url = "https://www.fussballdaten.de/bundesliga/historie/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Fehler beim Laden der Webseite")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table: return

    df = pd.read_html(io.StringIO(str(table)))[0]
    df.columns = ['platz', 'spieler', 'spiele', 'tore']
    
    df['spieler'] = df['spieler'].apply(clean_player_name)
    df = df[df['platz'].astype(str).str.contains(r'^\d+$', na=False)].copy()
    df['platz'] = df['platz'].astype(int)
    df['spiele'] = df['spiele'].astype(int)
    df['tore'] = df['tore'].astype(int)

    print(f"Schreibe {len(df)} Einträge in BEIDE Datenbanken...")

    # --- TEIL A: IN DIE CLOUD SCHREIBEN (Supabase) ---
    try:
        with engine_cloud.begin() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS torschuetzen (platz INT PRIMARY KEY, spieler TEXT, spiele INT, tore INT);"))
            conn.execute(text("TRUNCATE TABLE torschuetzen;"))
            for _, row in df.iterrows():
                conn.execute(text("INSERT INTO torschuetzen (platz, spieler, spiele, tore) VALUES (:p, :s, :sp, :t)"),
                           {"p": row['platz'], "s": row['spieler'], "sp": row['spiele'], "t": row['tore']})
        print("✅ Cloud-Update (Supabase) erfolgreich.")
    except Exception as e:
        print(f"❌ Cloud-Fehler: {e}")

    # --- TEIL B: IN DIE LOKALE DATEI SCHREIBEN (SQLite) ---
    try:
        local_conn = sqlite3.connect(DB_NAME_LOCAL)
        cursor = local_conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS torschuetzen (platz INT PRIMARY KEY, spieler TEXT, spiele INT, tore INT);")
        cursor.execute("DELETE FROM torschuetzen;") # SQLite kennt kein TRUNCATE, daher DELETE
        for _, row in df.iterrows():
            cursor.execute("INSERT INTO torschuetzen (platz, spieler, spiele, tore) VALUES (?, ?, ?, ?)",
                         (int(row['platz']), str(row['spieler']), int(row['spiele']), int(row['tore'])))
        local_conn.commit()
        local_conn.close()
        print("✅ Lokales Update (bundesliga.db) erfolgreich.")
    except Exception as e:
        print(f"❌ Lokal-Fehler: {e}")

if __name__ == "__main__":
    update_torschuetzen_db()