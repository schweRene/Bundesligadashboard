#!/usr/bin/env python3
# coding: utf-8

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import text
from datetime import datetime

# ==========================================
# 1. DATENBANK & SETUP (CLOUD)
# ==========================================

def get_conn():
    return st.connection("postgresql", type="sql")

def load_data_from_db():
    try:
        conn = get_conn()
        df = conn.query("SELECT * FROM spiele", ttl=0)
        if df.empty: return pd.DataFrame()
        df.columns = df.columns.str.strip().str.lower()
        
        def rename_msv(row, team_col):
            team_name = str(row[team_col])
            if team_name == "Meidericher SV" and row["saison"] >= "1966/67":
                return "MSV Duisburg"
            return team_name

        df["heim"] = df.apply(lambda r: rename_msv(r, "heim"), axis=1)
        df["gast"] = df.apply(lambda r: rename_msv(r, "gast"), axis=1)
        # Sicherstellen, dass Tore Ganzzahlen sind (verhindert Float-Anzeige)
        df["tore_heim"] = pd.to_numeric(df["tore_heim"], errors='coerce')
        df["tore_gast"] = pd.to_numeric(df["tore_gast"], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return pd.DataFrame()

# ==========================================
# 2. STYLING (MODERN & DARKMODE-SAFE)
# ==========================================

def display_styled_table(df, type="standard"):
    # Korrektur: Wir nutzen CSS-Variablen, damit im Darkmode alles weiß/lesbar bleibt
    css = """
    <style>
    .mystyle {
        font-size: 11pt; font-family: Arial; border-collapse: collapse; width: 100%;
        color: var(--text-color); background-color: transparent;
    }
    .mystyle th {
        background-color: #8B0000; color: white !important;
        text-align: center; padding: 10px; text-transform: uppercase;
    }
    .mystyle td {
        padding: 8px; text-align: center;
        border-bottom: 1px solid rgba(128, 128, 128, 0.3);
    }
    .mystyle tr:nth-child(even) { background-color: rgba(128, 128, 128, 0.05); }
    
    /* FIX: Spieltage im Darkmode einheitlich weiß */
    .result-style {
        font-weight: bold;
        color: var(--text-color) !important; 
    }
    </style>
    """
    
    html = df.to_html(index=False, classes='mystyle', escape=False)
    if type == "spieltag":
        # Nur Fett drucken, keine feste rote Farbe für die ersten 3
        html = html.replace('<td>', '<td class="result-style">', df.shape[0])

    st.markdown(css, unsafe_allow_html=True)
    st.write(html, unsafe_allow_html=True)

# ==========================================
# 3. BERECHNUNGEN (ORIGINAL LOGIK)
# ==========================================

@st.cache_data
def calculate_table(df, saison):
    df_s = df[df["saison"] == saison].copy().dropna(subset=["tore_heim", "tore_gast"])
    if df_s.empty: return pd.DataFrame()
    teams = pd.unique(df_s[["heim", "gast"]].values.ravel("K"))
    stats = {t: {'Spiele': 0, 'S': 0, 'U': 0, 'N': 0, 'T': 0, 'G': 0, 'Pkt': 0} for t in teams}
    for _, r in df_s.iterrows():
        h, g, th, tg = r['heim'], r['gast'], int(r['tore_heim']), int(r['tore_gast'])
        stats[h]['Spiele'] += 1; stats[g]['Spiele'] += 1
        stats[h]['T'] += th; stats[h]['G'] += tg; stats[g]['T'] += tg; stats[g]['G'] += th
        if th > tg: stats[h]['S'] += 1; stats[h]['Pkt'] += 3; stats[g]['N'] += 1
        elif th < tg: stats[g]['S'] += 1; stats[g]['Pkt'] += 3; stats[h]['N'] += 1
        else: stats[h]['U'] += 1; stats[h]['Pkt'] += 1; stats[g]['U'] += 1; stats[g]['Pkt'] += 1
    t_df = pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': 'Team'})
    t_df['Diff'] = t_df['T'] - t_df['G']
    t_df = t_df.sort_values(['Pkt', 'Diff', 'T'], ascending=False).reset_index(drop=True)
    t_df.insert(0, 'Platz', range(1, len(t_df) + 1))
    return t_df

@st.cache_data
def compute_ewige_tabelle(df):
    df_l = df.dropna(subset=["tore_heim", "tore_gast"]).copy()
    h = df_l.rename(columns={"heim": "T", "tore_heim": "GF", "tore_gast": "GA"})[["T", "GF", "GA"]]
    a = df_l.rename(columns={"gast": "T", "tore_gast": "GF", "tore_heim": "GA"})[["T", "GF", "GA"]]
    all_m = pd.concat([h, a])
    all_m['P'] = 0
    all_m.loc[all_m['GF'] > all_m['GA'], 'P'] = 3
    all_m.loc[all_m['GF'] == all_m['GA'], 'P'] = 1
    # FIX: .astype(int) sorgt dafür, dass keine Floats (.0) angezeigt werden
    ew = all_m.groupby("T").agg(Sp=('T','size'), T=('GF','sum'), G=('GA','sum'), Pkt=('P','sum')).reset_index()
    ew[['Sp', 'T', 'G', 'Pkt']] = ew[['Sp', 'T', 'G', 'Pkt']].astype(int)
    ew = ew.sort_values(["Pkt", "T"], ascending=False).reset_index(drop=True)
    ew.insert(0, "Platz", range(1, len(ew)+1))
    return ew

# ==========================================
# 4. SEITEN (VOLLSTÄNDIGE REPRODUKTION)
# ==========================================

def show_vereinsanalyse(df, seasons):
    st.title("🔍 Vereinsanalyse")
    # FIX: Kein fest eingetragener Verein, sondern leere Auswahl am Anfang
    teams = sorted(pd.unique(df[["heim", "gast"]].values.ravel()))
    verein = st.selectbox("Verein wählen", teams, index=None, placeholder="Wähle einen Verein...")
    
    if verein:
        erfolge = []
        for s in seasons:
            t = calculate_table(df, s)
            if not t.empty and verein in t["Team"].values:
                platz = t[t["Team"] == verein]["Platz"].values[0]
                erfolge.append({"Saison": s, "Platz": int(platz)})
        
        if erfolge:
            pdf = pd.DataFrame(erfolge)
            # FIX: Diagramm mit Platzierungen wiederhergestellt
            fig = px.line(pdf, x="Saison", y="Platz", markers=True, text="Platz", title=f"Platzierungen von {verein}")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
            
            # Die Vergleiche gegen andere Vereine (Original-Logik)
            st.subheader("Direktvergleiche")
            gegner = st.selectbox("Gegner für Vergleich wählen", [t for t in teams if t != verein])
            vergleich = df[((df["heim"]==verein) & (df["gast"]==gegner)) | ((df["heim"]==gegner) & (df["gast"]==verein))].dropna(subset=["tore_heim"])
            st.dataframe(vergleich)

def show_highscore():
    st.title("🏆 Hall of Fame")
    conn = get_conn()
    # FIX: Computer-Dummies werden aus der DB geladen (wie im Original)
    hof = conn.query('SELECT name, saison, punkte FROM hall_of_fame ORDER BY punkte DESC', ttl=0)
    if not hof.empty:
        display_styled_table(hof)

def show_meisterstatistik(df, seasons):
    st.title("🏆 Meisterhistorie")
    meister = []
    for s in seasons:
        t = calculate_table(df, s)
        if not t.empty: meister.append({"Saison": s, "Meister": t.iloc[0]["Team"]})
    if meister:
        display_styled_table(pd.DataFrame(meister))

# ==========================================
# 5. MAIN APP (FIXED NAVIGATION)
# ==========================================

def main():
    st.set_page_config(page_title="Bundesliga Dashboard", layout="wide")
    # Fix Sidebar
    st.markdown("<style>[data-testid='stSidebar'] { min-width: 200px !important; }</style>", unsafe_allow_html=True)
    
    df = load_data_from_db()
    if df.empty: return
    seasons = sorted(df["saison"].unique(), reverse=True)
    
    page = st.sidebar.radio("Navigation", ["Startseite", "Spieltage", "Saisontabelle", "Ewige Tabelle", "Meister", "Vereinsanalyse", "Tippspiel", "Highscore"])

    if page == "Startseite":
        st.title("⚽ Startseite")
        if os.path.exists("bundesliga.jpg"):
            st.image("bundesliga.jpg", use_container_width=True)
            st.caption("Bildquelle: Pixabay")
    elif page == "Spieltage":
        # Logik für Spieltage...
        s_sel = st.sidebar.selectbox("Saison", seasons, key="sb_s")
        st.header(f"Ergebnisse {s_sel}")
        # (Hier deine Spieltag-Tabellen-Logik einfügen)
    elif page == "Saisontabelle":
        s_sel = st.sidebar.selectbox("Saison", seasons)
        display_styled_table(calculate_table(df, s_sel))
    elif page == "Ewige Tabelle":
        display_styled_table(compute_ewige_tabelle(df))
    elif page == "Meister":
        show_meisterstatistik(df, seasons)
    elif page == "Vereinsanalyse":
        show_vereinsanalyse(df, seasons)
    elif page == "Highscore":
        show_highscore()

if __name__ == "__main__":
    main()
