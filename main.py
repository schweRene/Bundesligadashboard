#!/usr/bin/env python3
# coding: utf-8

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
from datetime import datetime
from sqlalchemy import text

# ==========================================
# 1. DATENBANK & SETUP (Cloud Version)
# ==========================================

def get_conn():
    """Erstellt die Verbindung über die Streamlit Cloud Secrets."""
    return st.connection("postgresql", type="sql")

def init_db():
    """In der Cloud bleiben die Tabellen in Supabase bestehen."""
    pass

def load_data_from_db():
    try:
        conn = get_conn()
        df = conn.query("SELECT * FROM spiele", ttl=0)
        if df.empty:
            return pd.DataFrame()
        
        df.columns = df.columns.str.strip().str.lower()
        
        # Original MSV Duisburg Logik
        def rename_msv(row, team_col):
            team_name = str(row[team_col])
            if team_name == "Meidericher SV" and row["saison"] >= "1966/67":
                return "MSV Duisburg"
            return team_name

        df["heim"] = df.apply(lambda r: rename_msv(r, "heim"), axis=1)
        df["gast"] = df.apply(lambda r: rename_msv(r, "gast"), axis=1)
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return pd.DataFrame()

# ==========================================
# 2. TIPPSPIEL LOGIK
# ==========================================

def save_tipp(user, saison, spieltag, heim, gast, th, tg):
    try:
        conn = get_conn()
        with conn.session as session:
            # Postgres braucht Anführungszeichen für "user"
            session.execute(text('DELETE FROM tipps WHERE "user"=:u AND saison=:s AND spieltag=:st AND heim=:h AND gast=:g'),
                          {"u": user, "s": saison, "st": int(spieltag), "h": heim, "g": gast})
            
            session.execute(text('''INSERT INTO tipps ("user", saison, spieltag, heim, gast, tipp_heim, tipp_gast, punkte)
                                  VALUES (:u, :s, :st, :h, :g, :th, :tg, NULL)'''),
                          {"u": user, "s": saison, "st": int(spieltag), "h": heim, "g": gast, "th": int(th), "tg": int(tg)})
            session.commit()
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")

def evaluate_tipps(df_spiele, user):
    conn = get_conn()
    try:
        with conn.session as session:
            sql = text('SELECT * FROM tipps WHERE "user" = :u AND punkte IS NULL')
            tipps = conn.query(sql, params={"u": user}, ttl=0)
            for _, tipp in tipps.iterrows():
                match = df_spiele[(df_spiele['saison'] == tipp['saison']) & 
                                  (df_spiele['heim'] == tipp['heim']) & 
                                  (df_spiele['gast'] == tipp['gast'])]
                if not match.empty and pd.notna(match.iloc[0]['tore_heim']):
                    e_h, e_g = int(match.iloc[0]['tore_heim']), int(match.iloc[0]['tore_gast'])
                    t_h, t_g = int(tipp['tipp_heim']), int(tipp['tipp_gast'])
                    pkt = 0
                    if e_h == t_h and e_g == t_g: pkt = 3
                    elif (e_h - e_g) == (t_h - t_g): pkt = 2
                    elif (e_h > e_g and t_h > t_g) or (e_h < e_g and t_h < t_g): pkt = 1
                    session.execute(text('UPDATE tipps SET punkte = :p WHERE id = :tid'), {"p": pkt, "tid": tipp['id']})
            session.commit()
    except: pass

# ==========================================
# 3. HELPER & BERECHNUNGEN (ORIGINAL)
# ==========================================

@st.cache_data
def calculate_table(df, saison):
    df_s = df[df["saison"] == saison].copy()
    if df_s.empty: return pd.DataFrame()
    df_s = df_s.dropna(subset=["tore_heim", "tore_gast"])
    teams = pd.unique(df_s[["heim", "gast"]].values.ravel("K"))
    res = {t: {'Spiele':0, 'S':0, 'U':0, 'N':0, 'T':0, 'G':0, 'Pkt':0} for t in teams}
    for _, r in df_s.iterrows():
        h, g, th, tg = r['heim'], r['gast'], int(r['tore_heim']), int(r['tore_gast'])
        for t in [h, g]: res[t]['Spiele'] += 1
        res[h]['T'] += th; res[h]['G'] += tg; res[g]['T'] += tg; res[g]['G'] += th
        if th > tg: res[h]['S'] += 1; res[h]['Pkt'] += 3; res[g]['N'] += 1
        elif th < tg: res[g]['S'] += 1; res[g]['Pkt'] += 3; res[h]['N'] += 1
        else: res[h]['U'] += 1; res[h]['Pkt'] += 1; res[g]['U'] += 1; res[g]['Pkt'] += 1
    t_df = pd.DataFrame.from_dict(res, orient='index').reset_index().rename(columns={'index': 'Team'})
    t_df['Diff'] = t_df['T'] - t_df['G']
    t_df = t_df.sort_values(['Pkt', 'Diff', 'T'], ascending=False).reset_index(drop=True)
    t_df.insert(0, 'Platz', range(1, len(t_df) + 1))
    return t_df

@st.cache_data
def compute_ewige_tabelle(df):
    if df.empty: return pd.DataFrame()
    df_l = df.dropna(subset=["tore_heim", "tore_gast"]).copy()
    h = df_l.rename(columns={"heim": "Team", "tore_heim": "GF", "tore_gast": "GA"})[["Team", "GF", "GA"]]
    a = df_l.rename(columns={"gast": "Team", "tore_gast": "GF", "tore_heim": "GA"})[["Team", "GF", "GA"]]
    all_m = pd.concat([h, a])
    all_m['P'], all_m['S'], all_m['U'], all_m['N'] = 0, 0, 0, 0
    all_m.loc[all_m['GF'] > all_m['GA'], ['P', 'S']] = [3, 1]
    all_m.loc[all_m['GF'] == all_m['GA'], ['P', 'U']] = [1, 1]
    all_m.loc[all_m['GF'] < all_m['GA'], ['N']] = 1
    ewige = all_m.groupby("Team").agg(Spiele=('Team', 'size'), S=('S', 'sum'), U=('U', 'sum'), N=('N', 'sum'), T=('GF', 'sum'), G=('GA', 'sum'), Punkte=('P', 'sum')).reset_index()
    ewige = ewige.sort_values(by=["Punkte", "T"], ascending=False).reset_index(drop=True)
    ewige.insert(0, "Platz", range(1, len(ewige) + 1))
    return ewige

def get_latest_played_matchday(df_saison):
    played = df_saison.dropna(subset=["tore_heim", "tore_gast"])
    return int(played["spieltag"].max()) if not played.empty else 1

# ==========================================
# 4. STYLING (EXAKT AUS ORIGINAL)
# ==========================================

def display_styled_table(df, type="standard"):
    # Wir nutzen CSS-Variablen für automatische Farbanpassung
    css = """
    <style>
    .mystyle {
        font-size: 11pt; 
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        border-collapse: collapse; 
        width: 100%;
        margin: 10px 0;
        color: var(--text-color);
        background-color: var(--background-color);
    }
    .mystyle th {
        background-color: #8B0000;
        color: white !important;
        text-align: center;
        padding: 15px;
        text-transform: uppercase;
        border: none;
    }
    .mystyle td {
        padding: 12px;
        text-align: center;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
    }
    /* Zebra-Streifen die im Dark- und Lightmode funktionieren */
    .mystyle tr:nth-child(even) { 
        background-color: rgba(139, 0, 0, 0.03); 
    }
    .mystyle tr:hover { 
        background-color: rgba(139, 0, 0, 0.1); 
        transition: 0.3s;
    }
    
    /* Ergebnis-Highlighting */
    .result-font {
        font-weight: bold;
        color: #ff4b4b;
        font-size: 1.1em;
    }
    </style>
    """
    
    html = df.to_html(index=False, classes='mystyle', escape=False)
    
    if type == "spieltag":
        # Stylt die mittlere Spalte (Ergebnis)
        html = html.replace('<td>', '<td class="result-font">', df.shape[0]) 

    st.markdown(css, unsafe_allow_html=True)
    st.markdown(html, unsafe_allow_html=True)

# ==========================================
# 5. SEITEN-LOGIK
# ==========================================

def show_startseite():
    st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>⚽ Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)
        st.caption("Bildquelle: [Pixabay](https://pixabay.com)")

def show_spieltag_ansicht(df):
    seasons = sorted(df["saison"].unique(), reverse=True)
    st.sidebar.markdown("---")
    # HIER war der Fehler (Anführungszeichen bei key ergänzt):
    s_sel = st.sidebar.selectbox("Saison wählen", seasons, key="sb_s") 
    
    df_s = df[df["saison"] == s_sel]
    l_md = get_latest_played_matchday(df_s)
    s_md = st.sidebar.selectbox("Spieltag wählen", list(range(1, 35)), index=l_md-1)
    
    st.markdown(f"<h1 style='text-align: center; color: darkred;'>⚽ Ergebnisse {s_md}. Spieltag</h1>", unsafe_allow_html=True)
    matches = df[(df["saison"] == s_sel) & (df["spieltag"] == s_md)].copy()
    
    if not matches.empty:
        res_df = pd.DataFrame({
            'Heim': matches['heim'], 
            'Ergebnis': matches.apply(lambda r: f"{int(r['tore_heim'])} : {int(r['tore_gast'])}" if pd.notna(r['tore_heim']) else "vs", axis=1),
            'Gast': matches['gast']
        })
        display_styled_table(res_df, type="spieltag")

def show_meisterstatistik(df):
    st.markdown("<h1 style='text-align: center;'>🏆 Ehrentafel der Meister</h1>", unsafe_allow_html=True)
    seasons = sorted(df["saison"].unique())
    meister_data = []
    for s in seasons:
        t = calculate_table(df, s)
        if not t.empty:
            meister_data.append({"Saison": s, "Meister": t.iloc[0]["Team"]})
    
    if meister_data:
        m_df = pd.DataFrame(meister_data)
        # Zähle Titel pro Verein
        stats = m_df["Meister"].value_counts().reset_index()
        stats.columns = ["Verein", "Titel"]
        # Jahre hinzufügen
        jahre = m_df.groupby("Meister")["Saison"].apply(lambda x: ", ".join(x)).reset_index()
        jahre.columns = ["Verein", "Jahre"]
        
        final_df = pd.merge(stats, jahre, on="Verein").sort_values("Titel", ascending=False)
        display_styled_table(final_df)

def show_vereinsanalyse(df, seasons):
    st.title("📈 Vereinsanalyse")
    v = st.selectbox("Verein wählen", sorted(df["heim"].unique()))
    erf = []
    for s in seasons:
        t = calculate_table(df, s)
        if not t.empty and v in t["Team"].values:
            erf.append({"Saison": s, "Platz": int(t[t["Team"] == v]["Platz"].values[0])})
    if erf:
        fig = px.line(pd.DataFrame(erf), x="Saison", y="Platz", markers=True, title=f"Platzierungen {v}")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig)

def show_tippspiel(df):
    st.title("🎯 Tippspiel")
    all_s = sorted(df["saison"].unique(), reverse=True)
    akt_s = all_s[0]
    future = df[(df['saison'] == akt_s) & (df['tore_heim'].isna())].copy()
    if not future.empty:
        tage = sorted(future['spieltag'].unique())
        tag = st.selectbox("Wähle Spieltag:", tage)
        tag_m = future[future['spieltag'] == tag]
        with st.form("tipp_form"):
            t_data = {}
            for i, r in tag_m.iterrows():
                c1, c2, c3 = st.columns([4, 1, 1])
                c1.write(f"**{r['heim']}** - **{r['gast']}**")
                th = c2.number_input("H", 0, 15, 0, key=f"h_{i}")
                tg = c3.number_input("G", 0, 15, 0, key=f"g_{i}")
                t_data[i] = (th, tg)
            user = st.text_input("Dein Name:")
            if st.form_submit_button("Tipps speichern"):
                if user.strip():
                    for i, r in tag_m.iterrows():
                        save_tipp(user.strip(), akt_s, tag, r['heim'], r['gast'], t_data[i][0], t_data[i][1])
                    st.success("Gespeichert!")
                    st.rerun()

def show_highscore(df):
    st.title("🏆 Highscore")
    conn = get_conn()
    hof = conn.query('SELECT name, saison, punkte FROM hall_of_fame ORDER BY punkte DESC', ttl=0)
    display_styled_table(hof)

# ==========================================
# 6. MAIN APP
# ==========================================

def main():
    st.set_page_config(page_title="Bundesliga Dashboard", layout="wide")
    st.markdown("<style>[data-testid='stSidebar'] { min-width: 200px !important; max-width: 200px !important; }</style>", unsafe_allow_html=True)
    df = load_data_from_db()
    if df.empty: return
    seasons = sorted(df["saison"].unique(), reverse=True)
    page = st.sidebar.radio("Navigation", ["Startseite", "Spieltage", "Saisontabelle", "Ewige Tabelle", "Meister", "Vereinsanalyse", "Tippspiel", "Highscore"])

    if page == "Startseite": show_startseite()
    elif page == "Spieltage": show_spieltag_ansicht(df)
    elif page == "Saisontabelle":
        s = st.sidebar.selectbox("Saison wählen", seasons)
        st.title(f"📅 Tabelle Saison {s}")
        display_styled_table(calculate_table(df, s))
    elif page == "Ewige Tabelle": 
        st.title("📚 Ewige Tabelle")
        display_styled_table(compute_ewige_tabelle(df))
    elif page == "Meister": show_meisterstatistik(df, seasons)
    elif page == "Vereinsanalyse": show_vereinsanalyse(df, seasons)
    elif page == "Tippspiel": show_tippspiel(df)
    elif page == "Highscore": show_highscore(df)

if __name__ == "__main__":
    main()
