#!/usr/bin/env python3
# coding: utf-8

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import text
from datetime import datetime

# Wir verwenden hier kein lokales SQLITE mehr, sondern die PostgreSQL-Verbindung von Supabase.
# Die Zugangsdaten werden sicher aus den Streamlit Secrets (Einstellungen) geladen.

# ==========================================
# 1. DATENBANK-VERBINDUNG & SETUP
# ==========================================

def get_conn():
    """Erstellt eine Verbindung zur PostgreSQL-Datenbank in der Cloud."""
    return st.connection("postgresql", type="sql")

def load_data_from_db():
    """Lädt die Spieldaten aus der Online-Datenbank in einen Pandas-Datensatz."""
    conn = get_conn()
    # Wir setzen die Gültigkeitsdauer des Zwischenspeichers (ttl) auf 0, 
    # damit wir immer die aktuellsten Ergebnisse direkt aus der Datenbank erhalten.
    df = conn.query("SELECT * FROM spiele", ttl=0)
    
    if df.empty:
        return pd.DataFrame()
    
    # Spaltennamen normalisieren (Leerzeichen entfernen und Kleinschreibung erzwingen)
    df.columns = df.columns.str.strip().str.lower()
    
    # Falls die Spaltennamen in der Datenbank Englisch sind, benennen wir sie um
    df = df.rename(columns={"home": "heim", "away": "gast"})
    
    # Korrektur für den Vereinsnamen MSV Duisburg (historische Bedingung)
    def rename_msv(row, team_col):
        team_name = str(row[team_col])
        if team_name == "Meidericher SV" and row["saison"] >= "1966/67":
            return "MSV Duisburg"
        return team_name

    df["heim"] = df.apply(lambda r: rename_msv(r, "heim"), axis=1)
    df["gast"] = df.apply(lambda r: rename_msv(r, "gast"), axis=1)
    
    return df

# ==========================================
# 2. TIPPSPIEL LOGIK (SUPABASE OPTIMIERT)
# ==========================================

def save_tipp(user, saison, spieltag, heim, gast, th, tg):
    """Speichert einen einzelnen Tipp in der Supabase-Datenbank mit Fehlerprüfung."""
    try:
        conn = get_conn()
        with conn.session as session:
            sql = text("""
                INSERT INTO tipps ("user", saison, spieltag, heim, gast, tipp_heim, tipp_gast, punkte)
                VALUES (:u, :s, :st, :h, :g, :th, :tg, :p)
            """)
            session.execute(sql, {
                "u": user, "s": saison, "st": spieltag, 
                "h": heim, "g": gast, "th": th, "tg": tg, "p": 0
            })
            session.commit()
    except Exception as e:
        # Dies zeigt uns in der App sofort an, wenn Supabase den Zugriff verweigert
        st.error(f"Datenbank-Fehler beim Speichern von {heim} vs {gast}: {e}")

def evaluate_tipps(df_spiele, user):
    """Vergleicht Tipps mit echten Ergebnissen und aktualisiert die Punkte in der DB."""
    conn = get_conn()
    try:
        with conn.session as session:
            # Wir holen nur Tipps, die noch 0 Punkte haben (ungewertet)
            sql_tipps = text('SELECT * FROM tipps WHERE "user" = :u AND punkte = 0')
            tipps = conn.query(sql_tipps, params={"u": user}, ttl=0)
            
            for _, tipp in tipps.iterrows():
                # Finde das echte Ergebnis im übergebenen DataFrame
                match = df_spiele[
                    (df_spiele['saison'] == tipp['saison']) & 
                    (df_spiele['heim'] == tipp['heim']) & 
                    (df_spiele['gast'] == tipp['gast'])
                ]
                
                if not match.empty and pd.notna(match.iloc[0]['tore_heim']):
                    t_h_echt = int(match.iloc[0]['tore_heim'])
                    t_g_echt = int(match.iloc[0]['tore_gast'])
                    t_h_tipp = int(tipp['tipp_heim'])
                    t_g_tipp = int(tipp['tipp_gast'])
                    
                    pkt = 0
                    if t_h_echt == t_h_tipp and t_g_echt == t_g_tipp:
                        pkt = 3  # Volltreffer
                    elif (t_h_echt - t_g_echt) == (t_h_tipp - t_g_tipp):
                        pkt = 2  # Differenz
                    elif (t_h_echt > t_g_echt and t_h_tipp > t_g_tipp) or \
                         (t_h_echt < t_g_echt and t_h_tipp < t_g_tipp):
                        pkt = 1  # Tendenz
                    
                    if pkt > 0:
                        sql_update = text('UPDATE tipps SET punkte = :p WHERE id = :tid')
                        session.execute(sql_update, {"p": pkt, "tid": tipp['id']})
            session.commit()
    except Exception as e:
        st.error(f"Fehler bei der Punkteberechnung: {e}")

# ==========================================
# 3. HILFSFUNKTIONEN & BERECHNUNGEN
# ==========================================

@st.cache_data
def calculate_table(df, saison):
    """Berechnet die Bundesliga-Tabelle für eine bestimmte Saison."""
    df_saison = df[df["saison"] == saison].copy()
    if df_saison.empty:
        return pd.DataFrame()
    
    df_saison = df_saison.dropna(subset=["tore_heim", "tore_gast"])
    teams = pd.unique(df_saison[["heim", "gast"]].values.ravel("K"))
    statistik = {team: {'Spiele': 0, 'S': 0, 'U': 0, 'N': 0, 'T': 0, 'G': 0, 'Punkte': 0} for team in teams}

    for _, row in df_saison.iterrows():
        h, g = row['heim'], row['gast']
        try:
            th, tg = int(row['tore_heim']), int(row['tore_gast'])
            statistik[h]['Spiele'] += 1
            statistik[g]['Spiele'] += 1
            statistik[h]['T'] += th
            statistik[h]['G'] += tg
            statistik[g]['T'] += tg
            statistik[g]['G'] += th
            
            if th > tg:
                statistik[h]['S'] += 1; statistik[h]['Punkte'] += 3; statistik[g]['N'] += 1
            elif th < tg:
                statistik[g]['S'] += 1; statistik[g]['Punkte'] += 3; statistik[h]['N'] += 1
            else:
                statistik[h]['U'] += 1; statistik[h]['Punkte'] += 1; statistik[g]['U'] += 1; statistik[g]['Punkte'] += 1
        except:
            continue

    tabelle = pd.DataFrame.from_dict(statistik, orient='index').reset_index().rename(columns={'index': 'Team'})
    tabelle['Diff'] = tabelle['T'] - tabelle['G']
    tabelle = tabelle.sort_values(by=['Punkte', 'Diff', 'T'], ascending=False).reset_index(drop=True)
    tabelle.insert(0, 'Platz', range(1, len(tabelle) + 1))
    return tabelle

@st.cache_data
def compute_ewige_tabelle(df):
    """Erstellt die Ewige Tabelle über alle verfügbaren Saisons hinweg."""
    if df.empty:
        return pd.DataFrame()
    
    df_lokal = df.dropna(subset=["tore_heim", "tore_gast"]).copy()
    heim_statistik = df_lokal.rename(columns={"heim": "Team", "tore_heim": "GF", "tore_gast": "GA"})[["Team", "GF", "GA"]]
    gast_statistik = df_lokal.rename(columns={"gast": "Team", "tore_gast": "GF", "tore_heim": "GA"})[["Team", "GF", "GA"]]
    
    alle_spiele = pd.concat([heim_statistik, gast_statistik])
    alle_spiele['P'] = 0; alle_spiele['S'] = 0; alle_spiele['U'] = 0; alle_spiele['N'] = 0
    
    alle_spiele.loc[alle_spiele['GF'] > alle_spiele['GA'], ['P', 'S']] = [3, 1]
    alle_spiele.loc[alle_spiele['GF'] == alle_spiele['GA'], ['P', 'U']] = [1, 1]
    alle_spiele.loc[alle_spiele['GF'] < alle_spiele['GA'], ['N']] = 1
    
    ewige = alle_spiele.groupby("Team").agg(
        Spiele=('Team', 'size'), S=('S', 'sum'), U=('U', 'sum'),
        N=('N', 'sum'), T=('GF', 'sum'), G=('GA', 'sum'), Punkte=('P', 'sum')
    ).reset_index()
    
    ewige = ewige.sort_values(by=["Punkte", "T"], ascending=False).reset_index(drop=True)
    ewige.insert(0, "Platz", range(1, len(ewige) + 1))
    return ewige

# ==========================================
# 4. TABELLEN-STYLING (CSS)
# ==========================================

def display_styled_table(df, type="standard"):
    """Formatiert die Tabellenausgabe mit HTML und CSS für eine bessere Optik."""
    html = df.to_html(index=False, classes='mystyle')
    css = """<style>
        .mystyle { width: 100%; border-collapse: collapse; color: black !important; }
        .mystyle th { background-color: #D3D3D3 !important; color: black !important; padding: 10px; border: 1px solid #ddd; text-align: center !important; }
        .mystyle td { padding: 8px; border: 1px solid #ddd; background-color: white !important; color: black !important; text-align: center !important; }
        .mystyle tr:nth-child(even) td { background-color: #f9f9f9 !important; }
    </style>"""
    st.markdown(css, unsafe_allow_html=True)
    st.write(html, unsafe_allow_html=True)

# ==========================================
# 5. SEITEN-INHALTE
# ==========================================

def show_startseite():
    st.markdown("<h1 style='text-align: center; color: darkred;'>⚽Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)

def show_spieltag_ansicht(df):
    seasons = sorted(df["saison"].unique(), reverse=True)
    saison_auswahl = st.sidebar.selectbox("Saison für Spieltage", seasons, key="view_saison")
    df_saison = df[df["saison"] == saison_auswahl]
    gespielte_spiele = df_saison.dropna(subset=["tore_heim", "tore_gast"])
    letzter_spieltag = int(gespielte_spiele["spieltag"].max()) if not gespielte_spiele.empty else 1
    
    spieltag_auswahl = st.sidebar.selectbox("Spieltag wählen", list(range(1, 35)), index=int(letzter_spieltag) - 1)
    st.markdown(f"<h3 style='text-align: center;'>Ergebnisse {spieltag_auswahl}. Spieltag ({saison_auswahl})</h3>", unsafe_allow_html=True)
    
    spiele_des_tages = df[(df["saison"] == saison_auswahl) & (df["spieltag"] == spieltag_auswahl)].copy()
    if not spiele_des_tages.empty:
        anzeige_df = pd.DataFrame()
        anzeige_df['Heim'] = spiele_des_tages['heim']
        anzeige_df['Ergebnis'] = spiele_des_tages.apply(lambda r: f"{int(r['tore_heim'])} : {int(r['tore_gast'])}" if pd.notna(r['tore_heim']) else "vs", axis=1)
        anzeige_df['Gast'] = spiele_des_tages['gast']
        display_styled_table(anzeige_df)

def show_tippspiel(df):
    """Die Seite für das Tippspiel - Robust ohne st.form."""
    st.title("🎯 Tippspiel")
    
    aktuelle_saison = sorted(df["saison"].unique(), reverse=True)[0]
    
    # Filter für Spiele ohne Ergebnis (NaN)
    zukunft_spiele = df[(df['saison'] == aktuelle_saison) & (df['tore_heim'].isna())].copy()
    
    if zukunft_spiele.empty:
        st.info("Keine offenen Spiele zum Tippen gefunden.")
        return

    spieltag_tippen = st.selectbox("Wähle den Spieltag:", sorted(zukunft_spiele['spieltag'].unique()))
    spiele_auswahl = zukunft_spiele[zukunft_spiele['spieltag'] == spieltag_tippen]

    st.subheader(f"Tipps für Spieltag {spieltag_tippen}")
    
    # Wir speichern die Eingaben direkt in einem Dictionary
    aktuelle_eingaben = {}
    
    for idx, zeile in spiele_auswahl.iterrows():
        cols = st.columns([3, 1, 1])
        cols[0].write(f"**{zeile['heim']}** - **{zeile['gast']}**")
        h_tipp = cols[1].number_input("H", 0, 20, 0, key=f"h_{idx}")
        g_tipp = cols[2].number_input("G", 0, 20, 0, key=f"g_{idx}")
        aktuelle_eingaben[idx] = (h_tipp, g_tipp, zeile['heim'], zeile['gast'])
    
    nutzer_name = st.text_input("Dein Name:", key="user_name")
    
    if st.button("🚀 Tipps in Cloud speichern"):
        if not nutzer_name.strip():
            st.error("Bitte gib einen Namen ein!")
        else:
            try:
                # Hier rufen wir die Speicherfunktion für jeden Tipp auf
                for idx, (th, tg, h, g) in aktuelle_eingaben.items():
                    save_tipp(nutzer_name.strip(), aktuelle_saison, spieltag_tippen, h, g, th, tg)
                
                st.success(f"✅ Tipps für {nutzer_name} wurden gespeichert!")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Fehler: {e}")

    st.divider()
    st.subheader("Meine Punkte")
    auswertung_nutzer = st.text_input("Name suchen:", key="view_res")
    if auswertung_nutzer.strip():
        evaluate_tipps(df, auswertung_nutzer.strip())
        conn = get_conn()
        sql = text('SELECT spieltag as "SP", heim, gast, tipp_heim || \':\' || tipp_gast as "Tipp", punkte FROM tipps WHERE "user" = :u')
        res = conn.query(sql, params={"u": auswertung_nutzer.strip()}, ttl=0)
        st.dataframe(res)

# ==========================================
# 6. HAUPTPROGRAMM (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="Bundesliga Cloud Dashboard", layout="wide")
    
    # Laden der Daten von Supabase
    df = load_data_from_db()
    if df.empty:
        st.warning("Keine Daten in der Cloud-Datenbank gefunden.")
        return
    
    saisons = sorted(df["saison"].unique(), reverse=True)
    seite = st.sidebar.radio("Menü", ["Startseite", "Spieltage", "Saisontabelle", "Ewige Tabelle", "Tippspiel"])

    if seite == "Startseite":
        show_startseite()
    elif seite == "Spieltage":
        show_spieltag_ansicht(df)
    elif seite == "Saisontabelle":
        saison_wahl = st.sidebar.selectbox("Saison wählen", saisons)
        st.title(f"Tabelle Saison {saison_wahl}")
        display_styled_table(calculate_table(df, saison_wahl))
    elif seite == "Ewige Tabelle":
        st.title("Ewige Tabelle")
        display_styled_table(compute_ewige_tabelle(df))
    elif seite == "Tippspiel":
        show_tippspiel(df)

if __name__ == "__main__":
    main()