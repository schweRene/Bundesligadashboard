#!/usr/bin/env python3
# coding: utf-8

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import text
from datetime import datetime

# ==========================================
# 1. DATENBANK-VERBINDUNG & SETUP
# ==========================================

def get_conn():
    """Erstellt eine Verbindung zur PostgreSQL-Datenbank in der Cloud."""
    return st.connection("postgresql", type="sql")

def load_data_from_db():
    """Lädt die Spieldaten aus der Online-Datenbank."""
    conn = get_conn()
    df = conn.query("SELECT * FROM spiele", ttl=0)
    
    if df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip().str.lower()
    
    # MSV Duisburg Korrektur
    def rename_msv(row, team_col):
        team_name = str(row[team_col])
        if team_name == "Meidericher SV" and row["saison"] >= "1966/67":
            return "MSV Duisburg"
        return team_name

    df["heim"] = df.apply(lambda r: rename_msv(r, "heim"), axis=1)
    df["gast"] = df.apply(lambda r: rename_msv(r, "gast"), axis=1)
    
    return df

# ==========================================
# 2. HILFSFUNKTIONEN FÜR TIPPSPIEL
# ==========================================

def save_tipp(user, saison, spieltag, heim, gast, th, tg):
    """Speichert einen einzelnen Tipp. Spalte 'punkte' wird weggelassen (bleibt NULL)."""
    conn = get_conn()
    with conn.session as session:
        # WICHTIG: Wir speichern KEINE Punkte beim INSERT
        sql = text("""
            INSERT INTO tipps ("user", saison, spieltag, heim, gast, tipp_heim, tipp_gast)
            VALUES (:u, :s, :st, :h, :g, :th, :tg)
        """)
        session.execute(sql, {
            "u": user, "s": saison, "st": int(spieltag), 
            "h": heim, "g": gast, "th": int(th), "tg": int(tg)
        })
        session.commit()

def evaluate_tipps(df_spiele, user):
    """Berechnet Punkte für offene Tipps (wo punkte IS NULL)."""
    conn = get_conn()
    try:
        with conn.session as session:
            # Wir suchen nur Tipps ohne Punkte
            sql_tipps = text('SELECT * FROM tipps WHERE "user" = :u AND punkte IS NULL')
            tipps = conn.query(sql_tipps, params={"u": user}, ttl=0)
            
            for _, tipp in tipps.iterrows():
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
                        pkt = 3
                    elif (t_h_echt - t_g_echt) == (t_h_tipp - t_g_tipp):
                        pkt = 2
                    elif (t_h_echt > t_g_echt and t_h_tipp > t_g_tipp) or \
                         (t_h_echt < t_g_echt and t_h_tipp < t_g_tipp):
                        pkt = 1
                    
                    # Hier wird die Punktzahl per UPDATE nachgetragen
                    session.execute(
                        text('UPDATE tipps SET punkte = :p WHERE id = :tid'),
                        {"p": pkt, "tid": tipp['id']}
                    )
            session.commit()
    except Exception as e:
        st.error(f"Fehler bei der Auswertung: {e}")

# ==========================================
# 3. TABELLEN-LOGIK
# ==========================================

def calculate_table(df, saison):
    df_saison = df[df["saison"] == saison].copy().dropna(subset=["tore_heim", "tore_gast"])
    if df_saison.empty: return pd.DataFrame()
    
    teams = pd.unique(df_saison[["heim", "gast"]].values.ravel("K"))
    statistik = {team: {'Spiele': 0, 'S': 0, 'U': 0, 'N': 0, 'T': 0, 'G': 0, 'Punkte': 0} for team in teams}
    
    for _, row in df_saison.iterrows():
        h, g, th, tg = row['heim'], row['gast'], int(row['tore_heim']), int(row['tore_gast'])
        statistik[h]['Spiele'] += 1; statistik[g]['Spiele'] += 1
        statistik[h]['T'] += th; statistik[h]['G'] += tg; statistik[g]['T'] += tg; statistik[g]['G'] += th
        if th > tg:
            statistik[h]['S'] += 1; statistik[h]['Punkte'] += 3; statistik[g]['N'] += 1
        elif th < tg:
            statistik[g]['S'] += 1; statistik[g]['Punkte'] += 3; statistik[h]['N'] += 1
        else:
            statistik[h]['U'] += 1; statistik[h]['Punkte'] += 1; statistik[g]['U'] += 1; statistik[g]['Punkte'] += 1
            
    tabelle = pd.DataFrame.from_dict(statistik, orient='index').reset_index().rename(columns={'index': 'Team'})
    tabelle['Diff'] = tabelle['T'] - tabelle['G']
    tabelle = tabelle.sort_values(by=['Punkte', 'Diff', 'T'], ascending=False).reset_index(drop=True)
    tabelle.insert(0, 'Platz', range(1, len(tabelle) + 1))
    return tabelle

# ==========================================
# 4. SEITEN-ANZEIGEN
# ==========================================

def show_startseite():
    st.title("⚽ Bundesliga Cloud Dashboard")
    st.write("Willkommen im Tippspiel!")

def show_tippspiel(df):
    st.title("🎯 Tippspiel")
    
    aktuelle_saison = sorted(df["saison"].unique(), reverse=True)[0]
    zukunft_spiele = df[(df['saison'] == aktuelle_saison) & (df['tore_heim'].isna())].copy()
    
    if zukunft_spiele.empty:
        st.info("Keine offenen Spiele zum Tippen verfügbar.")
        return

    spieltag_tippen = st.selectbox("Wähle den Spieltag:", sorted(zukunft_spiele['spieltag'].unique()))
    spiele_auswahl = zukunft_spiele[zukunft_spiele['spieltag'] == spieltag_tippen]

    # Daten sammeln (ohne Formular)
    tipp_liste = []
    for idx, zeile in spiele_auswahl.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{zeile['heim']}** - **{zeile['gast']}**")
        h = c2.number_input("H", 0, 20, 0, key=f"h_{idx}")
        g = c3.number_input("G", 0, 20, 0, key=f"g_{idx}")
        tipp_liste.append({"h": h, "g": g, "heim": zeile['heim'], "gast": zeile['gast']})
    
    nutzer_name = st.text_input("Dein Name für die Wertung:", key="user_input")
    
    if st.button("🚀 Tipps jetzt in der Cloud speichern"):
        if not nutzer_name.strip():
            st.warning("Bitte Namen eingeben!")
        else:
            try:
                for t in tipp_liste:
                    save_tipp(nutzer_name.strip(), aktuelle_saison, spieltag_tippen, t['heim'], t['gast'], t['h'], t['g'])
                st.success(f"✅ Erfolg! Tipps für {nutzer_name} wurden gespeichert.")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Fehler: {e}")

    st.divider()
    st.subheader("Punkte-Übersicht")
    suche = st.text_input("Dein Name zum Suchen:", key="search")
    if suche.strip():
        evaluate_tipps(df, suche.strip())
        conn = get_conn()
        sql = text('SELECT spieltag as "SP", heim, gast, tipp_heim || \':\' || tipp_gast as "Tipp", punkte FROM tipps WHERE "user" = :u')
        res = conn.query(sql, params={"u": suche.strip()}, ttl=0)
        st.dataframe(res)

# ==========================================
# 5. HAUPTPROGRAMM (MAIN)
# ==========================================

def main():
    st.set_page_config(page_title="Bundesliga Dashboard", layout="wide")
    df = load_data_from_db()
    
    if df.empty:
        st.error("Keine Daten geladen.")
        return

    menue = st.sidebar.radio("Navigation", ["Startseite", "Tippspiel"])

    if menue == "Startseite":
        show_startseite()
    elif menue == "Tippspiel":
        show_tippspiel(df)

if __name__ == "__main__":
    main()