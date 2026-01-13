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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Erstellt die Tabelle für Tipps mit der neuen Spalte 'user'
    c.execute('''CREATE TABLE IF NOT EXISTS tipps 
                 (user TEXT, saison TEXT, spieltag INTEGER, heim TEXT, gast TEXT, 
                  tipp_heim INTEGER, tipp_gast INTEGER, punkte INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS hall_of_fame 
                 (name TEXT, saison TEXT, punkte INTEGER)''')
    
    # Erstellt die Tabelle für Spiele, falls sie noch nicht existiert
    c.execute('''CREATE TABLE IF NOT EXISTS spiele 
                 (saison TEXT, spieltag INTEGER, heim TEXT, gast TEXT, 
                  tore_heim INTEGER, tore_gast INTEGER)''')
    
    # Hall of Fame Dummies nur einfugen, wenn leer
    c.execute("SELECT COUNT(*) FROM hall_of_fame")
    if c.fetchone()[0] == 0:
        dummies = [('Computer 1', 'Historisch', 20), ('Computer 2', 'Historisch', 17), ('Computer 3', 'Historisch', 14)]
        c.executemany("INSERT INTO hall_of_fame VALUES (?,?,?)", dummies)
    
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

def save_tipp(user, saison, spieltag, heim, gast, th, tg):
    """Speichert den Tipp und gibt Erfolg/Fehler zurück."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        # Wichtig: user=? in der WHERE-Klausel und beim INSERT
        c.execute("DELETE FROM tipps WHERE user=? AND saison=? AND spieltag=? AND heim=? AND gast=?", 
                  (user, saison, spieltag, heim, gast))
        c.execute("INSERT INTO tipps (user, saison, spieltag, heim, gast, tipp_heim, tipp_gast, punkte) VALUES (?,?,?,?,?,?,?,?)", 
                  (user, saison, spieltag, heim, gast, th, tg, 0))
        conn.commit()
        conn.close()
        return True, f"Tipp gespeichert: {heim} vs. {gast} ({th}:{tg})"
    except Exception as e:
        return False, f"Fehler: {str(e)}"

def evaluate_tipps(df, user=None):
    conn = sqlite3.connect(DB_FILE)
    if user:
        tipps_df = pd.read_sql_query("SELECT * FROM tipps WHERE user=?", conn, params=(user,))
    else:
        tipps_df = pd.read_sql_query("SELECT * FROM tipps", conn)
        
    for idx, row in tipps_df.iterrows():
        match = df[(df['saison'] == row['saison']) & (df['heim'] == row['heim']) & (df['gast'] == row['gast'])]
        if not match.empty and pd.notna(match.iloc[0]['tore_heim']):
            e_h, e_g = int(match.iloc[0]['tore_heim']), int(match.iloc[0]['tore_gast'])
            t_h, t_g = int(row['tipp_heim']), int(row['tipp_gast'])
            punkte = 3 if (e_h == t_h and e_g == t_g) else (1 if (e_h > e_g and t_h > t_g) or (e_h < e_g and t_h < t_g) or (e_h == e_g and t_h == t_g) else 0)
            
            c = conn.cursor()
            c.execute("UPDATE tipps SET punkte = ? WHERE user=? AND saison=? AND heim=? AND gast=?", 
                      (punkte, row['user'], row['saison'], row['heim'], row['gast']))
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

def get_latest_played_matchday(df, saison="2025/26"):
    """Findet den aktuellsten Spieltag mit Ergebnissen in der Datenbank."""
    df_saison = df[df["saison"] == saison]
    # Filtert Spiele, die bereits Tore eingetragen haben
    played = df_saison.dropna(subset=["tore_heim", "tore_gast"])
    if not played.empty:
        return int(played["spieltag"].max())
    return 1

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
            .mystyle td:nth-child(3) { width: auto; white-space: normal !important; text-align: left !important; }
        """
    elif type == "analyse":
        css += """
            .mystyle td:nth-child(1) { width: 80px !important; text-align: left !important; } 
            .mystyle td:nth-child(2), .mystyle td:nth-child(3), 
            .mystyle td:nth-child(4), .mystyle td:nth-child(5) { width: 30px !important; }
        """
    # --- OPTIMIERTER SPIELTAG-MODUS ---
    elif type == "spieltag":
        css += """
            /* Heimteam: schmaler (35%), rechtsbündig */
            .mystyle td:nth-child(1) { width: 35%; text-align: right !important; padding-right: 15px; font-weight: bold; } 
            /* Ergebnis: breiter (30%), zentriert, hervorgehoben */
            .mystyle td:nth-child(2) { width: 30%; font-weight: bold; text-align: center !important; background-color: #eeeeee !important; } 
            /* Gastteam: schmaler (35%), linksbündig */
            .mystyle td:nth-child(3) { width: 35%; text-align: left !important; padding-left: 15px; font-weight: bold; }
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

def show_spieltag_ansicht(df):
    # Sidebar-Steuerung
    seasons = sorted(df["saison"].unique(), reverse=True)
    st.sidebar.markdown("---")
    saison_sel = st.sidebar.selectbox("Saison für Spieltage", seasons, key="view_saison")
    
    # Automatisch aktuellsten Spieltag finden
    df_saison = df[df["saison"] == saison_sel]
    played = df_saison.dropna(subset=["tore_heim", "tore_gast"])
    latest_md = int(played["spieltag"].max()) if not played.empty else 1
    
    selected_spieltag = st.sidebar.selectbox(
        "Spieltag wählen", 
        list(range(1, 35)), 
        index=int(latest_md) - 1
    )

    # Einheitliche Überschrift
    st.markdown(f"<h1 style='text-align: center; color: darkred;'>⚽ Spieltagsergebnisse {selected_spieltag}. Spieltag ({saison_sel})</h1>", unsafe_allow_html=True)

    # Daten filtern und für die Tabelle vorbereiten
    day_matches = df[(df["saison"] == saison_sel) & (df["spieltag"] == selected_spieltag)].copy()

    if not day_matches.empty:
        # Wir bauen einen sauberen DataFrame nur für die Anzeige
        display_df = pd.DataFrame()
        display_df['Heim'] = day_matches['heim']
        
        # Formatierung: "4 : 0" oder "vs"
        display_df['Ergebnis'] = day_matches.apply(
            lambda r: f"{int(r['tore_heim'])} : {int(r['tore_gast'])}" 
            if pd.notna(r['tore_heim']) else "vs", axis=1
        )
        
        display_df['Gast'] = day_matches['gast']

        # Aufruf der Styling-Funktion mit dem neuen Typ
        display_styled_table(display_df, type="spieltag")
    else:
        st.info("Keine Daten für diesen Spieltag verfügbar.")

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
    all_seasons = sorted(df["saison"].unique(), reverse=True)
    aktuelle_saison = all_seasons[0]
    st.info(f"Aktuelle Saison: {aktuelle_saison}")

    # --- TEIL 1: TIPPS ABGEBEN ---
    #st.subheader("Deine Tipps")
    future_matches = df[(df['saison'] == aktuelle_saison) & (df['tore_heim'].isna())].copy()

    if future_matches.empty:
        st.info("Keine zukünftigen Spiele zum Tippen verfügbar.")
    else:
        spieltage = sorted(future_matches['spieltag'].unique())
        ausgewaehlter_tag = st.selectbox("Wähle einen Spieltag zum Tippen aus:", spieltage)
        tag_matches = future_matches[future_matches['spieltag'] == ausgewaehlter_tag]

        with st.form("tipp_form"):
            tipp_input_data = {}
            for idx, row in tag_matches.iterrows():
                h_name = str(row['heim']).strip()
                g_name = str(row['gast']).strip()
                col1, col2, col3 = st.columns([4, 1, 1])
                col1.write(f"**{h_name}** - **{g_name}**")
                t_h = col2.number_input("H", min_value=0, step=1, value=0, key=f"h_{idx}")
                t_g = col3.number_input("G", min_value=0, step=1, value=0, key=f"g_{idx}")
                tipp_input_data[idx] = (t_h, t_g)
            
            st.divider()
            user_name_input = st.text_input("Dein Name (erforderlich zum Speichern):", value="", placeholder="z.B. Max_Mustermann")
            
            if st.form_submit_button("Tipps speichern"):
                if not user_name_input.strip():
                    st.error("❌ Bitte gib deinen Namen ein!")
                else:
                    success_count = 0
                    for idx, row in tag_matches.iterrows():
                        th, tg = tipp_input_data[idx]
                        success, _ = save_tipp(user_name_input.strip(), aktuelle_saison, row['spieltag'], row['heim'], row['gast'], th, tg)
                        if success:
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"✅ {success_count} Tipps für '{user_name_input}' erfolgreich gespeichert!")
                        st.rerun()

    st.divider()
    # --- TEIL 2: ERGEBNISSE ANZEIGEN ---
    st.subheader("Deine Ergebnisse & Punkte")
    view_user = st.text_input("Gib deinen Namen ein, um deine Punkte zu sehen:", key="view_res")
    if view_user.strip():
        evaluate_tipps(df, view_user.strip()) 
        conn = sqlite3.connect(DB_FILE)
        query_auswertung = """
            SELECT t.spieltag as Sp, t.heim as Heim, t.gast as Gast, 
                   t.tipp_heim || ':' || t.tipp_gast as 'Dein Tipp',
                   s.tore_heim || ':' || s.tore_gast as 'Ergebnis',
                   t.punkte as 'Pkt'
            FROM tipps t
            JOIN spiele s ON t.saison = s.saison AND t.heim = s.heim AND t.gast = s.gast
            WHERE t.user = ? AND t.saison = ? AND s.tore_heim IS NOT NULL
            ORDER BY t.spieltag DESC, t.heim ASC
        """
        try:
            results_df = pd.read_sql_query(query_auswertung, conn, params=(view_user.strip(), aktuelle_saison))
            conn.close()
            if not results_df.empty:
                st.dataframe(results_df, use_container_width=True, hide_index=True)
            else:
                st.write(f"Keine gewerteten Tipps für '{view_user}' gefunden.")
        except Exception as e:
            st.error(f"Fehler bei der Abfrage: {e}")
            if conn: conn.close()

def show_highscore(df):
    st.title("🏆 Hall of Fame")
    evaluate_tipps(df)
    
    all_seasons = sorted(df["saison"].unique(), reverse=True)
    aktuelle_saison = all_seasons[0]
    
    conn = sqlite3.connect(DB_FILE)
    res = conn.execute("SELECT SUM(punkte) FROM tipps WHERE saison=?", (aktuelle_saison,)).fetchone()
    deine_punkte = res[0] if res[0] is not None else 0
    
    # 1. Bestenliste anzeigen (Immer sichtbar)
    query = "SELECT name as Name, saison as Saison, punkte as Punkte FROM hall_of_fame ORDER BY Punkte DESC"
    hof_df = pd.read_sql_query(query, conn)
    hof_df.insert(0, 'Platz', range(1, len(hof_df) + 1))

    # Optimierte Spaltenkonfiguration mit festen Breiten
    st.dataframe(
        hof_df,
        hide_index=True,
        use_container_width=False, # Verhindert das Strecken über die ganze Seite
        column_config={
            "Platz": st.column_config.NumberColumn("Platz", width=60), # Feste Breite in Pixeln
            "Name": st.column_config.TextColumn("Name", width=200),
            "Saison": st.column_config.TextColumn("Saison", width=120),
            "Punkte": st.column_config.NumberColumn("Punkte", width=80, format="%d ⭐") # Schön schmal
        }
    )
    
    # 2. Saison-Abschlussprüfung
    check_for_record(df, aktuelle_saison, deine_punkte)
    
    conn.close()

def check_for_record(df, saison, punkte):
    if punkte == 0: return
    
    # PRÜFUNG: Gibt es in dieser Saison noch Spiele ohne Ergebnis?
    offene_spiele = df[(df['saison'] == saison) & (df['tore_heim'].isna())]
    
    if not offene_spiele.empty:
        # Saison läuft noch -> Kein Eintrag möglich
        st.info(f"ℹ️ Die Saison {saison} läuft noch. Dein aktueller Stand: {punkte} Punkte. Die Hall of Fame wird nach dem letzten Spieltag freigeschaltet.")
        return

    # Wenn Saison beendet: Prüfen, ob schon eingetragen
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM hall_of_fame WHERE saison=? AND name != 'Computer 1' AND name != 'Computer 2' AND name != 'Computer 3'", (saison,))
    schon_eingetragen = c.fetchone()

    if not schon_eingetragen:
        # Prüfen, ob die Punkte reichen, um unter die Top 3 zu kommen oder Computer zu schlagen
        c.execute("SELECT MIN(punkte) FROM (SELECT punkte FROM hall_of_fame ORDER BY punkte DESC LIMIT 3)")
        min_top_punkte = c.fetchone()[0]

        if punkte >= min_top_punkte:
            st.balloons()
            st.success(f"🏆 Saison beendet! Du hast {punkte} Punkte erreicht und einen Platz in der Bestenliste verdient!")
            with st.form("hof_form"):
                name = st.text_input("Dein Name für die Ewigkeit:", placeholder="Echte Legende")
                if st.form_submit_button("In Hall of Fame eintragen"):
                    c.execute("INSERT INTO hall_of_fame (name, saison, punkte) VALUES (?,?,?)", (name, saison, punkte))
                    conn.commit()
                    st.rerun()
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
    
    # HIER "Spieltage" hinzugefügt:
    page = st.sidebar.radio("Navigation", ["Startseite", "Spieltage", "Saisontabelle", "Ewige Tabelle", "Meister", "Vereinsanalyse", "Tippspiel", "Highscore"])

    if page == "Startseite": show_startseite()
    
    # HIER die neue Seite verknüpft:
    elif page == "Spieltage":
        show_spieltag_ansicht(df)
        
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