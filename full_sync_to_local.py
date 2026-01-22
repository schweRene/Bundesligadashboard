import sqlite3
import pandas as pd
from sqlalchemy import create_engine

# Konfiguration
DB_NAME = "bundesliga.db"
DB_URL = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"

def full_master_sync():
    print("🚀 Starte VOLLSTÄNDIGEN Sync (Cloud -> Lokal)...")
    cloud_engine = create_engine(DB_URL)
    local_conn = sqlite3.connect(DB_NAME)

    try:
        # Liste aller Tabellen, die wir synchronisieren wollen
        tabellen = ["torschuetzen", "rekordspieler", "spiele", "tipps"]

        for tabelle in tabellen:
            print(f"📥 Synchronisiere Tabelle: {tabelle}...")
            try:
                # Daten aus Cloud laden
                query = f"SELECT * FROM {tabelle}"
                if tabelle == "spiele":
                    query += " WHERE saison = '2025/26'"
                
                df = pd.read_sql(query, cloud_engine)

                # Spezialbehandlung für Spiele (Zukunftsbereinigung)
                if tabelle == "spiele":
                    print("🧹 Bereinige Zukunftsdaten (Spieltag 25+)...")
                    df.loc[df['spieltag'] >= 25, ['tore_heim', 'tore_gast']] = None

                # In lokale SQLite schreiben
                df.to_sql(tabelle, local_conn, if_exists="replace", index=False)
                print(f"✅ {len(df)} Zeilen in '{tabelle}' übertragen.")
            
            except Exception as e:
                print(f"⚠️ Tabelle '{tabelle}' konnte nicht geladen werden: {e}")

        print("\n✨ Synchronisation abgeschlossen!")

    except Exception as e:
        print(f"❌ Kritischer Fehler beim Sync: {e}")
    finally:
        local_conn.close()
        print("Lokale Datenbank-Verbindung geschlossen.")

if __name__ == "__main__":
    full_master_sync()