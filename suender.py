import pandas as pd
import cloudscraper
import io
import re
import time
from sqlalchemy import create_engine, text
import sqlite3

# --- KONFIGURATION ---
DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
DB_NAME_LOCAL = "bundesliga.db"

def clean_name(text):
    if not isinstance(text, str): return text
    match = re.search(r'([a-z])([A-Z])', text)
    if match:
        return text[:match.start()+1].strip()
    return text.strip()

def update_suender():
    # Wir nutzen deinen Code für die Saison 2025/2026
    jahr = 2025
    saison_name = "2025/26"
    scraper = cloudscraper.create_scraper()
    
    url = f"https://www.transfermarkt.de/bundesliga/suenderkartei/wettbewerb/L1/saison_id/{jahr}/plus/1"
    print(f"Lade aktuelle Saison {saison_name}...")
    
    try:
        response = scraper.get(url)
        if response.status_code == 200:
            html_data = io.StringIO(response.text)
            dfs = pd.read_html(html_data)
            df = dfs[1]

            # 1. Datenreinigung (Dein Code)
            df = df[df.iloc[:, 0].notna()].copy()
            
            # 2. Spaltenwahl (Dein Code)
            df = df.iloc[:, [0, 1, 4, 6, 7, 8, 10]]
            df.columns = ['platz', 'spieler', 'einsaetze', 'gelb', 'gelb_rot', 'rot', 'punkte']
            
            # 3. Saison-Spalte hinzufügen (Dein Code)
            df.insert(0, 'saison', saison_name)
            
            # 4. Namen säubern (Dein Code)
            df['spieler'] = df['spieler'].apply(clean_name)

            # 5. Zahlen formatieren (Dein Code - DER WICHTIGE TEIL)
            for col in ['platz', 'einsaetze', 'gelb', 'gelb_rot', 'rot', 'punkte']:
                # Entfernt Bindestriche und sorgt für saubere Ganzzahlen
                df[col] = df[col].astype(str).str.replace('-', '0').str.split('.').str[0]
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

            print(f"   -> Erfolg: {len(df)} Spieler gefunden.")

            # --- JETZT IN BEIDE DATENBANKEN SPEICHERN ---

            # A. LOKAL (SQLite)
            conn_local = sqlite3.connect(DB_NAME_LOCAL)
            # Löschen verhindert Doppeleinträge der aktuellen Saison
            conn_local.execute("DELETE FROM suenderkartei WHERE saison = ?", (saison_name,))
            df.to_sql("suenderkartei", conn_local, if_exists="append", index=False)
            conn_local.close()
            print("✅ Lokale DB (bundesliga.db) aktualisiert.")

            # B. CLOUD (Supabase)
            engine_cloud = create_engine(DB_URL_CLOUD)
            with engine_cloud.begin() as conn:
                conn.execute(text("DELETE FROM suenderkartei WHERE saison = :s"), {"s": saison_name})
                df.to_sql("suenderkartei", conn, if_exists="append", index=False)
            print("✅ Cloud DB (Supabase) aktualisiert.")

        else:
            print(f"⚠️ Fehler {response.status_code}")
            
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    update_suender()