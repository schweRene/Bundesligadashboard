import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

# Konfiguration
DB_NAME_LOCAL = "bundesliga.db"
DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
SAISON = "2025/26"

def repair_cloud():
    print(f"🚀 Starte Cloud-Reparatur...")
    
    # 1. Verbindung zur lokalen DB prüfen
    conn_local = sqlite3.connect(DB_NAME_LOCAL)
    
    # Check: Welche Tabellen gibt es lokal?
    cursor = conn_local.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tabellen = [t[0] for t in cursor.fetchall()]
    print(f"🔎 In lokaler DB gefunden: {tabellen}")

    if "spiele" not in tabellen:
        print(f"❌ FEHLER: Tabelle 'spiele' wurde in {DB_NAME_LOCAL} nicht gefunden!")
        conn_local.close()
        return

    # 2. Saubere Daten lokal lesen
    print(f"📥 Lese lokale Daten für Saison {SAISON}...")
    query = "SELECT * FROM spiele WHERE saison = ?"
    # Fix: params muss ein Tupel sein (SAISON,)
    df_local = pd.read_sql(query, conn_local, params=(SAISON,))
    conn_local.close()
    
    if df_local.empty:
        print("⚠️ Keine lokalen Daten für diese Saison gefunden.")
        return

    # 3. Verbindung zur Cloud
    engine_cloud = create_engine(DB_URL_CLOUD)
    print(f"📤 Übertrage {len(df_local)} Zeilen in die Cloud und korrigiere falsche Ergebnisse...")
    
    try:
        with engine_cloud.begin() as conn:
            for _, row in df_local.iterrows():
                sql = text("""
                    INSERT INTO spiele (saison, spieltag, heim, gast, tore_heim, tore_gast)
                    VALUES (:s, :st, :h, :g, :th, :tg)
                    ON CONFLICT (saison, spieltag, heim, gast) 
                    DO UPDATE SET 
                        tore_heim = EXCLUDED.tore_heim, 
                        tore_gast = EXCLUDED.tore_gast;
                """)
                
                # Konvertierung für saubere Übergabe (None für NULL)
                th = None if pd.isna(row['tore_heim']) else int(row['tore_heim'])
                tg = None if pd.isna(row['tore_gast']) else int(row['tore_gast'])
                
                conn.execute(sql, {
                    "s": row['saison'],
                    "st": int(row['spieltag']),
                    "h": row['heim'],
                    "g": row['gast'],
                    "th": th,
                    "tg": tg
                })
        print("✅ Cloud-Ergebnisse wurden erfolgreich korrigiert!")
    except Exception as e:
        print(f"❌ Fehler beim Cloud-Update: {e}")

if __name__ == "__main__":
    repair_cloud()