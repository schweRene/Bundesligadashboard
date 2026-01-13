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
    """Lädt die Spieldaten aus der Online-Datenbank in einen Pandas-Datensatz."""
    conn = get_conn()
    df = conn.query("SELECT * FROM spiele", ttl=0)
    
    if df.empty:
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={"home": "heim", "away": "gast"})
    
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
    """Speichert einen einzelnen Tipp und gibt bei Erfolg True zurück."""
    conn = get_conn()
    with conn.session as session:
        # "user" muss in Anführungszeichen, da es ein SQL-Keywort ist
        sql = text("""
            INSERT INTO tipps ("user", saison, spieltag, heim, gast, tipp_heim, tipp_gast, punkte)
            VALUES (:u, :s, :st, :h, :g, :th, :tg, :p)
        """)
        session.execute(sql, {
            "u": user, "s": saison, "st": int(spieltag), 
            "h": heim, "g": gast, "th": int(th), "tg": int(tg), "p": 0
        })
        session.commit()

def evaluate_tipps(df_spiele, user):
    """Vergleicht Tipps mit echten Ergebnissen und aktualisiert die Punkte."""
    conn = get_conn()
    try:
        with conn.session as session:
            sql_tipps = text('SELECT * FROM tipps WHERE "user" = :u AND punkte = 0')
            tipps = conn.query(sql_tipps, params={"u": user}, ttl=0)
            
            for _, tipp in tipps.iterrows():
                match = df_spiele[
                    (df_spiele['saison'] == tipp['saison']) & 
                    (df_spiele['heim'] == tipp['heim']) & 
                    (df_spiele['gast'] == tipp['gast'])
                ]
                
                if not match.empty and pd.notna(match.iloc[0]['tore_heim']):
                    t_h_echt, t_g_echt = int(match.iloc[0]['tore_heim']), int(match.iloc[0]['tore_gast'])
                    t_h_tipp, t_g_tipp = int(tipp['tipp_heim']), int(tipp['tipp_gast'])
                    
                    pkt = 0
                    if t_h_echt == t_h_tipp and t_g_echt == t_g_tipp: pkt = 3
                    elif (t_h_echt - t_g_echt) == (t_h_tipp - t_g_tipp): pkt = 2
                    elif (t_h_echt > t_g_echt and t_h_tipp > t_g_tipp) or (t_h_echt < t_g_echt and t_h_tipp < t_g_tipp): pkt = 1
                    
                    if pkt > 0:
                        session.execute(text('UPDATE tipps SET punkte = :p WHERE id = :tid'), {"p": pkt, "tid": tipp['id']})
            session.commit()
    except Exception as e:
        st.error(f"Fehler bei Punkteberechnung: {e}")

# ==========================================
# 3. TABELLEN-BERECHNUNG
# ==========================================

@st.cache_data
def calculate_table(df, saison):
    df_saison = df[df["saison"] == saison].copy().dropna(subset=["tore_heim", "tore_gast"])
    if df_saison.empty: return pd.DataFrame()
    teams = pd.unique(df_saison[["heim", "gast"]].values.ravel("K"))
    statistik = {team: {'Spiele': 0, 'S': 0, 'U': 0, 'N': 0, 'T': 0, 'G': 0, 'Punkte': 0} for team in teams}
    for _, row in df_saison.iterrows():
        h, g, th, tg = row['heim'], row['gast'], int(row['tore_heim']), int(row['tore_gast'])
        statistik[h]['Spiele'] += 1; statistik[g]['Spiele'] += 1
        statistik[h]['T'] += th; statistik[h]['G'] += tg; statistik[g]['T'] += tg; statistik[g]['G'] += th
        if th > tg: statistik[h]['S'] += 1; statistik[h]['Punkte'] += 3; statistik[g]['N'] += 1
        elif th < tg: statistik[g]['S'] += 1; statistik[g]['Punkte'] += 3; statistik[h]['N'] += 1
        else: statistik[h]['U'] += 1; statistik[h]['Punkte'] += 1; statistik[g]['U'] += 1; statistik[g]['Punkte'] += 1
    tabelle = pd.DataFrame.from_dict(statistik, orient='index').reset_index().rename(columns={'index': 'Team'})
    tabelle['Diff'] = tabelle['T'] - tabelle['G']
    tabelle = tabelle.sort_values(by=['Punkte', 'Diff', 'T'], ascending=False).reset_index(drop=True)
    tabelle.insert(0, 'Platz', range(1, len(tabelle) + 1))
    return tabelle

@st.cache_data
def compute_ewige_tabelle(df):
    if df.empty: return pd.DataFrame()
    df_lokal = df.dropna(subset=["tore_heim", "tore_gast"]).copy()
    alle = pd.concat([df_lokal.rename(columns={"heim": "Team", "tore_heim": "GF", "tore_gast": "GA"}),
                      df_lokal.rename(columns={"gast": "Team", "tore_gast": "GF", "tore_heim": "GA"})])
    alle['P'] = 0; alle['S'] = 0; alle['U'] = 0; alle['N'] = 0
    alle.loc[alle['GF'] > alle['GA'], ['P', 'S']] = [3, 1]
    alle.loc[alle['GF'] == alle['GA'], ['P', 'U']] = [1, 1]
    alle.loc[alle['GF'] < alle['GA'], ['N']] = 1
    ewige = alle.groupby("Team").agg(Spiele=('Team', 'size'), S=('S', 'sum'), U=('U', 'sum'), N=('N', 'sum'), T=('GF', 'sum'), G=('GA', 'sum'), Punkte=('P', 'sum')).reset_index()
    ewige = ewige.sort_values(by=["Punkte", "T"], ascending=False).reset_index(drop=True)
    ewige.insert(0, "Platz", range(1, len(ewige) + 1))
    return ewige

def display_styled_table(df):
    st.markdown("""<style>
        .mystyle { width: 100%; border-collapse: collapse; color: black !important; }
        .mystyle th { background-color: #D3D3D3 !important; color: black; padding: 10px; border: 1px solid #ddd; }
        .mystyle td { padding: 8px; border: 1px solid #ddd; background-color: white; color: black; text-align: center; }
    </style>""", unsafe_allow_html=True)
    st.write(df.to_html(index=False, classes='mystyle'), unsafe_allow_html=True)

# ==========================================
# 4. SEITEN-FUNKTIONEN
# ==========================================

def show_tippspiel(df):
    st.title("🎯 Tippspiel")
    aktuelle_saison = sorted(df["saison"].unique(), reverse=True)[0]
    zukunft_spiele = df[(df['saison'] == aktuelle_saison) & (df['tore_heim'].isna())].copy()
    
    if zukunft_spiele.empty:
        st.info("Keine offenen Spiele gefunden.")
        return

    spieltag_tippen = st.selectbox("Wähle den Spieltag:", sorted(zukunft_spiele['spieltag'].unique()))
    spiele_auswahl = zukunft_spiele[zukunft_spiele['spieltag'] == spieltag_tippen]
    
    # Eingabe-Container
    tipp_inputs = {}
    for idx, zeile in spiele_auswahl.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{zeile['heim']}** - **{zeile['gast']}**")
        h = c2.number_input("H", 0, 20, 0, key=f"h_{idx}")
        g = c3.number_input("G", 0, 20, 0, key=f"g_{idx}")
        tipp_inputs[idx] = (h, g, zeile['heim'], zeile['gast'])
    
    nutzer_name = st.text_input("Dein Name:", key="user_name")
    
    if st.button("🚀 Tipps in Cloud speichern"):
        if not nutzer_name.strip():
            st.warning("Bitte gib einen Namen ein!")
        else:
            with st.spinner("Speichere Tipps..."):
                try:
                    for idx, (th, tg, h, g) in tipp_inputs.items():
                        save_tipp(nutzer_name.strip(), aktuelle_saison, spieltag_tippen, h, g, th, tg)
                    st.success(f"✅ Tipps für {nutzer_name} erfolgreich gespeichert!")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Schwerer Datenbankfehler: {e}")

    st.divider()
    st.subheader("Meine Punkte")
    user_search = st.text_input("Name suchen:", key="view_res")
    if user_search.strip():
        evaluate_tipps(df, user_search.strip())
        conn = get_conn()
        res = conn.query(text('SELECT spieltag as "SP", heim, gast, tipp_heim || \':\' || tipp_gast as "Tipp", punkte FROM tipps WHERE "user" = :u'), params={"u": user_search.strip()}, ttl=0)
        st.dataframe(res)

# ==========================================
# 5. MAIN
# ==========================================

def main():
    st.set_page_config(page_title="Bundesliga Dashboard", layout="wide")
    df = load_data_from_db()
    if df.empty:
        st.error("Datenbankverbindung fehlgeschlagen.")
        return

    seite = st.sidebar.radio("Menü", ["Startseite", "Spieltage", "Saisontabelle", "Ewige Tabelle", "Tippspiel"])
    if seite == "Startseite":
        st.title("⚽ Bundesliga-Dashboard")
    elif seite == "Spieltage":
        saison = st.sidebar.selectbox("Saison", sorted(df["saison"].unique(), reverse=True))
        tag = st.sidebar.selectbox("Tag", range(1, 35))
        tag_df = df[(df["saison"] == saison) & (df["spieltag"] == tag)]
        display_styled_table(tag_df[["heim", "gast"]])
    elif seite == "Saisontabelle":
        s = st.sidebar.selectbox("Saison", sorted(df["saison"].unique(), reverse=True))
        display_styled_table(calculate_table(df, s))
    elif seite == "Ewige Tabelle":
        display_styled_table(compute_ewige_tabelle(df))
    elif seite == "Tippspiel":
        show_tippspiel(df)

if __name__ == "__main__":
    main()