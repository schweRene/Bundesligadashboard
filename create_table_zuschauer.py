from sqlalchemy import create_engine, text

# Deine Zugangsdaten
DB_NAME_LOCAL = "sqlite:///bundesliga.db"
DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"

def setup_databases():
    engines = [
        ("Lokal (SQLite)", create_engine(DB_NAME_LOCAL)),
        ("Cloud (Postgres)", create_engine(DB_URL_CLOUD))
    ]

    for name, engine in engines:
        print(f"Prüfe {name}...")
        try:
            with engine.connect() as conn:
                # SQL-Befehl: Wir erstellen die Tabelle
                # Hinweis: In Postgres nutzen wir SERIAL, in SQLite wird daraus AUTOINCREMENT
                if "sqlite" in str(engine.url):
                    sql = """
                    CREATE TABLE IF NOT EXISTS zuschauer (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        saison TEXT,
                        platz INTEGER,
                        verein TEXT,
                        schnitt INTEGER,
                        gesamt INTEGER
                    );
                    """
                else:
                    sql = """
                    CREATE TABLE IF NOT EXISTS zuschauer (
                        id SERIAL PRIMARY KEY,
                        saison VARCHAR(10),
                        platz INTEGER,
                        verein VARCHAR(100),
                        schnitt INTEGER,
                        gesamt INTEGER
                    );
                    """
                
                conn.execute(text(sql))
                conn.commit() # Ganz wichtig für die Cloud!
                
                # Test-Abfrage: Existiert die Tabelle?
                if "sqlite" in str(engine.url):
                    check = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='zuschauer';")).fetchone()
                else:
                    check = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE tablename='zuschauer';")).fetchone()
                
                if check:
                    print(f"✅ Erfolg: Tabelle 'zuschauer' existiert jetzt in {name}.")
                else:
                    print(f"❌ Fehler: Tabelle wurde in {name} nicht gefunden.")

        except Exception as e:
            print(f"⚠️ Kritischer Fehler bei {name}: {e}")

if __name__ == "__main__":
    setup_databases()