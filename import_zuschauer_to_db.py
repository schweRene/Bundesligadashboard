import pandas as pd
from sqlalchemy import create_engine, text

# Konfiguration
DB_NAME_LOCAL = "sqlite:///bundesliga.db"
DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"

def to_pure_int(val):
    """Wandelt '40.400' in 40400 um."""
    if pd.isna(val):
        return 0
    # Entfernt alle Punkte, damit nur die nackte Zahl übrig bleibt
    clean_val = str(val).replace(".", "").strip()
    return int(clean_val) if clean_val.isdigit() else 0

def run_import():
    print("📖 Lese saubere zuschauer.csv ein...")
    # Wir lesen alles als String ein, um volle Kontrolle über die Konvertierung zu haben
    df = pd.read_csv("zuschauer.csv", dtype=str)

    # Konvertierung der Zahlen-Spalten in echte Integer
    df['Schnitt'] = df['Schnitt'].apply(to_pure_int)
    df['Gesamt'] = df['Gesamt'].apply(to_pure_int)
    
    # Spaltennamen auf Kleinschreibung (für die DB-Kompatibilität)
    df.columns = [c.lower() for c in df.columns]

    engines = [
        ("Lokal (SQLite)", create_engine(DB_NAME_LOCAL)),
        ("Cloud (Postgres)", create_engine(DB_URL_CLOUD))
    ]

    for name, engine in engines:
        print(f"🚀 Übertrag läuft: {name}...")
        try:
            with engine.begin() as conn:
                # Tabelle leeren, um einen sauberen Neustart ohne Dubletten zu haben
                conn.execute(text("DELETE FROM zuschauer"))
                
                # Daten einfügen
                df.to_sql('zuschauer', conn, if_exists='append', index=False)
                
            print(f"✅ Fertig! {len(df)} Zeilen in {name} importiert.")
        except Exception as e:
            print(f"❌ Fehler bei {name}: {e}")

if __name__ == "__main__":
    run_import()