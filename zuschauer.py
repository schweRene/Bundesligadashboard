import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine, text
import sqlite3


# --- KONFIGURATION ---
DB_NAME_LOCAL = "bundesliga.db"
DB_URL_CLOUD = "postgresql://postgres.scspxyixfumfhfkodsit:zz2r9OSjV8L@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
SAISON_URL_JAHR = "2026"  # fussballdaten.de nutzt das Endjahr in der URL
SAISON_LABEL = "2025/26"

# Deine Team-Map zur Bereinigung
TEAM_MAP = {
    "Bremen": "SV Werder Bremen", "Dortmund": "Borussia Dortmund",
    "Frankfurt": "Eintracht Frankfurt", "Nürnberg": "1. FC Nürnberg",
    "Braunschweig": "Eintracht Braunschweig", "Karlsruhe": "Karlsruher SC",
    "TSV 1860": "TSV 1860 München", "Münster": "Preußen Münster",
    "Hamburg": "Hamburger SV", "Kaiserslautern": "1.FC Kaiserslautern",
    "K'lautern": "1.FC Kaiserslautern", "1. FC Kaiserslautern": "1.FC Kaiserslautern",
    "Meidericher SV": "MSV Duisburg", "Duisburg": "MSV Duisburg", "Meiderich": "Meidericher SV",
    "Saarbrücken": "1. FC Saarbrücken", "Schalke": "FC Schalke 04",
    "Hertha": "Hertha BSC", "Hannover": "Hannover 96",
    "Neunkirchen": "Borussia Neunkirchen", "Tasmania": "Tasmania Berlin",
    "Essen": "Rot-Weiss Essen", "Offenbach": "Kickers Offenbach",
    "Leipzig": "RB Leipzig", "Oberhausen": "Rot-Weiß Oberhausen",
    "Bielefeld": "Arminia Bielefeld", "Uerdingen": "Bayer 05 Uerdingen",
    "Wattenscheid": "SG Wattenscheid 09", "St. Pauli": "FC St. Pauli",
    "Homburg": "FC 08 Homburg", "Stuttg. Kickers": "Stuttgarter Kickers",
    "Dresden": "Dynamo Dresden", "Rostock": "Hansa Rostock",
    "Düsseldorf": "Fortuna Düsseldorf", "Unterhaching": "SpVgg Unterhaching",
    "Cottbus": "Energie Cottbus", "Fürth": "SpVgg Greuther Fürth",
    "Paderborn": "SC Paderborn 07", "Ingolstadt": "FC Ingolstadt 04",
    "Darmstadt": "SV Darmstadt 98", "Heidenheim": "1. FC Heidenheim",
    "Bayern": "FC Bayern München", "Leverkusen": "Bayer 04 Leverkusen",
    "Gladbach": "Borussia Mönchengladbach", "Stuttgart": "VfB Stuttgart",
    "Augsburg": "1.FC Augsburg", "Mainz": "FSV Mainz 05",
    "Wolfsburg": "VfL Wolfsburg", "Hoffenheim": "TSG Hoffenheim",
    "Freiburg": "SC Freiburg", "Union Berlin": "1. FC Union Berlin",
    "Köln": "1. FC Köln", "Bochum": "VfL Bochum", "Kiel": "Holstein Kiel",
    "M'gladbach": "Borussia Mönchengladbach"
}

def clean_to_int(val):
    if not val: return 0
    s = str(val).split(',')[0].replace(".", "").strip()
    return int(s) if s.isdigit() else 0

def update_zuschauer():
    scraper = cloudscraper.create_scraper()
    url = f"https://www.fussballdaten.de/bundesliga/{SAISON_URL_JAHR}/zuschauer/"
    
    print(f"Scrape aktuelle Zuschauerzahlen ({SAISON_LABEL})...")
    
    try:
        response = scraper.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")
        if not table: return

        new_data = []
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) >= 5:
                verein_raw = cols[1].text.strip()
                verein = next((v for k, v in TEAM_MAP.items() if k in verein_raw), verein_raw)
                
                new_data.append({
                    "saison": SAISON_LABEL,
                    "platz": int(cols[0].text.strip().replace(".", "")),
                    "verein": verein,
                    "schnitt": clean_to_int(cols[2].text.strip()),
                    "gesamt": clean_to_int(cols[4].text.strip())
                })

        df = pd.DataFrame(new_data)

        # --- A. LOKAL UPDATE ---
        conn_l = sqlite3.connect(DB_NAME_LOCAL)
        # Erst alte Daten der Saison löschen
        conn_l.execute("DELETE FROM zuschauer WHERE saison = ?", (SAISON_LABEL,))
        df.to_sql('zuschauer', conn_l, if_exists='append', index=False)
        conn_l.commit()
        conn_l.close()
        print("✅ Lokale DB aktualisiert.")

        # --- B. CLOUD UPDATE ---
        engine_c = create_engine(DB_URL_CLOUD)
        with engine_c.begin() as conn_c:
            conn_c.execute(text("DELETE FROM zuschauer WHERE saison = :s"), {"s": SAISON_LABEL})
            df.to_sql('zuschauer', conn_c, if_exists='append', index=False)
        print("✅ Cloud DB aktualisiert.")

    except Exception as e:
        print(f"❌ Fehler beim Zuschauer-Update: {e}")

if __name__ == "__main__":
    update_zuschauer()