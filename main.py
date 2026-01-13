#!/usr/bin/env python3
# coding: utf-8

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import text
from datetime import datetime

# ==========================================
# 1. DATENBANK & SETUP (Cloud Version)
# ==========================================

def get_conn():
    return st.connection("postgresql", type="sql")

def init_db():
    """Fügt die Computer-Dummies mit den korrekten Werten (20, 17, 14) ein, falls leer."""
    try:
        conn = get_conn()
        res = conn.query("SELECT COUNT(*) as count FROM hall_of_fame", ttl=0)
        if res.iloc[0]['count'] == 0:
            with conn.session as session:
                dummies = [
                    ('Computer 1', 'Historisch', 20),
                    ('Computer 2', 'Historisch', 17),
                    ('Computer 3', 'Historisch', 14)
                ]
                for name, saison, punkte in dummies:
                    session.execute(
                        text('INSERT INTO hall_of_fame (name, saison, punkte) VALUES (:n, :s, :p)'),
                        {"n": name, "s": saison, "p": punkte}
                    )
                session.commit()
    except Exception:
        pass

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
        df["tore_heim"] = pd.to_numeric(df["tore_heim"], errors='coerce')
        df["tore_gast"] = pd.to_numeric(df["tore_gast"], errors='coerce')
        return df
    except Exception:
        return pd.DataFrame()

# ==========================================
# 2. TIPPSPIEL LOGIK 
# ==========================================

def save_tipp(user, saison, spieltag, heim, gast, th, tg):
    try:
        conn = get_conn()
        with conn.session as session:
            del_sql = text('DELETE FROM tipps WHERE "user" = :u AND saison = :s AND spieltag = :st AND heim = :h AND gast = :g')
            session.execute(del_sql, {"u": user, "s": saison, "st": int(spieltag), "h": heim, "g": gast})
            
            ins_sql = text('''INSERT INTO tipps ("user", saison, spieltag, heim, gast, tipp_heim, tipp_gast, punkte)
                              VALUES (:u, :s, :st, :h, :g, :th, :tg, 0)''')
            session.execute(ins_sql, {"u": user, "s": saison, "st": int(spieltag), "h": heim, "g": gast, "th": int(th), "tg": int(tg)})
            session.commit()
        return True, "Erfolg"
    except Exception as e:
        return False, str(e)

def evaluate_tipps(df_spiele, user=None):
    conn = get_conn()
    try:
        with conn.session as session:
            if user:
                sql = text('SELECT * FROM tipps WHERE "user" = :u')
                tipps = conn.query(sql, params={"u": user}, ttl=0)
            else:
                tipps = conn.query('SELECT * FROM tipps', ttl=0)
            
            for _, tipp in tipps.iterrows():
                match = df_spiele[(df_spiele['saison'] == tipp['saison']) & 
                                  (df_spiele['heim'] == tipp['heim']) & 
                                  (df_spiele['gast'] == tipp['gast'])]
                
                if not match.empty and pd.notna(match.iloc[0]['tore_heim']):
                    e_h, e_g = int(match.iloc[0]['tore_heim']), int(match.iloc[0]['tore_gast'])
                    t_h, t_g = int(tipp['tipp_heim']), int(tipp['tipp_gast'])
                    pkt = 3 if (e_h == t_h and e_g == t_g) else (1 if (e_h > e_g and t_h > t_g) or (e_h < e_g and t_h < t_g) or (e_h == e_g and t_h == t_g) else 0)
                    upd = text('UPDATE tipps SET punkte = :p WHERE id = :tid')
                    session.execute(upd, {"p": pkt, "tid": tipp['id']})
            session.commit()
    except:
        pass

# ==========================================
# 3. BERECHNUNGEN 
# ==========================================

@st.cache_data
def calculate_table(df, saison):
    df_s = df[df["saison"] == saison].copy().dropna(subset=["tore_heim", "tore_gast"])
    if df_s.empty: return pd.DataFrame()
    teams = pd.unique(df_s[["heim", "gast"]].values.ravel("K"))
    stats = {t: {'Spiele': 0, 'S': 0, 'U': 0, 'N': 0, 'T': 0, 'G': 0, 'Punkte': 0} for t in teams}
    for _, row in df_s.iterrows():
        h, g, th, tg = row['heim'], row['gast'], int(row['tore_heim']), int(row['tore_gast'])
        stats[h]['Spiele'] += 1; stats[g]['Spiele'] += 1
        stats[h]['T'] += th; stats[h]['G'] += tg; stats[g]['T'] += tg; stats[g]['G'] += th
        if th > tg: stats[h]['S'] += 1; stats[h]['Punkte'] += 3; stats[g]['N'] += 1
        elif th < tg: stats[g]['S'] += 1; stats[g]['Punkte'] += 3; stats[h]['N'] += 1
        else: stats[h]['U'] += 1; stats[h]['Punkte'] += 1; stats[g]['U'] += 1; stats[g]['Punkte'] += 1
    table = pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': 'Team'})
    table['Diff'] = table['T'] - table['G']
    table = table.sort_values(by=['Punkte', 'Diff', 'T'], ascending=False).reset_index(drop=True)
    table.insert(0, 'Platz', range(1, len(table) + 1))
    return table

@st.cache_data
def compute_ewige_tabelle(df):
    df_l = df.dropna(subset=["tore_heim", "tore_gast"]).copy()
    h = df_l.rename(columns={"heim": "Team", "tore_heim": "GF", "tore_gast": "GA"})[["Team", "GF", "GA"]]
    a = df_l.rename(columns={"gast": "Team", "tore_gast": "GF", "tore_heim": "GA"})[["Team", "GF", "GA"]]
    all_m = pd.concat([h, a])
    all_m['P']=0; all_m['S']=0; all_m['U']=0; all_m['N']=0
    all_m.loc[all_m['GF'] > all_m['GA'], ['P', 'S']] = [3, 1]
    all_m.loc[all_m['GF'] == all_m['GA'], ['P', 'U']] = [1, 1]
    all_m.loc[all_m['GF'] < all_m['GA'], ['N']] = 1
    ewige = all_m.groupby("Team").agg(Spiele=('Team','size'), S=('S','sum'), U=('U','sum'), N=('N','sum'), T=('GF','sum'), G=('GA','sum'), Punkte=('P','sum')).reset_index()
    cols = ['Spiele', 'S', 'U', 'N', 'T', 'G', 'Punkte']
    ewige[cols] = ewige[cols].fillna(0).astype(int)
    ewige = ewige.sort_values(by=["Punkte", "T"], ascending=False).reset_index(drop=True)
    ewige.insert(0, "Platz", range(1, len(ewige) + 1))
    return ewige

# ==========================================
# 4. MODERNES DESIGN
# ==========================================

def display_styled_table(df, type="standard"):
    css = """
    <style>
    .mystyle { width: 100%; border-collapse: collapse; color: var(--text-color) !important; background-color: transparent !important; }
    .mystyle th { background-color: #8B0000 !important; color: white !important; padding: 12px; text-align: center !important; text-transform: uppercase; }
    .mystyle td { padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.3); text-align: center !important; }
    .mystyle tr:nth-child(even) { background-color: rgba(128,128,128,0.05); }
    .res-bold { font-weight: bold; font-size: 1.1em; color: var(--text-color) !important; }
    </style>
    """
    html = df.to_html(index=False, classes='mystyle', escape=False)
    if type == "spieltag":
        html = html.replace('<td>', '<td class="res-bold">', df.shape[0])
    st.markdown(css, unsafe_allow_html=True)
    st.write(html, unsafe_allow_html=True)

# ==========================================
# 5. SEITEN
# ==========================================

def show_startseite():
    st.markdown("<h1 style='text-align: center; color: darkred;'>⚽Bundesliga-Dashboard</h1>", unsafe_allow_html=True)
    if os.path.exists("bundesliga.jpg"):
        st.image("bundesliga.jpg", use_container_width=True)
        st.caption("Bildquelle: Pixabay")

def show_spieltag_ansicht(df):
    seasons = sorted(df["saison"].unique(), reverse=True)
    st.sidebar.markdown("---")
    saison_sel = st.sidebar.selectbox("Saison für Spieltage", seasons, key="view_saison")
    
    # Filter für die gewählte Saison
    df_saison = df[df["saison"] == saison_sel]
    played = df_saison.dropna(subset=["tore_heim", "tore_gast"])
    
    # Ermittlung des aktuellsten Spieltags
    latest_md = int(played["spieltag"].max()) if not played.empty else 1
    selected_spieltag = st.sidebar.selectbox("Spieltag wählen", list(range(1, 35)), index=int(latest_md) - 1)
    
    st.markdown(f"<h1 style='text-align: center; color: darkred;'>⚽ {selected_spieltag}. Spieltag ({saison_sel})</h1>", unsafe_allow_html=True)
    
    day_matches = df[(df["saison"] == saison_sel) & (df["spieltag"] == selected_spieltag)].copy()
    
    if not day_matches.empty:
        display_df = pd.DataFrame()
        display_df['Heim'] = day_matches['heim']
        # Ergebnis-Formatierung (ohne zusätzliche HTML-Fett-Tags)
        display_df['Ergebnis'] = day_matches.apply(
            lambda r: f"{int(r['tore_heim'])} : {int(r['tore_gast'])}" if pd.notna(r['tore_heim']) else "vs", 
            axis=1
        )
        display_df['Gast'] = day_matches['gast']
        
        # Aufruf der Styling-Funktion OHNE den type="spieltag" Parameter, 
        # damit die Ersetzung für den Fettdruck nicht triggert.
        display_styled_table(display_df)

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
        display_styled_table(final_meister)

def show_vereinsanalyse(df, seasons):
    st.title("📈 Vereinsanalyse")
    teams = sorted(df["heim"].unique())
    verein = st.selectbox("Verein auswählen", teams, index=None)
    
    if verein:
        erfolge = []
        for s in seasons:
            # Tabelle für jede Saison berechnen, um den Platz zu finden
            t = calculate_table(df, s)
            if not t.empty and verein in t["Team"].values:
                platz = t[t["Team"] == verein]["Platz"].values[0]
                erfolge.append({"Saison": s, "Platz": int(platz)})
        
        if erfolge:
            pdf = pd.DataFrame(erfolge)
            
            # WICHTIG: Chronologische Sortierung (von alt nach neu)
            # Damit die Kurve von links nach rechts durch die Zeit läuft
            pdf = pdf.sort_values("Saison")
            
            # Erstellung des Liniendiagramms
            fig = px.line(
                pdf, 
                x="Saison", 
                y="Platz", 
                markers=True, 
                text="Platz", 
                title=f"Platzierungen im Zeitverlauf: {verein}"
            )
            
            # WICHTIG: Skalierung fixieren (1 bis 18)
            # autorange="reversed" sorgt dafür, dass Platz 1 oben ist
            fig.update_yaxes(
                autorange="reversed", 
                tick0=1, 
                dtick=1, 
                range=[18.5, 0.5],  # Begrenzt die Anzeige exakt auf die 18 Plätze
                gridcolor='rgba(128,128,128,0.2)'
            )
            
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)

        # Der restliche Code für den Direktvergleich (Tore/Gegentore)
        st.subheader("Direktvergleich")
        v_spiele = df[((df["heim"] == verein) | (df["gast"] == verein))].dropna(subset=["tore_heim", "tore_gast"])
        bilanz_dict = {}
        for _, r in v_spiele.iterrows():
            is_h = r["heim"] == verein
            gegner = r["gast"] if is_h else r["heim"]
            if gegner not in bilanz_dict: 
                bilanz_dict[gegner] = {"Spiele":0, "S":0, "U":0, "N":0, "T":0, "G":0}
            
            gf, ga = (int(r["tore_heim"]), int(r["tore_gast"])) if is_h else (int(r["tore_gast"]), int(r["tore_heim"]))
            bilanz_dict[gegner]["Spiele"] += 1
            bilanz_dict[gegner]["T"] += gf
            bilanz_dict[gegner]["G"] += ga
            if gf > ga: bilanz_dict[gegner]["S"] += 1
            elif gf < ga: bilanz_dict[gegner]["N"] += 1
            else: bilanz_dict[gegner]["U"] += 1

        if bilanz_dict:
            res_df = pd.DataFrame.from_dict(bilanz_dict, orient='index').reset_index().rename(columns={'index': 'Gegner'})
            # Bilanz-Spalte ist weg, Tore (T) und Gegentore (G) sind da
            res_df = res_df[["Gegner", "Spiele", "S", "U", "N", "T", "G"]].sort_values("Spiele", ascending=False)
            display_styled_table(res_df)

def show_tippspiel(df):
    st.title("🎯 Tippspiel")
    # Ermittlung der aktuellsten Saison aus den Daten
    aktuelle_saison = sorted(df["saison"].unique(), reverse=True)[0]
    st.subheader(f"Tipps abgeben für Saison: {aktuelle_saison}")
    
    # Filter für Spiele, die noch kein Ergebnis haben
    future = df[(df['saison'] == aktuelle_saison) & (df['tore_heim'].isna())]
    
    if not future.empty:
        st.info("Hinweis: Zum Speichern der Tipps muss unten zwingend ein Name eingetragen werden.")
        spieltag = st.selectbox("Spieltag wählen", sorted(future['spieltag'].unique()))
        tag_matches = future[future['spieltag'] == spieltag]

        with st.form("tipp_form"):
            tipps = {}
            for idx, row in tag_matches.iterrows():
                c1, c2, c3 = st.columns([4, 1, 1])
                c1.write(f"**{row['heim']}** - **{row['gast']}**")
                tipps[idx] = (
                    c2.number_input("H", min_value=0, step=1, key=f"h_{idx}"), 
                    c3.number_input("G", min_value=0, step=1, key=f"g_{idx}")
                )
            
            user = st.text_input("Dein Name (Pflichtfeld zum Speichern):")
            
            if st.form_submit_button("Tipps jetzt speichern"):
                if user.strip():
                    try:
                        conn = get_conn()
                        with conn.session as session:
                            for idx, val in tipps.items():
                                row = tag_matches.loc[idx]
                                # 1. Alten Tipp des Users für dieses Spiel löschen
                                session.execute(
                                    text('DELETE FROM tipps WHERE "user"=:u AND saison=:s AND spieltag=:st AND heim=:h AND gast=:g'),
                                    {"u": user, "s": aktuelle_saison, "st": int(row['spieltag']), "h": row['heim'], "g": row['gast']}
                                )
                                # 2. Neuen Tipp einfügen
                                session.execute(
                                    text('INSERT INTO tipps ("user", saison, spieltag, heim, gast, tipp_heim, tipp_gast, punkte) VALUES (:u, :s, :st, :h, :g, :th, :tg, 0)'),
                                    {"u": user, "s": aktuelle_saison, "st": int(row['spieltag']), "h": row['heim'], "g": row['gast'], "th": val[0], "tg": val[1]}
                                )
                            session.commit()
                        st.success(f"Tipps für {user} wurden erfolgreich gespeichert!")
                    except Exception as e:
                        st.error(f"Datenbankfehler: {e}")
                else:
                    st.error("Bitte gib einen Namen ein, bevor du speicherst!")
    else:
        st.write("Aktuell stehen keine Spiele zum Tippen bereit.")

def show_highscore():
    st.title("🏆 Hall of Fame")
    conn = get_conn()
    hof_df = conn.query('SELECT name, saison, punkte FROM hall_of_fame ORDER BY punkte DESC', ttl=0)
    if not hof_df.empty:
        display_styled_table(hof_df)

# ==========================================
# 6. MAIN APP
# ==========================================

def main():
    st.set_page_config(page_title="Bundesliga Dashboard", layout="wide")
    init_db() 
    df = load_data_from_db()
    if df.empty: return
    seasons = sorted(df["saison"].unique(), reverse=True)
    
    page = st.sidebar.radio("Navigation", ["Startseite", "Spieltage", "Saisontabelle", "Ewige Tabelle", "Meisterschaften", "Vereinsanalyse", "Tippspiel", "Highscore"])

    if page == "Startseite": show_startseite()
    elif page == "Spieltage": show_spieltag_ansicht(df)
    elif page == "Saisontabelle":
        s_sel = st.sidebar.selectbox("Saison wählen", seasons)
        st.title(f"Saison {s_sel}") 
        from main import calculate_table
        display_styled_table(calculate_table(df, s_sel))
    elif page == "Ewige Tabelle":
        st.title("📚 Ewige Tabelle")
        display_styled_table(compute_ewige_tabelle(df))
    elif page == "Meisterschaften": show_meisterstatistik(df, seasons)
    elif page == "Vereinsanalyse": show_vereinsanalyse(df, seasons)
    elif page == "Tippspiel": show_tippspiel(df)
    elif page == "Highscore": show_highscore()

if __name__ == "__main__":
    main()
