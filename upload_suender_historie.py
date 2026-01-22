import pandas as pd
import sqlite3
from sqlalchemy import create_engine, text

#Konfiguration 
CSV_FILE = "bundesliga_suender_historie.csv"
DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
DB_NAME_LOCAL = "bundesliga.db"

def upload():
    df = pd.read_csv(CSV_FILE)

    #1. Cloud (Supabase)
    print("📤 Lade Historie in die Cloud...")
    engine_cloud = create_engine(DB_URL_CLOUD)
    with engine_cloud.begin() as conn:
        df.to_sql("suenderkartei", conn, if_exists="replace", index=False)

    #2. Lokal (SQLite)
    print("📥 Lade Historie in lokale DB...")
    conn_local = sqlite3.connect(DB_NAME_LOCAL)
    df.to_sql("suenderkartei", conn_local, if_exists="replace", index=False)
    conn_local.close

    print("✅ Historische Daten in beiden DBs gespeichert!")

if __name__ == "__main__":
    upload()
