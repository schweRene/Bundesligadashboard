#!/usr/bin/env python3
# coding: utf-8

import io
import requests
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

def get_torschuetzen():
    """ Lädt die ewige Torschützenliste aus der Supabase DB"""
    try:
        conn = get_conn()
        # sortieren nach Platz
        df = conn.query("SELECT * FROM torschuetzen ORDER BY platz ASC", ttl="1h")
        return df
    except Exception as e:
        # Falls die Tabelle noch nicht existiert oder ein Fehler auftritt
        st.error(f"Fehler beim Laden der Torschützenliste: [e]")
        return pd.DataFrame()

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
    # 1. Namen vereinheitlichen (MSV Duisburg Fix)
    df_clean = df.dropna(subset=["tore_heim", "tore_gast"]).copy()
    df_clean["heim"] = df_clean["heim"].replace(["Meidericher SV", "Meiderich"], "MSV Duisburg")
    df_clean["gast"] = df_clean["gast"].replace(["Meidericher SV", "Meiderich"], "MSV Duisburg")

    # 2. Berechnung der Statistiken
    h = df_clean.rename(columns={"heim": "Team", "tore_heim": "GF", "tore_gast": "GA"})[["Team", "GF", "GA"]]
    a = df_clean.rename(columns={"gast": "Team", "tore_gast": "GF", "tore_heim": "GA"})[["Team", "GF", "GA"]]
    all_m = pd.concat([h, a])
    all_m['P']=0; all_m['S']=0; all_m['U']=0; all_m['N']=0
    all_m.loc[all_m['GF'] > all_m['GA'], ['P', 'S']] = [3, 1]
    all_m.loc[all_m['GF'] == all_m['GA'], ['P', 'U']] = [1, 1]
    all_m.loc[all_m['GF'] < all_m['GA'], ['N']] = 1
    
    ewige = all_m.groupby("Team").agg(
        Spiele=('Team','size'), 
        S=('S','sum'), 
        U=('U','sum'), 
        N=('N','sum'), 
        T=('GF','sum'), 
        G=('GA','sum'), 
        Punkte=('P','sum')
    ).reset_index()
    
    cols = ['Spiele', 'S', 'U', 'N', 'T', 'G', 'Punkte']
    ewige[cols] = ewige[cols].fillna(0).astype(int)
    
    # Sortieren und Platzierung vergeben
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
    
    # Namen für die Analyse vereinheitlichen
    df_clean = df.copy()
    df_clean["heim"] = df_clean["heim"].replace(["Meidericher SV", "Meiderich"], "MSV Duisburg")
    df_clean["gast"] = df_clean["gast"].replace(["Meidericher SV", "Meiderich"], "MSV Duisburg")
    
    # Teams aus den bereinigten Daten laden
    teams = sorted(df_clean["heim"].unique())
    verein = st.selectbox("Verein auswählen", teams, index=None)
    
    if verein:
        erfolge = []
        for s in seasons:
            # Wir nutzen df_clean, damit calculate_table die Punkte für den fusionierten Verein zählt
            t = calculate_table(df_clean, s)
            if not t.empty and verein in t["Team"].values:
                platz = t[t["Team"] == verein]["Platz"].values[0]
                erfolge.append({"Saison": s, "Platz": int(platz)})
        
        if erfolge:
            pdf = pd.DataFrame(erfolge).sort_values("Saison")
            fig = px.line(pdf, x="Saison", y="Platz", markers=True, text="Platz", 
                         title=f"Platzierungen im Zeitverlauf: {verein}")
            
            fig.update_yaxes(autorange="reversed", tick0=1, dtick=1, range=[18.5, 0.5], 
                             gridcolor='rgba(128,128,128,0.2)')
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Direktvergleich")
        v_spiele = df_clean[((df_clean["heim"] == verein) | (df_clean["gast"] == verein))].dropna(subset=["tore_heim", "tore_gast"])
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
            res_df = res_df[["Gegner", "Spiele", "S", "U", "N", "T", "G"]].sort_values("Spiele", ascending=False)
            display_styled_table(res_df)

def show_torschuetzen():
    st.title("⚽ Ewige Torschützenliste")
    st.markdown("----")

    with st.spinner("Lade Daten aus der DB..."):
        df_tore = get_torschuetzen()

        if not df_tore.empty:
            st.dataframe(
                df_tore,
                column_config={
                    "platz": "Rang",
                    "spieler": "Spieler",
                    "spiele": "Einsätze",
                    "tore": "Tore"
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("Keine Torschützen gefunden.")

def show_tippspiel(df):
    
    # Dynamische Saison
    aktuelle_saison = str(df["saison"].max())

    # 1. SPIELTAGS-AUSWAHL
    offene_spieltage = sorted(df[(df["saison"] == aktuelle_saison) & (df["tore_heim"].isna())]["spieltag"].unique())

    if offene_spieltage:
        selected_st = st.selectbox("Spieltag auswählen:", offene_spieltage)
        
        mask = (df["saison"] == aktuelle_saison) & (df["spieltag"] == selected_st) & (df["tore_heim"].isna())
        current_st_df = df[mask].sort_values("heim")

        st.subheader(f"Gib deinen Tipp für den {selected_st}. Spieltag ein")

        with st.form("tipp_form"):
            tipps_data = {} # Hier speichern wir die Werte der Number-Inputs
            
            for idx, row in current_st_df.iterrows():
                col_h, col_th, col_vs, col_tg, col_g = st.columns([3, 2, 1, 2, 3])
                with col_h: 
                    st.write(f"**{row['heim']}**")
                with col_th: 
                    th = st.number_input("Heim", min_value=0, max_value=20, value=0, step=1, key=f"h_{idx}", label_visibility="collapsed")
                with col_vs: 
                    st.write(":")
                with col_tg: 
                    tg = st.number_input("Gast", min_value=0, max_value=20, value=0, step=1, key=f"g_{idx}", label_visibility="collapsed")
                with col_g: 
                    st.write(f"**{row['gast']}**")
                tipps_data[idx] = (th, tg)

            st.markdown("---")
            # Name als Pflichtfeld direkt über dem Button
            user_name = st.text_input("Gib deinen Namen ein", placeholder="Pflichtfeld", key="tipp_user_name").strip()
            
            if st.form_submit_button("Tipp speichern"):
                user_name = user_name.strip()
                if not user_name:
                    st.error("Bitte gib deinen Namen ein!")
                else:
                    erfolgreich = True
                    fehler_meldung = ""
                    
                    # Da deine save_tipp jedes Spiel einzeln braucht, 
                    # gehen wir hier in einer Schleife durch alle eingegebenen Tipps
                    for idx, (th, tg) in tipps_data.items():
                        row = current_st_df.loc[idx]
                        heim_team = row["heim"]
                        gast_team = row["gast"]
                        
                        # Aufruf deiner Funktion mit allen 7 Parametern
                        status, msg = save_tipp(
                            user_name, 
                            aktuelle_saison, 
                            selected_st, 
                            heim_team, 
                            gast_team, 
                            th, 
                            tg
                        )
                        
                        if not status:
                            erfolgreich = False
                            fehler_meldung = msg
                    
                    if erfolgreich:
                        st.success(f"Tipps für Spieltag {selected_st} erfolgreich gespeichert!")
                        st.rerun() # Seite neu laden, um die Auswertung unten direkt zu aktualisieren
                    else:
                        st.error(f"Fehler beim Speichern: {fehler_meldung}")
    else:
        st.info("Keine weiteren Spiele zum Tippen verfügbar.")

    # 2. AUSWERTUNG 
    st.markdown("---")
    st.subheader("📊 Deine Tippspiel-Auswertung")
    
    check_user = st.text_input("Name eingeben, um deine Punktzahl zu sehen:", key="check_user_stats")
    
    if check_user:
        with st.spinner('Lade deine Punkte...'):
            conn = get_conn()
            # Hier säubern wir die Eingabe für die Suche
            clean_search = check_user.strip()
            
            # Wir nutzen ILIKE für Case-Insensitivity (Groß/Kleinschreibung egal)
            query = ("""
                SELECT t.spieltag, t.heim, t.gast, t.tipp_heim, t.tipp_gast, t.punkte, s.tore_heim, s.tore_gast
                FROM tipps t
                JOIN spiele s ON t.saison = s.saison AND t.spieltag = s.spieltag AND t.heim = s.heim
                WHERE t."user" ILIKE :u AND t.saison = :s
                ORDER BY t.spieltag DESC, t.heim ASC
            """)
            
            # WICHTIG: Hier übergeben wir den gesäuberten Namen 'clean_search'
            user_tipps = conn.query(query, params={"u": clean_search, "s": aktuelle_saison}, ttl=0)
        
        if not user_tipps.empty:
            # Name aus der Metrik entfernt, wie gewünscht
            gesamt_pkt = int(user_tipps['punkte'].sum())
            st.metric("Deine aktuellen Gesamtpunkte", f"{gesamt_pkt} Pkt.")

            user_tipps['Ergebnis'] = user_tipps.apply(
                lambda r: f"{int(r['tore_heim'])}:{int(r['tore_gast'])}" if pd.notna(r['tore_heim']) else "-", axis=1
            )
            user_tipps['Tipp'] = user_tipps.apply(lambda r: f"{int(r['tipp_heim'])}:{int(r['tipp_gast'])}", axis=1)
            
            ausgabe = user_tipps[['spieltag', 'heim', 'gast', 'Tipp', 'Ergebnis', 'punkte']].copy()
            ausgabe.columns = ['ST', 'Heim', 'Gast', 'Tipp', 'Real', 'Pkt']
            display_styled_table(ausgabe)
        else:
            st.info("Keine Tipps gefunden.")

def show_highscore():
    st.markdown("<h2 style='text-align: center; color: #8B0000;'>🏆 Hall of Fame</h2>", unsafe_allow_html=True)
    conn = get_conn()
    # Begrenzung auf Top 10 via LIMIT 10
    hof_df = conn.query('SELECT name, saison, punkte FROM hall_of_fame ORDER BY punkte DESC LIMIT 10', ttl=0)
    
    if not hof_df.empty:
        # Spalten-Layout für Desktop-Karten (zentriert)
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            for i, row in hof_df.iterrows():
                rank = i + 1
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                border_style = "border: 2px solid #FFD700; box-shadow: 0px 0px 10px #FFD700;" if rank == 1 else "border: 1px solid #ddd;"
                
                st.markdown(f"""
                    <div style='{border_style} border-radius: 10px; padding: 15px; margin-bottom: 15px; background-color: white;'>
                        <table style='width: 100%; border: none;'>
                            <tr style='border: none;'>
                                <td style='width: 10%; font-size: 24px; text-align: center; border: none;'>{medal}</td>
                                <td style='width: 70%; padding-left: 15px; border: none;'>
                                    <div style='font-weight: bold; font-size: 18px; color: {"#8B0000" if "Computer" in str(row["name"]) else "#31333F"};'>{row['name']}</div>
                                    <div style='font-size: 0.9rem; color: gray;'>Saison {row['saison']}</div>
                                </td>
                                <td style='width: 20%; text-align: right; border: none;'>
                                    <div style='font-weight: bold; font-size: 20px; color: #8B0000;'>{int(row['punkte'])}</div>
                                    <div style='font-size: 0.8rem; color: gray;'>Punkte</div>
                                </td>
                            </tr>
                        </table>
                    </div>
                """, unsafe_allow_html=True)

# ==========================================
# 6. MAIN APP
# ==========================================

def main():
    
    st.set_page_config(page_title="Bundesliga Dashboard", layout="wide")
    # Einheitliches Design für alle Überschriften erzwingen
    st.markdown("""
        <style>
        h1, h2, h3, h4 { color: darkred !important; }
        /* Fix für Tippspiel und andere Texte */
        .stMarkdown p { color: inherit; } 
        </style>
        """, unsafe_allow_html=True)
    # 1. JavaScript zur Breitenerkennung
    import streamlit.components.v1 as components
    
    # Wir senden die Breite an Streamlit
    components.html(
        """
        <script>
        var width = window.parent.innerWidth;
        window.parent.postMessage({type: 'streamlit:setComponentValue', value: width}, '*');
        </script>
        """,
        height=0,
    )

    # 2. Breite aus Session State abrufen
    # Falls noch nicht erkannt, nehmen wir 1200 (Desktop) als Fallback
    detected_width = st.session_state.get("device_width", 1200)

    # 3. Die Weiche (Logik)
    query_params = st.query_params
    
    # Wir erhöhen den Schwellenwert auf 1100px, damit auch große Handys 
    # im Querformat oder mit hoher Auflösung sicher als "Mobile" erkannt werden.
    if query_params.get("view") == "mobile" or detected_width < 1100:
        from mobile_app import run_mobile_main
        run_mobile_main()
        st.stop() # Verhindert das Laden der Desktop-Konfiguration
    
    #st.set_page_config(page_title="Bundesliga Dashboard", layout="wide")
    
    init_db() 
    df = load_data_from_db()
    if df.empty: return

    # Korrekter Aufruf deiner Funktion aus Zeile 70
    evaluate_tipps(df)

    seasons = sorted(df["saison"].unique(), reverse=True)
    
    page = st.sidebar.radio("Navigation", ["Startseite", "Spieltage", "Saisontabelle", "Ewige Tabelle", "Torschützen", "Meisterschaften", "Vereinsanalyse", "Tippspiel", "Highscore"])

    if page == "Startseite": 
        show_startseite()
    elif page == "Spieltage": 
        show_spieltag_ansicht(df)
    elif page == "Saisontabelle":
        s_sel = st.sidebar.selectbox("Saison wählen", seasons)
        st.markdown(f"<h1 style='color: darkred;'>Saison {s_sel}</h1>", unsafe_allow_html=True)
        display_styled_table(calculate_table(df, s_sel))
    elif page == "Ewige Tabelle":
        st.markdown("<h1 style='color: darkred;'>📚 Ewige Tabelle</h1>", unsafe_allow_html=True)
        ewige_df = compute_ewige_tabelle(df)
        top_10 = ewige_df.head(10)
        max_punkte = top_10['Punkte'].max()
        y_obergrenze = max_punkte * 1.15 

        fig = px.bar(
            top_10, 
            x='Team', 
            y='Punkte', 
            text='Punkte',
            title="Top 10",
            color='Punkte',
            color_continuous_scale='Viridis'
        )
        
        fig.update_traces(textposition='outside')
        fig.update_layout(
            xaxis_title="Verein", 
            yaxis_title="Gesamtpunkte", 
            showlegend=False,
            yaxis_range=[0, y_obergrenze]
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("Rangliste ab Platz 11")
        ab_platz_11 = ewige_df.iloc[10:] 
        display_styled_table(ab_platz_11)

    elif page == "Torschützen":
        st.markdown("<h1 style='color: darkred;'>⚽ Ewige Torschützenliste</h1>", unsafe_allow_html=True)
        st.markdown("----")

        df_tore = get_torschuetzen()
        
        if not df_tore.empty:
            # --- DATENBEREINIGUNG ---
            def clean_player_name(full_name):
                # Wir suchen nach Vereinen oder "X Vereine" und schneiden dort ab
                # Hinzugefügt: "1.", "2." etc. auch ohne führendes Leerzeichen prüfen
                stops = [" FC ", " 1.", " 2 ", " 3 ", " 4 ", " 5 ", " 6 ", " Bayer ", " Eintracht ", " Borussia ", " VfB ", " Schalke "]
                name = full_name
                for stop in stops:
                    if stop in name:
                        name = name.split(stop)[0]
                return name.strip()

            df_tore['spieler'] = df_tore['spieler'].apply(clean_player_name)

            # Top 3 für das Diagramm
            top_3 = df_tore.head(3)
            rest_tore = df_tore.iloc[3:]

            fig_tore = px.bar(top_3, x='spieler', y='tore', text='tore', color='tore', color_continuous_scale='Reds')
            fig_tore.update_layout(xaxis_title="", yaxis_title="Tore", showlegend=False, height=350)
            st.plotly_chart(fig_tore, use_container_width=True)

            st.subheader("Weitere Platzierungen")
            
            # Höhe berechnen (35px pro Zeile + Header)
            h = (len(rest_tore) + 1) * 35 + 10

            st.dataframe(
                rest_tore,
                column_config={
                    "platz": st.column_config.NumberColumn("Platz", width=50, format="%d"),
                    "spieler": st.column_config.TextColumn("Spieler", width=200),
                    "spiele": st.column_config.NumberColumn("Einsätze", width=80, format="%d"),
                    "tore": st.column_config.NumberColumn("Tore", width=80, format="%d")
                },
                hide_index=True,
                use_container_width=False, # Erzwingt die festen Breiten
                height=h
            )
        else:
            st.warning("Keine Torschützendaten gefunden.")
    elif page == "Meisterschaften": 
        show_meisterstatistik(df, seasons)
    elif page == "Vereinsanalyse": 
        show_vereinsanalyse(df, seasons)
    elif page == "Tippspiel": 
        st.markdown("<h1 style='color: darkred;'>🎮 Tippspiel</h1>", unsafe_allow_html=True)
        show_tippspiel(df)
    elif page == "Highscore": 
        show_highscore()

if __name__ == "__main__":
    main()
