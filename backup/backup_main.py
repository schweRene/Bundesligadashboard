#!/usr/bin/env python3
# coding: utf-8

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
import re
from datetime import datetime

DB_FILE = "bundesliga.db"

# ==========================================
# 1. DATENBANK & SETUP
# ==========================================

def init_db():
    """Erstellt die Tipps-Tabelle, falls sie noch nicht existiert."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tipps 
                 (saison TEXT, spieltag INTEGER, heim TEXT, gast TEXT, 
                  tipp_heim INTEGER, tipp_gast INTEGER, punkte INTEGER)''')
    conn.commit()
    conn.close()


def load_data_from_db():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM spiele", conn)
    conn.close()
    
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
# 2. TIPPSPIEL LOGIK
# ==========================================

def save_tipp(saison, spieltag, heim, gast, t_h, t_g):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM tipps WHERE saison=? AND heim=? AND gast=?", (saison, heim, gast))
    c.execute("INSERT INTO tipps (saison, spieltag, heim, gast, tipp_heim, tipp_gast, punkte) VALUES (?,?,?,?,?,?,?)",
              (saison, spieltag, heim, gast, t_h, t_g, 0))
    conn.commit()
    conn.close()

def evaluate_tipps(df):
    conn = sqlite3.connect(DB_FILE)
    tipps_df = pd.read_sql_query("SELECT * FROM tipps", conn)
    for idx, row in tipps_df.iterrows():
        match = df[(df['saison'] == row['saison']) & (df['heim'] == row['heim']) & (df['gast'] == row['gast'])]
        if not match.empty and pd.notna(match.iloc[0]['tore_heim']):
            e_h = int(match.iloc[0]['tore_heim'])
            e_g = int(match.iloc[0]['tore_gast'])
            t_h, t_g = int(row['tipp_heim']), int(row['tipp_gast'])
            punkte = 0
            if e_h == t_h and e_g == t_g:
                punkte = 3
            elif (e_h > e_g and t_h > t_g) or (e_h < e_g and t_h < t_g) or (e_h == e_g and t_h == t_g):
                punkte = 1
            c = conn.cursor()
            c.execute("UPDATE tipps SET punkte = ? WHERE saison=? AND heim=? AND gast=?", 
                      (punkte, row['saison'], row['heim'], row['gast']))
    conn.commit()
    conn.close()

# ==========================================
# 3. HELPER & BERECHNUNGEN
# ==========================================

@st.cache_data
def calculate_table(df, saison):
    df_saison = df[df["saison"] == saison].copy()
    if df_saison.empty: return pd.DataFrame()
    df_saison = df_saison.dropna(subset=["tore_heim", "tore_gast"])
    
    teams = pd.unique(df_saison[["heim", "gast"]].values.ravel("K"))
    stats = {t: {'Spiele': 0, 'S': 0, 'U': 0, 'N': 0, 'T': 0, 'G': 0, 'Punkte': 0} for t in teams}

    for _, row in df_saison.iterrows():
        h, g = row['heim'], row['gast']
        try:
            th, tg = int(row['tore_heim']), int(row['tore_gast'])
            stats[h]['Spiele'] += 1; stats[g]['Spiele'] += 1
            stats[h]['T'] += th; stats[h]['G'] += tg
            stats[g]['T'] += tg; stats[g]['G'] += th
            if th > tg:
                stats[h]['S'] += 1; stats[h]['Punkte'] += 3
                stats[g]['N'] += 1
            elif th < tg:
                stats[g]['S'] += 1; stats[g]['Punkte'] += 3
                stats[h]['N'] += 1
            else:
                stats[h]['U'] += 1; stats[h]['Punkte'] += 1
                stats[g]['U'] += 1; stats[g]['Punkte'] += 1
        except: continue

    table = pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': 'Team'})
    table['Diff'] = table['T'] - table['G']
    table = table.sort_values(by=['Punkte', 'Diff', 'T'], ascending=False).reset_index(drop=True)
    table.insert(0, 'Platz', range(1, len(table) + 1))
    return table

@st.cache_data
def compute_ewige_tabelle(df):
    if df.empty: return pd.DataFrame()
    df_local = df.dropna(subset=["tore_heim", "tore_gast"]).copy()
    h = df_local.rename(columns={"heim": "Team", "tore_heim": "GF", "tore_gast": "GA"})[["Team", "GF", "GA"]]
    a = df_local.rename(columns={"gast": "Team", "tore_gast": "GF", "tore_heim": "GA"})[["Team", "GF", "GA"]]
    all_m = pd.concat([h, a])
    all_m['P'] = 0; all_m['S'] = 0; all_m['U'] = 0; all_m['N'] = 0
    all_m.loc[all_m['GF'] > all_m['GA'], ['P', 'S']] = [3, 1]
    all_m.loc[all_m['GF'] == all_m['GA'], ['P', 'U']] = [1, 1]
    all_m.loc[all_m['GF'] < all_m['GA'], ['N']] = 1
    ewige = all_m.groupby("Team").agg(
        Spiele=('Team', 'size'), S=('S', 'sum'), U=('U', 'sum'),
        N=('N', 'sum'), T=('GF', 'sum'), G=('GA', 'sum'), Punkte=('P', 'sum')
    ).reset_index()
    cols = ['Spiele', 'S', 'U', 'N', 'T', 'G', 'Punkte']
    ewige[cols] = ewige[cols].astype(int)
    ewige = ewige.sort_values(by=["Punkte", "T"], ascending=False).reset_index(drop=True)
    ewige.insert(0, "Platz", range(1, len(ewige) + 1))
    return ewige

# ==========================================
# 4. HELPER FÜR STYLING
# ==========================================

def display_styled_table(df, type="standard"):
    html = df.to_html(index=False, classes='mystyle')
    
    css = """
        <style>
        .mystyle { width: 100%; border-collapse: collapse; color: black !important; }
        .mystyle th { 
            background-color: #D3D3D3 !important; 
            color: black !important; 
            padding: 10px; 
            border: 1px solid #ddd;
            text-align: center !important; 
        }
        .mystyle td { 
            padding: 8px; 
            border: 1px solid #ddd; 
            background-color: white !important; 
            color: black !important;
            text-align: center !important; 
        }
        .mystyle tr:nth-child(even) td { background-color: #f9f9f9 !important; }
    """
    
    if type == "meister":
        css += """
            .mystyle td:nth-child(1) { width: 150px; text-align: left !important; } 
            .mystyle td:nth-child(2) { width: 60px; } 
            .mystyle td:nth-child(3) { 
                width: auto; 
                white-space: normal !important; 
                text-align: left !important; 
            }
        """
    elif type == "analyse":
        css += """
            /* EXTREM SCHMALE SPALTEN FÜR ANALYSE */
            .mystyle td:nth-child(1) { width: 80px !important; text-align: left !important; } 
            .mystyle td:nth-child(2), .mystyle td:nth-child(3), 
            .mystyle td:nth-child(4), .mystyle td:nth-child(5) { width: 30px !important; }
        """
    else: 
        css += """
            .mystyle td:nth-child(2) { width: 150px; text-align: left !important; } 
        """

    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)
    st.write(html, unsafe_allow_html=True)

# ==========================================
# 5. SEITEN-INHALTE
# ==========================================

def show_startseite():
    st.markdown("<h1 style='text-align: center; color: darkred;'>⚽Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)
        st.markdown("<p style='text-align:center; font-size:12px;'>Quelle: Pixabay</p>", unsafe_allow_html=True)

def show_meisterstatistik(df, seasons):
    st.title("🏆 Deutsche Meisterschaften")
    meister_data = []
    for s in seasons:
        t = calculate_table(df, s)
        if not t.empty:
            meister_data.append({"Saison": s, "Meister": t.iloc[0]["Team"]})
    
    if meister_data:
        m_df = pd.DataFrame(meister_data)
        stats = m_df["Meister"].value_counts().reset_index()
        stats.columns = ["Verein", "Titel"]
        jahre = m_df.groupby("Meister")["Saison"].apply(lambda x: ", ".join(x)).reset_index()
        jahre.columns = ["Verein", "Saison"] 
        
        final_meister = pd.merge(stats, jahre, on="Verein").sort_values("Titel", ascending=False)
        display_styled_table(final_meister, type="meister")

def show_vereinsanalyse(df, seasons):
    st.title("📈 Vereinsanalyse")
    teams = sorted(df["heim"].unique())
    verein = st.selectbox("Verein suchen oder auswählen", teams, index=None, placeholder="Vereinsname eingeben...")
    
    if not verein:
        st.info("Bitte wähle einen Verein aus.")
        return

    st.subheader(f"Platzierungen: {verein}")
    erfolge = []
    for s in reversed(seasons):
        t = calculate_table(df, s)
        if not t.empty and verein in t["Team"].values:
            platz = t[t["Team"] == verein]["Platz"].values[0]
            erfolge.append({"Saison": s, "Platz": int(platz)})
    
    if erfolge:
        pdf = pd.DataFrame(erfolge)
        fig = px.line(pdf, x="Saison", y="Platz", markers=True, text="Platz")
        fig.update_traces(textposition="top center")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Direktvergleich")
    v_spiele = df[((df["heim"] == verein) | (df["gast"] == verein))].dropna(subset=["tore_heim", "tore_gast"])
    bilanz_list = []
    for _, r in v_spiele.iterrows():
        is_h = r["heim"] == verein
        gegner = r["gast"] if is_h else r["heim"]
        try:
            gf, ga = (int(r["tore_heim"]), int(r["tore_gast"])) if is_h else (int(r["tore_gast"]), int(r["tore_heim"]))
            res = "S" if gf > ga else ("U" if gf == ga else "N")
            bilanz_list.append({"Gegner": gegner, "Ergebnis": res})
        except: continue

    if bilanz_list:
        b_df = pd.DataFrame(bilanz_list)
        final_b = b_df.groupby("Gegner")["Ergebnis"].value_counts().unstack(fill_value=0)
        for c in ["S", "U", "N"]: 
            if c not in final_b: final_b[c] = 0
        final_b["Spiele"] = final_b["S"] + final_b["U"] + final_b["N"]
        final_b = final_b[["Spiele", "S", "U", "N"]].sort_values("Spiele", ascending=False).reset_index()
        final_b.columns = ["Gegner", "Spiele", "S", "U", "N"]
        display_styled_table(final_b, type="analyse")

def show_tippspiel(df):
    st.title("🎯 Tippspiel")
    seasons = sorted(df["saison"].unique(), reverse=True)
    saison = st.selectbox("Saison wählen", seasons, key="tipp_saison")
    # Nur Spiele ohne Tore (Zukunft)
    future_matches = df[(df['saison'] == saison) & (df['tore_heim'].isna())]
    if future_matches.empty:
        st.info("Keine zukünftigen Spiele zum Tippen verfügbar.")
    else:
        with st.form("tipp_form"):
            for idx, row in future_matches.iterrows():
                col1, col2, col3 = st.columns([4, 1, 1])
                col1.write(f"**{row['heim']}** vs. **{row['gast']}**")
                t_h = col2.number_input("H", min_value=0, step=1, key=f"h_{idx}")
                t_g = col3.number_input("G", min_value=0, step=1, key=f"g_{idx}")
            if st.form_submit_button("Tipps speichern"):
                for idx, row in future_matches.iterrows():
                    save_tipp(saison, row['spieltag'], row['heim'], row['gast'], st.session_state[f"h_{idx}"], st.session_state[f"g_{idx}"])
                st.success("Tipps gespeichert!")

def show_highscore(df):
    st.title("🏆 Highscore")
    evaluate_tipps(df)
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT saison as Saison, SUM(punkte) as Gesamtpunkte FROM tipps GROUP BY saison ORDER BY Gesamtpunkte DESC"
    highscore_df = pd.read_sql_query(query, conn)
    if not highscore_df.empty:
        st.table(highscore_df)
    else:
        st.info("Noch keine Punkte gesammelt.")
    conn.close()

# ==========================================
# 6. MAIN APP
# ==========================================

def main():
    st.set_page_config(page_title="Bundesliga Dashboard", layout="wide")
    st.markdown("<style>[data-testid='stSidebar'] { min-width: 200px !important; max-width: 200px !important; }</style>", unsafe_allow_html=True)
    init_db()
    df = load_data_from_db()
    if df.empty: return
    seasons = sorted(df["saison"].unique(), reverse=True)
    page = st.sidebar.radio("Navigation", ["Startseite", "Saisontabelle", "Ewige Tabelle", "Meister", "Vereinsanalyse", "Tippspiel", "Highscore"])

    if page == "Startseite": show_startseite()
    elif page == "Saisontabelle":
        saison_sel = st.sidebar.selectbox("Saison wählen", seasons)
        st.title(f"📅 Tabelle Saison {saison_sel}")
        display_styled_table(calculate_table(df, saison_sel))
    elif page == "Ewige Tabelle":
        st.title("📚 Ewige Tabelle")
        display_styled_table(compute_ewige_tabelle(df))
    elif page == "Meister": show_meisterstatistik(df, seasons)
    elif page == "Vereinsanalyse": show_vereinsanalyse(df, seasons)
    elif page == "Tippspiel": show_tippspiel(df)
    elif page == "Highscore": show_highscore(df)

if __name__ == "__main__":
    main()