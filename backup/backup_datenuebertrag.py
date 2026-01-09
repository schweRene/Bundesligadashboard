#!/usr/bin/env python3
# coding: utf-8
"""
Erstellt oder verwendet eine Dummy-Datenbank (dummy_bundesliga.db), normalisiert
bundesliga_1964.csv und bundesliga_1965.csv und importiert die Daten in die
spiele-Tabelle. Gibt den Inhalt im Terminal aus.
Entfernt Platzierungen in Klammern (z.B. '(6.)' oder '(11.)') und standardisiert Teamnamen.
"""

import pandas as pd
import sqlite3
import re
import os

# === Konfig ===
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
DB_FILE = "dummy_bundesliga.db"


# === Hilfsfunktionen ===
def normalize_team_name(team):
    """Entfernt Platzierungen in Klammern wie '(6.)' oder '(11.)' aus Teamnamen."""
    if not isinstance(team, str):
        return team
    team = re.sub(r'\s*\(\d+\.\)\s*', '', team)
    return team.strip()


def normalize_team_names(df, saison):
    """Standardisiert Teamnamen (z.B. K'lautern -> 1.FC Kaiserslautern)."""
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

def create_dummy_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Wir entfernen 'NOT NULL' bei tore_heim und tore_gast
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spiele (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spieltag INTEGER,
            saison TEXT NOT NULL,
            heim TEXT NOT NULL,
            gast TEXT NOT NULL,
            tore_heim INTEGER,  -- NOT NULL entfernt
            tore_gast INTEGER   -- NOT NULL entfernt
        )
    """)
    conn.commit()
    conn.close()

def prepare_data(csv_file, saison):
    """Lese CSV, normalisiere Daten und bereite für DB-Import vor."""
    try:
        df = pd.read_csv(csv_file)
        print(f"\nCSV {csv_file} geladen: {len(df)} Zeilen")
        print("Erste 5 Zeilen (vor Normalisierung):")
        print(df.head())
        expected_columns = ["spieltag", "home", "away", "result"]
        if not all(col in df.columns for col in expected_columns):
            raise ValueError(f"CSV muss Spalten {expected_columns} enthalten, gefunden: {df.columns.tolist()}")

        # Entferne Duplikate (streng: gleicher Spieltag, Teams, Ergebnis)
        df = df.drop_duplicates(subset=["spieltag", "home", "away", "result"], keep="first")
        print(f"Nach Entfernung von Duplikaten: {len(df)} Zeilen")

        # Normalisiere Teamnamen
        df["home"] = df["home"].apply(normalize_team_name)
        df["away"] = df["away"].apply(normalize_team_name)
        df = normalize_team_names(df, saison)

        # Prüfe ungültige Ergebnisse
        invalid_results = df[~df["result"].str.match(r'^\d+:\d+$', na=False)]
        if not invalid_results.empty:
            print(f"Ungültige Ergebnisse in {csv_file} gefunden:")
            print(invalid_results[["spieltag", "home", "away", "result"]])
        df = df[df["result"].str.match(r'^\d+:\d+$', na=False)]

        # Splitte Ergebnisse
        result_split = df["result"].str.split(":", expand=True)
        df["tore_heim"] = result_split[0].astype(int)
        df["tore_gast"] = result_split[1].astype(int)
        df["saison"] = saison
        df = df[["saison", "home", "away", "tore_heim", "tore_gast"]]

        print(f"\nErste 5 Zeilen von {csv_file} (nach Normalisierung):")
        print(df.head())
        return df
    except FileNotFoundError:
        print(f"Fehler: {csv_file} nicht gefunden!")
        return pd.DataFrame()
    except Exception as e:
        print(f"Fehler beim Verarbeiten der CSV {csv_file}: {e}")
        return pd.DataFrame()


def import_to_db(df, csv_file, saison):
    """Importiere normalisierte Daten in die spiele-Tabelle, bereinige alte Daten."""
    if df.empty:
        print(f"Keine Daten aus {csv_file} zum Importieren!")
        return 0
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Bereinige alte Daten für die Saison
        cursor.execute("DELETE FROM spiele WHERE saison = ?", (saison,))
        conn.commit()
        print(f"Alte Daten für Saison {saison} gelöscht.")

        inserted = 0
        for _, row in df.iterrows():
            cursor.execute("""
                SELECT COUNT(*) FROM spiele 
                WHERE saison = ? AND heim = ? AND gast = ? AND tore_heim = ? AND tore_gast = ?
            """, (row["saison"], row["home"], row["away"], row["tore_heim"], row["tore_gast"]))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO spiele (saison, heim, gast, tore_heim, tore_gast)
                    VALUES (?, ?, ?, ?, ?)
                """, (row["saison"], row["home"], row["away"], row["tore_heim"], row["tore_gast"]))
                inserted += 1
        conn.commit()
        print(f"Eingefügt: {inserted} Spiele aus {csv_file} in {DB_FILE} (Tabelle spiele)")

        # Prüfe Spiele pro Team
        df_check = pd.read_sql_query(f"""
            SELECT heim AS team, COUNT(*) AS spiele
            FROM spiele
            WHERE saison = ?
            GROUP BY heim
            UNION
            SELECT gast AS team, COUNT(*) AS spiele
            FROM spiele
            WHERE saison = ?
            GROUP BY gast
        """, conn, params=(saison, saison))
        team_spiele = df_check.groupby('team')['spiele'].sum().reset_index()
        expected_spiele = 30 if saison in ["1963/64", "1964/65"] else 34
        print(f"\nSpiele pro Team in Saison {saison}:")
        print(team_spiele)
        fehlerhafte_teams = team_spiele[team_spiele['spiele'] != expected_spiele]
        if not fehlerhafte_teams.empty:
            print(f"Fehlerhafte Teams in Saison {saison}:")
            print(fehlerhafte_teams)

        conn.close()
        return inserted
    except sqlite3.Error as e:
        print(f"Datenbankfehler beim Import von {csv_file}: {e}")
        return 0
    except Exception as e:
        print(f"Allgemeiner Fehler beim Import von {csv_file}: {e}")
        return 0


"""def print_db_content():
    Gibt den Inhalt der spiele-Tabelle im Terminal aus.
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM spiele")
        total_games = cursor.fetchone()[0]
        print(f"\nGesamtzahl der Spiele in spiele-Tabelle: {total_games}")
        cursor.execute("SELECT saison, COUNT(*) FROM spiele GROUP BY saison ORDER BY saison")
        saison_counts = cursor.fetchall()
        print("\nSpiele pro Saison:")
        for saison, count in saison_counts:
            print(f"Saison {saison}: {count} Spiele")
        for saison, _ in saison_counts:
            cursor.execute("SELECT * FROM spiele WHERE saison = ? LIMIT 5", (saison,))
            print(f"\nErste 5 Spiele in spiele-Tabelle (Saison {saison}):")
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    print(row)
            else:
                print(f"Keine Spiele für Saison {saison} gefunden.")
        conn.close()
    except sqlite3.Error as e:
        print(f"Datenbankfehler beim Auslesen: {e}")"""


def main():
    create_dummy_database()
    total_inserted = 0
    for csv in CSV_FILES:
        df = prepare_data(csv["file"], csv["saison"])
        total_inserted += import_to_db(df, csv["file"], csv["saison"])
    print(f"\nInsgesamt eingefügte Spiele: {total_inserted}")



if __name__ == "__main__":
    main()