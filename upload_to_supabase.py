import sqlite3
import pandas as pd
from sqlalchemy import create_engine

# 1. Verbindung zur LOKALEN Datenbank (dein PC)
local_conn = sqlite3.connect('bundesliga.db')
df_spiele = pd.read_sql_query("SELECT * FROM spiele", local_conn)

# 2. Verbindung zur ONLINE Datenbank (Supabase)

# Der Benutzername ist nicht mehr nur "postgres", 
# sondern "postgres.scspxyixfumfhfkodsit"
# Wir nehmen Port 5432 und den einfachen Benutzernamen "postgres"
# Versuchen wir es mit der direkten AWS-Adresse für Frankfurt
# Wir tauschen den Host gegen die direkte DB-Adresse aus
# Diese Adresse funktioniert auch mit deinem Internetanschluss (Port 5432)
supabase_url = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require"
engine = create_engine(supabase_url)

# 3. Daten hochladen
try:
    print("Starte Datentransfer zu Supabase...")
    # Wir laden die Spiele-Tabelle hoch
    df_spiele.to_sql('spiele', engine, if_exists='append', index=False)
    print("✅ Erfolg! Die Spieldaten wurden zu Supabase übertragen.")
except Exception as e:
    print(f"❌ Fehler beim Upload: {e}")
finally:
    local_conn.close()