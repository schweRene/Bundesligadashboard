import pandas as pd
import requests
import io
import re
from sqlalchemy import create_engine, text
import sqlite3

DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
DB_NAME_LOCAL = "bundesliga.db"

def clean_player_name(full_name):
    name = str(full_name).strip()
    
    # 1. Fall: Name ist durch Großbuchstaben am Vereinsanfang verklebt (z.B. "Charly KörbelEintracht")
    # Wir fügen ein Leerzeichen vor Großbuchstaben ein, die auf Kleinbuchstaben folgen
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    
    # 2. Schritt: Wir nehmen nur die ersten zwei Wörter (Vorname & Nachname)
    # Das funktioniert bei 99% der Bundesligaspieler perfekt.
    parts = name.split()
    if len(parts) >= 2:
        # Spezialfall für Namen wie "Ditmar Jakobs" (verhindert das Mitschleifen von "Hamburger SV")
        return f"{parts[0]} {parts[1]}"
    
    return name

def player_scraping():
    print("--- Korrektur Rekordspieler ---")
    url = "https://www.fussballdaten.de/bundesliga/rekordspieler/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    response = requests.get(url, headers=headers)
    # Wir nehmen die Tabelle und achten genau auf die Spalten
    df = pd.read_html(io.StringIO(response.text))[0]
    
    # Die Seite hat: 0: Platz, 1: Spieler, 2: Spiele
    df_clean = df.iloc[:, [0, 1, 3]].copy()
    df_clean.columns = ['platz', 'spieler', 'spiele']

    df_clean['spieler'] = df_clean['spieler'].apply(clean_player_name)
    # Nur Zeilen behalten, wo Platz eine Zahl ist
    df_clean = df_clean[df_clean['platz'].astype(str).str.isdigit()]
    
    df_clean['platz'] = df_clean['platz'].astype(int)
    df_clean['spiele'] = df_clean['spiele'].astype(int)

    # LOKAL
    conn = sqlite3.connect(DB_NAME_LOCAL)
    df_clean.to_sql("rekordspieler", conn, if_exists="replace", index=False)
    conn.close()

    # CLOUD
    engine = create_engine(DB_URL_CLOUD)
    with engine.begin() as conn_c:
        conn_c.execute(text("TRUNCATE TABLE rekordspieler;"))
        df_clean.to_sql("rekordspieler", conn_c, if_exists="append", index=False)
    
    print(f"✅ Rekordspieler korrigiert ({len(df_clean)} Einträge).")

if __name__ == "__main__":
    player_scraping()