#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
import sqlite3
import re
import os

# === Konfig === bis bundesliga_1981 bereits hochgeladen in DB
CSV_FILES = [
    {"file": "bundesliga_1964.csv", "saison": "1963/64"},
    {"file": "bundesliga_1965.csv", "saison": "1964/65"},
    {"file": "bundesliga_1966.csv", "saison": "1965/66"},
    {"file": "bundesliga_1967.csv", "saison": "1966/67"},
    {"file": "bundesliga_1968.csv", "saison": "1967/68"},
    {"file": "bundesliga_1969.csv", "saison": "1968/69"},
    {"file": "bundesliga_1970.csv", "saison": "1969/70"},
    {"file": "bundesliga_1971.csv", "saison": "1970/71"},
    {"file": "bundesliga_1972.csv", "saison": "1971/72"},
    {"file": "bundesliga_1973.csv", "saison": "1972/73"},
    {"file": "bundesliga_1974.csv", "saison": "1973/74"},
    {"file": "bundesliga_1975.csv", "saison": "1974/75"},
    {"file": "bundesliga_1976.csv", "saison": "1975/76"},
    {"file": "bundesliga_1977.csv", "saison": "1976/77"},
    {"file": "bundesliga_1978.csv", "saison": "1977/78"},
    {"file": "bundesliga_1979.csv", "saison": "1978/79"},
    {"file": "bundesliga_1980.csv", "saison": "1979/80"},
    {"file": "bundesliga_1981.csv", "saison": "1980/81"},
    {"file": "bundesliga_1982.csv", "saison": "1981/82"},
    {"file": "bundesliga_1983.csv", "saison": "1982/83"},
    {"file": "bundesliga_1984.csv", "saison": "1983/84"},
    {"file": "bundesliga_1985.csv", "saison": "1984/85"},
    {"file": "bundesliga_1986.csv", "saison": "1985/86"},
    {"file": "bundesliga_1987.csv", "saison": "1986/87"},
    {"file": "bundesliga_1988.csv", "saison": "1987/88"},
    {"file": "bundesliga_1989.csv", "saison": "1988/89"},
    {"file": "bundesliga_1990.csv", "saison": "1989/90"},
    {"file": "bundesliga_1991.csv", "saison": "1990/91"},
    {"file": "bundesliga_1992.csv", "saison": "1991/92"},
    {"file": "bundesliga_1993.csv", "saison": "1992/93"},
    {"file": "bundesliga_1994.csv", "saison": "1993/94"},
    {"file": "bundesliga_1995.csv", "saison": "1994/95"},
    {"file": "bundesliga_1996.csv", "saison": "1995/96"},
    {"file": "bundesliga_1997.csv", "saison": "1996/97"},
    {"file": "bundesliga_1998.csv", "saison": "1997/98"},
    {"file": "bundesliga_1999.csv", "saison": "1998/99"},
    {"file": "bundesliga_2000.csv", "saison": "1999/00"},
    {"file": "bundesliga_2001.csv", "saison": "2000/01"},
    {"file": "bundesliga_2002.csv", "saison": "2001/02"},
    {"file": "bundesliga_2003.csv", "saison": "2002/03"},
    {"file": "bundesliga_2004.csv", "saison": "2003/04"},
    {"file": "bundesliga_2005.csv", "saison": "2004/05"},
    {"file": "bundesliga_2006.csv", "saison": "2005/06"},
    {"file": "bundesliga_2007.csv", "saison": "2006/07"},
    {"file": "bundesliga_2008.csv", "saison": "2007/08"},
    {"file": "bundesliga_2009.csv", "saison": "2008/09"},
    {"file": "bundesliga_2010.csv", "saison": "2009/10"},
    {"file": "bundesliga_2011.csv", "saison": "2010/11"},
    {"file": "bundesliga_2012.csv", "saison": "2011/12"},
    {"file": "bundesliga_2013.csv", "saison": "2012/13"},
    {"file": "bundesliga_2014.csv", "saison": "2013/14"},
    {"file": "bundesliga_2015.csv", "saison": "2014/15"},
    {"file": "bundesliga_2016.csv", "saison": "2015/16"},
    {"file": "bundesliga_2017.csv", "saison": "2016/17"},
    {"file": "bundesliga_2018.csv", "saison": "2017/18"},
    {"file": "bundesliga_2019.csv", "saison": "2018/19"},
    {"file": "bundesliga_2020.csv", "saison": "2019/20"},
    {"file": "bundesliga_2021.csv", "saison": "2020/21"},
    {"file": "bundesliga_2022.csv", "saison": "2021/22"},
    {"file": "bundesliga_2023.csv", "saison": "2022/23"},
    {"file": "bundesliga_2024.csv", "saison": "2023/24"},
    {"file": "bundesliga_2025.csv", "saison": "2024/25"}   
]
DB_FILE = "bundesliga.db"

# === Hilfsfunktionen ===

def normalize_team_name(team):
    """Entfernt Platzierungen in Klammern wie '(6.)' oder '(11.)' aus Teamnamen."""
    if not isinstance(team, str):
        return team
    team = re.sub(r'\s*\(\d+\.\)\s*', '', team)
    return team.strip()

def normalize_team_names(df, saison):
    """Standardisiert Teamnamen (z.B. K'lautern -> 1.FC Kaiserslautern)."""
    # Zuerst die Klammern entfernen (deine Logik)
    df["home"] = df["home"].apply(normalize_team_name)
    df["away"] = df["away"].apply(normalize_team_name)
    
    replacements = {
        "Bremen": "SV Werder Bremen",
        "Dortmund": "Borussia Dortmund",
        "K'lautern": "1.FC Kaiserslautern",
        "1. FC Kaiserslautern": "1.FC Kaiserslautern",
        "Frankfurt": "Eintracht Frankfurt",
        "Nürnberg": "1. FC Nürnberg",
        "Braunschweig": "Eintracht Braunschweig",
        "Karlsruhe": "Karlsruher SC",
        "TSV 1860": "TSV 1860 München",
        "Münster": "Preußen Münster",
        "Hamburg": "Hamburger SV",
        "Köln": "1. FC Köln",
        "Stuttgart": "VfB Stuttgart",
        "Saarbrücken": "1. FC Saarbrücken",
        "Schalke": "FC Schalke 04",
        "M'gladbach": "Borussia Mönchengladbach",
        "Bayern": "FC Bayern München",
        "Düsseldorf": "Fortuna Düsseldorf",
        "Offenbach": "Kickers Offenbach",
        "Wuppertal": "Wuppertaler SV",
        "Bielefeld": "Arminia Bielefeld",
        "Tasmania": "Tasmania Berlin",
        "Mannheim": "Waldhof Mannheim",
        "Leverkusen": "Bayer 04 Leverkusen",
        "St. Kickers": "Stuttgarter Kickers",
        "Uerdingen": "KFC Uerdingen",
        "Wattenscheid": "SG Wattenscheid 09",
        "TB Berlin": "Tennis Borussia Berlin",
        "Duisburg": "MSV Duisburg",
        "RW Essen": "Rot Weiss Essen",
        "Dresden": "SG Dynamo Dresden",
        "Freiburg": "SC Freiburg",
        "Rostock": "FC Hansa Rostock",
        "St. Pauli": "FC St Pauli",
        "Wolfsburg": "VfL Wolfsburg",
        "Cottbus": "Energie Cottbus",
        "Hoffenheim": "TSG Hoffenheim",
        "Hannover": "Hannover 96",
        "Hannover 96": "Hannover 96",
        "Paderborn": "SC Paderborn 07",
        "Ingolstadt": "FC Ingolstadt 04",
        "Darmstadt": "SV Darmstadt 98",
        "Leipzig": "RB Leipzig",
        "Union Berlin": "1. FC Union Berlin",
        "Heidenheim": "1. FC Heidenheim",
        "Holstein Kiel": "Holstein Kiel",
        "Augsburg": "1.FC Augsburg",
        "Mainz": "FSV Mainz 05",
        "Meidericher SV": "MSV Duisburg" if saison >= "1966/67" else "Meidericher SV",
        "Neunkirchen": "Borussia Neunkirchen",
        "Meiderich": "MSV Duisburg" if saison >= "1966/67" else "Meidericher SV",
        "Homburg": "FC 08 Homburg",
        "-:- Schalke": "FC Schalke 04",
        "Fürth": "SpVgg Greuther Fürth",
        "Abbruch M'gladbach": "Borussia Mönchengladbach",
        "Wertung VfL Bochum": "VfL Bochum",
        "-:- Bremen": "SV Werder Bremen",
        "-:- Bayern": "FC Bayern München",
        "Oberhausen": "Rot Weiss Oberhausen",
        "-:- Düsseldorf": "Fortuna Düsseldorf",
        "-:- Frankfurt": "Eintracht Frankfurt",
        "Ulm": "SSV Ulm 1846",
        "Aachen": "Alemania Aachen",
        "Schalke 04": "FC Schalke 04",
    }
    df["home"] = df["home"].replace(replacements)
    df["away"] = df["away"].replace(replacements)
    return df

def create_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Tabelle mit Spieltag und erlaubten NULL-Werten bei Toren
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spiele (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spieltag INTEGER,
            saison TEXT NOT NULL,
            heim TEXT NOT NULL,
            gast TEXT NOT NULL,
            tore_heim INTEGER,
            tore_gast INTEGER,
            UNIQUE(saison, spieltag, heim, gast) --Verhindert Duplikate
        )
    """)
    conn.commit()
    conn.close()

def prepare_data(file_path, saison):
    if not os.path.exists(file_path):
        print(f"Datei nicht gefunden: {file_path}")
        return None
    
    df = pd.read_csv(file_path)
    
    # Spaltennamen auf Kleinbuchstaben vereinheitlichen für interne Logik
    df.columns = [c.lower() for c in df.columns]
    
    # 1. Teamnamen normalisieren
    df = normalize_team_names(df, saison)
    
    # 2. Spieltag prüfen (falls nicht da, 0 setzen)
    if 'spieltag' not in df.columns:
        df['spieltag'] = 0
    
    # 3. Tore-Logik: Erzeugt NULL (None) bei "-:-"
    def split_res(res):
        res_str = str(res).strip()
        if res_str == "-:-" or ":" not in res_str or len(res_str) > 5:
            return None, None
        try:
            h, g = res_str.split(':')
            return int(h), int(g)
        except:
            return None, None

    # Splitten (wir nutzen result, da wir oben df.columns.lower() gemacht haben)
    df['t_h'], df['t_g'] = zip(*df['result'].apply(split_res))
    
    # Saison Spalte
    df['saison_val'] = saison
    
    # Exakt die Spalten für das INSERT zurückgeben
    return df[['spieltag', 'saison_val', 'home', 'away', 't_h', 't_g']]

def import_to_db(df):
    if df is None: return 0
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Umwandlung in Liste von Tupeln
    data_to_insert = [tuple(x) for x in df.values]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO spiele (spieltag, saison, heim, gast, tore_heim, tore_gast)
        VALUES (?, ?, ?, ?, ?, ?)
    """, data_to_insert)
    
    inserted = cursor.rowcount
    conn.commit()
    conn.close()
    return inserted

def main():
    # Wichtig: Falls du das Schema ändern willst, lösche die DB Datei vorher manuell
    create_database()
    total_inserted = 0
    
    for entry in CSV_FILES:
        print(f"Verarbeite {entry['file']}...")
        df_prepared = prepare_data(entry["file"], entry["saison"])
        if df_prepared is not None:
            inserted = import_to_db(df_prepared)
            total_inserted += inserted
            
    print(f"\nFertig! Insgesamt eingefügte Spiele: {total_inserted}")

if __name__ == "__main__":
    main()