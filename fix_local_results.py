import sqlite3
import pandas as pd
from sqlalchemy import create_engine

DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
engine_cloud = create_engine(DB_URL_CLOUD)

def rescue_games():
    print("🚑 Rettung der Spiele-Historie aus der Cloud...")
    # Lade ALLE Spiele aus der Cloud (auch die alten Saisons)
    df_all_games = pd.read_sql("SELECT * FROM spiele", engine_cloud)
    
    conn_local = sqlite3.connect("bundesliga.db")
    # Überschreibe die kaputte lokale Tabelle mit der kompletten Historie
    df_all_games.to_sql("spiele", conn_local, if_exists="replace", index=False)
    conn_local.close()
    print(f"✅ {len(df_all_games)} Spiele wieder lokal hergestellt.")

if __name__ == "__main__":
    rescue_games()